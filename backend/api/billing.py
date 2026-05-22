"""
OmniLab Billing API - Stripe integration (CRE-21)
==================================================

Endpoints:
  POST /api/billing/create-checkout-session  -> {url: <stripe checkout url>}
  POST /api/billing/webhook                  -> handles Stripe events
  GET  /api/billing/health                   -> {status, mode, has_keys}

Env vars (see .env.example for placeholders + swap-when-real instructions):
  STRIPE_SECRET_KEY            sk_test_... (sk_live_... in prod)
  STRIPE_PUBLISHABLE_KEY       pk_test_... (pk_live_... in prod)
  STRIPE_WEBHOOK_SECRET        whsec_...    (from Stripe Dashboard webhook config)
  STRIPE_PRICE_MONTHLY         price_...    ($12/mo plan)
  STRIPE_PRICE_YEARLY          price_...    ($99/yr plan)
  STRIPE_SUCCESS_URL           default: http://localhost:5000/checkout/success
  STRIPE_CANCEL_URL            default: http://localhost:5000/checkout/cancel

Stub strategy:
  send_license_email() and send_payment_failed_email() currently LOG ONLY
  (no real email). CRE-13 (Module 8 - email templates wired to Postmark)
  will replace these stubs with real send calls. Look for `TODO(CRE-13)`.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

# Stripe SDK - imported lazily so the module loads even if not installed yet
try:
    import stripe  # type: ignore
    STRIPE_AVAILABLE = True
except ImportError:
    stripe = None  # type: ignore
    STRIPE_AVAILABLE = False

# License system from CRE-4 (already deployed). We call its key generator
# directly when a checkout succeeds.
try:
    from api.license import generate_license_key  # type: ignore
    LICENSE_AVAILABLE = True
except ImportError:
    # Fall back to a no-op stub so this module still loads if the license
    # module hasn't been deployed yet for some reason.
    generate_license_key = None  # type: ignore
    LICENSE_AVAILABLE = False

logger = logging.getLogger("omnilab.billing")
logger.setLevel(logging.INFO)

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration (env-driven, all swappable without code changes)
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY", "")
STRIPE_PRICE_YEARLY = os.getenv("STRIPE_PRICE_YEARLY", "")
STRIPE_SUCCESS_URL = os.getenv(
    "STRIPE_SUCCESS_URL", "http://localhost:5000/checkout/success"
)
STRIPE_CANCEL_URL = os.getenv(
    "STRIPE_CANCEL_URL", "http://localhost:5000/checkout/cancel"
)

# Test mode is determined by the secret key prefix
# (sk_test_ = test, sk_live_ = live). This mirrors Stripe's own convention.
STRIPE_TEST_MODE = STRIPE_SECRET_KEY.startswith("sk_test_") or not STRIPE_SECRET_KEY

if STRIPE_AVAILABLE and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# ---------------------------------------------------------------------------
# Email stubs (CRE-13 will replace these)
# ---------------------------------------------------------------------------
EMAIL_LOG = Path.home() / "netlab" / "backend" / "billing_emails.log"


def _log_email(template: str, recipient: str, context: dict) -> None:
    """TODO(CRE-13): Replace this with the Postmark sender from Module 8.

    Today: append a JSON line to billing_emails.log so we can confirm the
    webhook fired and the right template would have been sent. CRE-13's
    sender wiring should swap these two stub functions for real send calls.
    """
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "template": template,
        "to": recipient,
        "context": context,
    }
    try:
        with EMAIL_LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:  # pragma: no cover - logging-only
        logger.warning("Failed to write email log: %s", exc)
    logger.info("[email-stub] would send %s to %s", template, recipient)


def send_license_email(recipient: str, license_key: str, plan: str) -> None:
    """TODO(CRE-13): wire to emails/01_license_delivery.html via Postmark."""
    _log_email(
        "01_license_delivery",
        recipient,
        {"license_key": license_key, "plan": plan},
    )


def send_payment_failed_email(recipient: str, customer_id: str) -> None:
    """TODO(CRE-13): wire to emails/04_payment_failed.html via Postmark."""
    _log_email(
        "04_payment_failed",
        recipient,
        {"customer_id": customer_id, "grace_period_days": 7},
    )


# ---------------------------------------------------------------------------
# Health probe (works without any keys — useful while waiting for real account)
# ---------------------------------------------------------------------------
@router.get("/health")
def billing_health():
    return {
        "status": "ok",
        "stripe_sdk_installed": STRIPE_AVAILABLE,
        "license_module_available": LICENSE_AVAILABLE,
        "mode": "test" if STRIPE_TEST_MODE else "live",
        "has_secret_key": bool(STRIPE_SECRET_KEY),
        "has_publishable_key": bool(STRIPE_PUBLISHABLE_KEY),
        "has_webhook_secret": bool(STRIPE_WEBHOOK_SECRET),
        "has_price_ids": bool(STRIPE_PRICE_MONTHLY and STRIPE_PRICE_YEARLY),
        "note": (
            "Awaiting real Stripe account. Endpoints registered and reachable; "
            "create-checkout-session will return 503 until env vars are set."
            if not STRIPE_SECRET_KEY
            else "Live integration; check Stripe Dashboard for activity."
        ),
    }


# ---------------------------------------------------------------------------
# POST /api/billing/create-checkout-session
# ---------------------------------------------------------------------------
class CheckoutSessionRequest(BaseModel):
    plan: str  # "monthly" or "yearly"
    customer_email: Optional[str] = None
    promo_code: Optional[str] = None  # LAUNCH50, BETA20 (set in Stripe Dashboard)


@router.post("/create-checkout-session")
def create_checkout_session(req: CheckoutSessionRequest):
    if not STRIPE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Stripe SDK not installed. Run: pip install stripe",
        )
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "STRIPE_SECRET_KEY not set. See .env.example. "
                "(Expected: pending real Stripe account setup.)"
            ),
        )

    price_id = (
        STRIPE_PRICE_MONTHLY if req.plan == "monthly" else STRIPE_PRICE_YEARLY
    )
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail=(
                f"STRIPE_PRICE_{'MONTHLY' if req.plan == 'monthly' else 'YEARLY'} "
                "not set. Create the price in Stripe Dashboard and add to .env."
            ),
        )

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=req.customer_email,
            success_url=STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=STRIPE_CANCEL_URL,
            # Promo codes (LAUNCH50, BETA20) are configured in the Dashboard;
            # enabling allow_promotion_codes lets users redeem them at checkout.
            allow_promotion_codes=True,
            metadata={
                "plan": req.plan,
                "source": "omnilab_checkout",
            },
        )
    except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
        logger.error("Stripe checkout session creation failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))

    return {"url": session.url, "session_id": session.id}


# ---------------------------------------------------------------------------
# POST /api/billing/webhook
# ---------------------------------------------------------------------------
@router.post("/webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Stripe SDK not installed")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verify the event signature. In TEST mode without a webhook secret we
    # still parse the event but skip signature verification so the Stripe CLI
    # (`stripe listen --forward-to ...`) can drive end-to-end tests.
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        else:
            event = json.loads(payload)
            logger.warning(
                "Webhook signature verification SKIPPED "
                "(STRIPE_WEBHOOK_SECRET not set). OK in dev, NOT OK in prod."
            )
    except (stripe.error.SignatureVerificationError, ValueError) as exc:  # type: ignore[attr-defined]
        logger.error("Webhook signature verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type") if isinstance(event, dict) else event["type"]
    data_obj = (
        event["data"]["object"] if isinstance(event, dict) else event.data.object
    )

    logger.info("Stripe webhook received: %s", event_type)

    # ---- checkout.session.completed: issue license + email it ----
    if event_type == "checkout.session.completed":
        customer_email = data_obj.get("customer_email") or data_obj.get(
            "customer_details", {}
        ).get("email", "unknown@omnilab.io")
        plan = data_obj.get("metadata", {}).get("plan", "yearly")

        # Generate a license key via CRE-4 module.
        if LICENSE_AVAILABLE and generate_license_key:
            try:
                license_key = generate_license_key(
                    plan="pro", customer=customer_email
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("License generation failed: %s", exc)
                license_key = "OMNI-PEND-PEND-PEND-PEND"
        else:
            license_key = "OMNI-PEND-PEND-PEND-PEND"
            logger.error(
                "License module unavailable; sent placeholder key to %s. "
                "Check that ~/netlab/backend/api/license.py is deployed.",
                customer_email,
            )

        send_license_email(customer_email, license_key, plan)
        # TODO(future): persist customer->subscription mapping in DB.
        # Out of scope for CRE-21; the license system itself records activation.

        return {"status": "license_issued", "key_last4": license_key[-4:]}

    # ---- invoice.payment_failed: notify + start grace period ----
    if event_type == "invoice.payment_failed":
        customer_email = data_obj.get("customer_email", "unknown@omnilab.io")
        customer_id = data_obj.get("customer", "unknown")
        send_payment_failed_email(customer_email, customer_id)
        # TODO(future): mark subscription as past_due in local DB and surface
        # a grace-period banner in the frontend (separate ticket).
        return {"status": "grace_period_started"}

    # All other events: acknowledge so Stripe doesn't retry.
    return {"status": "ignored", "event_type": event_type}
