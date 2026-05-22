"""
OmniLab transactional email (CRE-13 / Module 8).

Pluggable sender with two providers:

  - "postmark"  — real send via Postmark's HTTP API (no SDK dependency)
  - "log"       — append to billing_emails.log; same behavior as the
                  pre-CRE-13 stub. Used when no provider keys are set.

Provider is selected from env at import time. Switch live by setting:

  EMAIL_PROVIDER         "postmark" | "log"  (default: log when no keys)
  POSTMARK_TOKEN         Postmark server token (sk_*)
  EMAIL_FROM             "OmniLab <hello@omnilab.io>"  (must be verified
                         in Postmark sender signatures)
  EMAIL_DRY_RUN          "1" to force log mode regardless of provider

Templates live next to this file in ./templates/email/. Each template is
a single HTML file with `{{placeholders}}`. Rendering uses str.format
semantics with the placeholder dict — no Jinja, no extra dep.

Sender failures NEVER raise: they log the failure and return False so
the caller (Stripe webhook, wizard) keeps going. A bad mailer cannot
break paid checkout — that's a hard product invariant.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger("omnilab.email")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "").lower()
POSTMARK_TOKEN = os.getenv("POSTMARK_TOKEN", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "OmniLab <hello@omnilab.io>")
EMAIL_DRY_RUN = os.getenv("EMAIL_DRY_RUN", "") == "1"

# Auto-pick provider: prefer explicit setting, fall back to Postmark if a token
# is configured, else log mode.
if not EMAIL_PROVIDER:
    EMAIL_PROVIDER = "postmark" if (POSTMARK_TOKEN and not EMAIL_DRY_RUN) else "log"

EMAIL_LOG_PATH = Path.home() / ".omnilab" / "email.log"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"

POSTMARK_URL = "https://api.postmarkapp.com/email"


# ---------------------------------------------------------------------------
# Public API — used by billing.py / system.py / cron jobs
# ---------------------------------------------------------------------------
def send_license_delivery(recipient: str, license_key: str, plan: str) -> bool:
    return _send(
        template="01_license_delivery",
        recipient=recipient,
        subject=f"Your OmniLab {plan.title()} license key",
        context={
            "license_key": license_key,
            "plan": plan,
            "year": datetime.now(timezone.utc).year,
        },
    )


def send_welcome(recipient: str, plan: str = "free") -> bool:
    return _send(
        template="02_welcome",
        recipient=recipient,
        subject="Welcome to OmniLab",
        context={
            "plan": plan,
            "year": datetime.now(timezone.utc).year,
        },
    )


def send_expiry_warning(recipient: str, days_left: int, plan: str = "pro") -> bool:
    return _send(
        template="03_expiry_warning",
        recipient=recipient,
        subject=f"Your OmniLab {plan.title()} license expires in {days_left} days",
        context={
            "days_left": days_left,
            "plan": plan,
            "year": datetime.now(timezone.utc).year,
        },
    )


def send_payment_failed(recipient: str, customer_id: str,
                        grace_period_days: int = 7) -> bool:
    return _send(
        template="04_payment_failed",
        recipient=recipient,
        subject="Action required: your OmniLab payment failed",
        context={
            "customer_id": customer_id,
            "grace_period_days": grace_period_days,
            "year": datetime.now(timezone.utc).year,
        },
    )


def send_update_available(recipient: str, version: str,
                          highlights: str = "") -> bool:
    return _send(
        template="05_update_available",
        recipient=recipient,
        subject=f"OmniLab {version} is available",
        context={
            "version": version,
            "highlights": highlights,
            "year": datetime.now(timezone.utc).year,
        },
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _render(template: str, context: dict) -> str:
    path = TEMPLATES_DIR / f"{template}.html"
    if not path.exists():
        # Last-ditch: render a plain fallback so we don't drop the message
        # entirely. Caller still sees a True from _send because we delivered
        # something rather than nothing.
        logger.warning("email template missing: %s — using plain fallback", path)
        return f"<html><body><pre>{json.dumps(context, indent=2)}</pre></body></html>"
    html = path.read_text(encoding="utf-8")
    # str.format style. Curly braces inside the template that aren't
    # placeholders are deliberately not used (the HTML templates we ship are
    # placeholder-safe). If a template introduces literal { it must be
    # escaped to {{ — documented in templates/email/README.md.
    try:
        return html.format(**context)
    except KeyError as exc:
        logger.error("template %s missing placeholder %s; rendering raw", template, exc)
        return html


def _send(template: str, recipient: str, subject: str, context: dict) -> bool:
    if not recipient:
        logger.warning("refusing to send %s with empty recipient", template)
        return False

    html = _render(template, context)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "template": template,
        "to": recipient,
        "subject": subject,
        "provider": EMAIL_PROVIDER,
        "context": context,
    }

    # In log mode (or dry-run override) we never reach the network
    if EMAIL_PROVIDER == "log" or EMAIL_DRY_RUN:
        _append_log(entry, html_size=len(html))
        logger.info("[email:log] would send %s to %s", template, recipient)
        return True

    if EMAIL_PROVIDER == "postmark":
        ok = _send_postmark(recipient, subject, html, template, context)
        entry["delivered"] = ok
        _append_log(entry, html_size=len(html))
        return ok

    logger.error("unknown EMAIL_PROVIDER: %r — falling back to log", EMAIL_PROVIDER)
    _append_log(entry, html_size=len(html))
    return False


def _append_log(entry: dict, html_size: int) -> None:
    entry = dict(entry, html_bytes=html_size)
    try:
        EMAIL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with EMAIL_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:  # pragma: no cover — logging only
        logger.warning("failed to append email log: %s", exc)


def _send_postmark(recipient: str, subject: str, html: str,
                   template: str, context: dict) -> bool:
    if not POSTMARK_TOKEN:
        logger.error("postmark provider selected but POSTMARK_TOKEN is empty")
        return False
    payload = {
        "From": EMAIL_FROM,
        "To": recipient,
        "Subject": subject,
        "HtmlBody": html,
        "MessageStream": "outbound",
        "Tag": template,
        "Metadata": {k: str(v) for k, v in context.items() if not isinstance(v, dict)},
    }
    headers = {
        "X-Postmark-Server-Token": POSTMARK_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(POSTMARK_URL, json=payload, headers=headers)
        if r.status_code == 200:
            return True
        logger.error("postmark send failed %s: %s", r.status_code, r.text[:300])
        return False
    except Exception as exc:
        logger.exception("postmark request crashed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Health probe — used by /api/system/email-health (and tests)
# ---------------------------------------------------------------------------
def health() -> dict:
    return {
        "provider": EMAIL_PROVIDER,
        "has_postmark_token": bool(POSTMARK_TOKEN),
        "from_address": EMAIL_FROM,
        "dry_run": EMAIL_DRY_RUN,
        "templates_dir": str(TEMPLATES_DIR),
        "templates_present": sorted(
            p.stem for p in TEMPLATES_DIR.glob("*.html")
        ) if TEMPLATES_DIR.exists() else [],
    }


__all__ = [
    "send_license_delivery",
    "send_welcome",
    "send_expiry_warning",
    "send_payment_failed",
    "send_update_available",
    "health",
]
