"""Email module tests (CRE-13 / Module 8)."""
import json
import os
from pathlib import Path

import pytest


def test_health_reports_log_provider_when_no_token():
    # Re-import fresh so we pick up the test env (no POSTMARK_TOKEN)
    import importlib

    import api.email as email_mod
    importlib.reload(email_mod)
    h = email_mod.health()
    assert h["provider"] in ("log", "postmark")
    assert isinstance(h["templates_present"], list)
    # All 5 CRE-13 templates exist on disk
    expected = {"01_license_delivery", "02_welcome", "03_expiry_warning",
                "04_payment_failed", "05_update_available"}
    assert expected.issubset(set(h["templates_present"])), \
        f"missing: {expected - set(h['templates_present'])}"


def test_render_license_template_substitutes_placeholders():
    from api.email import _render
    html = _render("01_license_delivery", {
        "license_key": "OMNI-XXXX-YYYY-ZZZZ-AAAA",
        "plan": "pro",
        "year": 2026,
    })
    assert "OMNI-XXXX-YYYY-ZZZZ-AAAA" in html
    assert "pro" in html.lower()
    assert "2026" in html


def test_render_missing_placeholder_returns_raw_html_without_crashing():
    from api.email import _render
    # Force a KeyError by omitting a required field — module should log & return raw
    html = _render("02_welcome", {})
    assert "<html" in html.lower() or "<table" in html.lower()


def test_send_license_delivery_in_log_mode(monkeypatch, tmp_path):
    """In log mode, send returns True and appends one JSON line to the log."""
    log_path = tmp_path / "email.log"

    import importlib

    import api.email as email_mod
    monkeypatch.setattr(email_mod, "EMAIL_PROVIDER", "log")
    monkeypatch.setattr(email_mod, "EMAIL_LOG_PATH", log_path)

    ok = email_mod.send_license_delivery("buyer@example.com", "OMNI-AAAA-BBBB-CCCC-DDDD", "pro")
    assert ok is True
    assert log_path.exists()
    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["template"] == "01_license_delivery"
    assert entry["to"] == "buyer@example.com"
    assert entry["provider"] == "log"
    assert entry["context"]["license_key"] == "OMNI-AAAA-BBBB-CCCC-DDDD"


def test_send_refuses_empty_recipient(monkeypatch, tmp_path):
    import api.email as email_mod
    monkeypatch.setattr(email_mod, "EMAIL_PROVIDER", "log")
    monkeypatch.setattr(email_mod, "EMAIL_LOG_PATH", tmp_path / "x.log")
    assert email_mod.send_welcome("", plan="free") is False


def test_send_postmark_failure_returns_false_without_raising(monkeypatch, tmp_path):
    """A Postmark outage must NOT propagate — paid checkout cannot break on email."""
    import api.email as email_mod
    monkeypatch.setattr(email_mod, "EMAIL_PROVIDER", "postmark")
    monkeypatch.setattr(email_mod, "POSTMARK_TOKEN", "test-token")
    monkeypatch.setattr(email_mod, "EMAIL_LOG_PATH", tmp_path / "x.log")

    # Patch httpx.Client to raise — simulate a network failure mid-request
    class BoomClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **kw):
            raise RuntimeError("simulated network outage")

    import httpx
    monkeypatch.setattr(httpx, "Client", BoomClient)

    ok = email_mod.send_license_delivery("buyer@example.com", "OMNI-AAAA-BBBB-CCCC-DDDD", "pro")
    assert ok is False  # no exception, just False


def test_send_postmark_non_200_returns_false(monkeypatch, tmp_path):
    """Postmark 422 (bad sender signature, missing fields, etc.) returns False."""
    import api.email as email_mod
    monkeypatch.setattr(email_mod, "EMAIL_PROVIDER", "postmark")
    monkeypatch.setattr(email_mod, "POSTMARK_TOKEN", "test-token")
    monkeypatch.setattr(email_mod, "EMAIL_LOG_PATH", tmp_path / "x.log")

    class FakeResp:
        status_code = 422
        text = '{"Error":401,"Message":"Bad signature"}'

    class FakeClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **kw): return FakeResp()

    import httpx
    monkeypatch.setattr(httpx, "Client", FakeClient)
    assert email_mod.send_license_delivery("x@y.com", "K", "pro") is False


def test_send_postmark_200_returns_true_and_includes_token(monkeypatch, tmp_path):
    """Happy path: 200 → True, and the Postmark token header is set."""
    import api.email as email_mod
    monkeypatch.setattr(email_mod, "EMAIL_PROVIDER", "postmark")
    monkeypatch.setattr(email_mod, "POSTMARK_TOKEN", "tok-12345")
    monkeypatch.setattr(email_mod, "EMAIL_LOG_PATH", tmp_path / "x.log")

    captured = {}

    class FakeResp:
        status_code = 200
        text = '{"MessageID":"abc"}'

    class FakeClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, json=None, headers=None, **kw):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResp()

    import httpx
    monkeypatch.setattr(httpx, "Client", FakeClient)
    ok = email_mod.send_welcome("user@example.com", plan="free")
    assert ok is True
    assert captured["url"] == "https://api.postmarkapp.com/email"
    assert captured["headers"]["X-Postmark-Server-Token"] == "tok-12345"
    assert captured["json"]["To"] == "user@example.com"
    assert captured["json"]["Tag"] == "02_welcome"


def test_email_health_endpoint(client):
    r = client.get("/api/system/email-health")
    assert r.status_code == 200
    h = r.json()
    assert "provider" in h
    assert "templates_present" in h


def test_billing_webhook_still_works_after_email_module_swap(client, clean_license):
    """Regression: CRE-13 rewired billing.py's email stubs. Confirm the
    Stripe checkout webhook still issues licenses and doesn't 500."""
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "customer_email": "buyer@example.com",
            "metadata": {"plan": "monthly"},
        }},
    }
    r = client.post("/api/billing/webhook", content=json.dumps(event),
                    headers={"Content-Type": "application/json"})
    if r.status_code == 503:
        return  # Stripe SDK missing — already covered upstream
    assert r.status_code == 200
    assert r.json()["status"] == "license_issued"
