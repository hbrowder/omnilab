"""First-run wizard tests (CRE-15)."""
import pytest


@pytest.fixture()
def fresh_settings():
    """Reset the settings row so each test sees an unconfigured install."""
    import asyncio

    import aiosqlite
    from core.config import settings as cfg

    async def _reset():
        async with aiosqlite.connect(str(cfg.DB_PATH)) as db:
            await db.execute(
                "UPDATE settings SET first_run_complete = 0, "
                "admin_password_hash = NULL, telemetry_enabled = 0, "
                "updated_at = NULL WHERE id = 1"
            )
            await db.commit()

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_reset())
    yield


def test_first_run_starts_incomplete(client, fresh_settings):
    r = client.get("/api/system/first-run")
    assert r.status_code == 200
    assert r.json() == {"complete": False}


def test_complete_persists_password_and_telemetry(client, fresh_settings):
    r = client.post("/api/system/first-run/complete", json={
        "password": "correct horse battery staple",
        "telemetry": True,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "complete"
    assert body["telemetry"] is True
    assert body["license"] is None

    # Status flips to complete
    assert client.get("/api/system/first-run").json() == {"complete": True}


def test_complete_is_idempotent_409_on_second_call(client, fresh_settings):
    payload = {"password": "first-password-ok", "telemetry": False}
    assert client.post("/api/system/first-run/complete", json=payload).status_code == 201
    r = client.post("/api/system/first-run/complete", json=payload)
    assert r.status_code == 409
    assert "already complete" in r.text.lower()


def test_complete_rejects_short_password(client, fresh_settings):
    r = client.post("/api/system/first-run/complete", json={
        "password": "short", "telemetry": False,
    })
    assert r.status_code == 422  # pydantic min_length


def test_complete_rejects_overlong_password(client, fresh_settings):
    # 73 ASCII bytes — one over the bcrypt cap
    long_pw = "a" * 73
    r = client.post("/api/system/first-run/complete", json={
        "password": long_pw, "telemetry": False,
    })
    assert r.status_code == 400
    assert "too long" in r.text.lower()


def test_password_is_hashed_not_stored_plain(client, fresh_settings):
    pw = "plaintext-must-not-survive"
    client.post("/api/system/first-run/complete", json={
        "password": pw, "telemetry": False,
    })
    # Inspect the DB directly to confirm we stored a bcrypt hash, not the password
    import asyncio

    import aiosqlite
    from core.config import settings as cfg

    async def _read():
        async with aiosqlite.connect(str(cfg.DB_PATH)) as db:
            async with db.execute(
                "SELECT admin_password_hash FROM settings WHERE id = 1"
            ) as cur:
                return (await cur.fetchone())[0]

    stored = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_read())
    assert stored is not None
    assert pw not in stored
    assert stored.startswith("$2"), f"expected bcrypt hash, got: {stored[:20]!r}"

    # And the hash verifies against the original password
    import bcrypt
    assert bcrypt.checkpw(pw.encode(), stored.encode())


def test_complete_with_valid_license_activates(client, fresh_settings, clean_license):
    from api.license import generate_key
    key = generate_key("pro", "user")
    r = client.post("/api/system/first-run/complete", json={
        "password": "wizard-with-license",
        "telemetry": False,
        "license_key": key,
    })
    assert r.status_code == 201
    body = r.json()
    assert body["license"] == {"activated": True, "plan": "pro"}

    # License status endpoint reflects the activation
    s = client.get("/api/license/status").json()
    assert s["activated"] is True
    assert s["plan"] == "pro"


def test_complete_with_invalid_license_still_completes_setup(client, fresh_settings, clean_license):
    """Bad license shouldn't block the wizard from finishing the rest of setup."""
    r = client.post("/api/system/first-run/complete", json={
        "password": "wizard-bad-license",
        "telemetry": False,
        "license_key": "OMNI-FAKE-FAKE-FAKE-FAKE",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "complete"
    assert body["license"]["activated"] is False
    assert "invalid" in body["license"]["error"].lower()

    # Setup still marked complete
    assert client.get("/api/system/first-run").json()["complete"] is True
