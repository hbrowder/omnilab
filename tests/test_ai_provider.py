"""
Tests for the BYO-key AI provider config (CRE-45 / AILB-5).

Coverage:
- POST then GET /api/settings/ai-provider: the api_key is NEVER echoed; the
  api_key_set boolean flips true after a POST with a key.
- Fernet encrypt/decrypt round-trip; the on-disk file holds ciphertext, not the
  plaintext key.
- The config file is written with 0600 perms.
- /api/agent/test with the provider call MOCKED (no real HTTP) -> {ok, latency_ms, model}.
- Redaction: the api_key string never appears in any response or error body.
- The runner resolves the stored (decrypted) config.

Every provider network call is mocked. No real (paid) request is ever made and
no real key is committed.
"""
from __future__ import annotations

import os
import stat

import pytest

# A fake key used everywhere — clearly not real, never charged.
FAKE_KEY = "sk-test-DO-NOT-CHARGE-1234567890abcdef-LAST4"


@pytest.fixture()
def clean_ai_config():
    """Remove the stored config before and after each test so state never
    leaks between tests (esp. into the runner's missing-key test)."""
    from services import ai_provider

    def _rm():
        try:
            os.remove(ai_provider.CONFIG_FILE)
        except OSError:
            pass

    _rm()
    yield
    _rm()


# ============================================================================
# Module-level: encryption round-trip and file perms
# ============================================================================

def test_encrypt_decrypt_roundtrip(clean_ai_config):
    from services import ai_provider

    token = ai_provider._encrypt(FAKE_KEY)
    assert token != FAKE_KEY  # ciphertext, not plaintext
    assert FAKE_KEY not in token
    assert ai_provider._decrypt(token) == FAKE_KEY


def test_decrypt_bad_token_returns_none(clean_ai_config):
    from services import ai_provider

    assert ai_provider._decrypt("not-a-valid-fernet-token") is None


def test_saved_file_has_0600_perms_and_ciphertext(clean_ai_config):
    from services import ai_provider

    ai_provider.save_config(provider="openrouter", api_key=FAKE_KEY)
    assert os.path.exists(ai_provider.CONFIG_FILE)

    mode = stat.S_IMODE(os.stat(ai_provider.CONFIG_FILE).st_mode)
    assert mode == 0o600, f"expected 0600, got {oct(mode)}"

    # The plaintext key must NOT appear anywhere in the file.
    raw_bytes = open(ai_provider.CONFIG_FILE, "rb").read()
    assert FAKE_KEY.encode() not in raw_bytes


def test_resolve_credentials_returns_decrypted_key(clean_ai_config):
    from services import ai_provider

    assert ai_provider.resolve_credentials() is None  # nothing stored yet
    ai_provider.save_config(provider="anthropic", api_key=FAKE_KEY,
                            model="claude-sonnet-4-5")
    creds = ai_provider.resolve_credentials()
    assert creds["api_key"] == FAKE_KEY
    assert creds["provider"] == "anthropic"
    assert creds["model"] == "claude-sonnet-4-5"


# ============================================================================
# GET / POST endpoint behavior
# ============================================================================

def test_get_fresh_install_reports_disabled(client, clean_ai_config):
    r = client.get("/api/settings/ai-provider")
    assert r.status_code == 200
    body = r.json()
    assert body["api_key_set"] is False
    assert body["provider"] == "openrouter"  # default
    assert "api_key" not in body  # never present


def test_post_then_get_sets_key_without_echoing_it(client, clean_ai_config):
    # POST a key.
    r = client.post("/api/settings/ai-provider", json={
        "provider": "openrouter",
        "api_key": FAKE_KEY,
        "model": "anthropic/claude-sonnet-4.5",
    })
    assert r.status_code == 200
    body = r.json()
    # The POST response is the redacted shape — the key is NEVER echoed.
    assert "api_key" not in body
    assert FAKE_KEY not in r.text
    assert body["api_key_set"] is True

    # GET reflects api_key_set true, still no key.
    r2 = client.get("/api/settings/ai-provider")
    body2 = r2.json()
    assert body2["api_key_set"] is True
    assert "api_key" not in body2
    assert FAKE_KEY not in r2.text
    # Only a last4 hint, if any.
    if "last4" in body2:
        assert body2["last4"] == FAKE_KEY[-4:]
        assert len(body2["last4"]) == 4


def test_post_empty_key_clears_it(client, clean_ai_config):
    client.post("/api/settings/ai-provider", json={"api_key": FAKE_KEY})
    assert client.get("/api/settings/ai-provider").json()["api_key_set"] is True
    # Empty string clears the stored key.
    client.post("/api/settings/ai-provider", json={"api_key": ""})
    assert client.get("/api/settings/ai-provider").json()["api_key_set"] is False


def test_post_without_key_preserves_existing_key(client, clean_ai_config):
    client.post("/api/settings/ai-provider", json={"api_key": FAKE_KEY})
    # Update only the model; omit api_key entirely (None) -> key preserved.
    r = client.post("/api/settings/ai-provider", json={"model": "some/model"})
    body = r.json()
    assert body["api_key_set"] is True
    assert body["model"] == "some/model"


def test_post_invalid_provider_rejected(client, clean_ai_config):
    r = client.post("/api/settings/ai-provider", json={"provider": "bogus"})
    assert r.status_code == 400


def test_provider_default_model_applied(client, clean_ai_config):
    r = client.post("/api/settings/ai-provider", json={"provider": "openai"})
    assert r.json()["model"] == "gpt-4o"


# ============================================================================
# /api/agent/test — provider ping, MOCKED (no real HTTP)
# ============================================================================

def test_agent_test_no_key_returns_not_ok(client, clean_ai_config):
    r = client.post("/api/agent/test")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "Settings" in body["error"]


def test_agent_test_success_is_mocked(client, clean_ai_config, monkeypatch):
    from api import settings as settings_api

    captured = {}

    def fake_ping(creds):
        # Assert the runner-facing creds carry the decrypted key but DON'T
        # leak it anywhere observable.
        captured["api_key"] = creds["api_key"]
        return {"model": creds["model"]}

    monkeypatch.setattr(settings_api, "_ping_provider", fake_ping)

    client.post("/api/settings/ai-provider", json={
        "provider": "openrouter", "api_key": FAKE_KEY,
        "model": "anthropic/claude-sonnet-4.5",
    })
    r = client.post("/api/agent/test")
    body = r.json()
    assert body["ok"] is True
    assert body["model"] == "anthropic/claude-sonnet-4.5"
    assert isinstance(body["latency_ms"], (int, float))
    # The mock saw the real key in-process (expected), but it must not be in
    # the HTTP response.
    assert captured["api_key"] == FAKE_KEY
    assert FAKE_KEY not in r.text


def test_agent_test_failure_redacts_key(client, clean_ai_config, monkeypatch):
    import httpx
    from api import settings as settings_api

    def boom(creds):
        # Simulate a provider error whose message embeds the key (worst case).
        raise httpx.HTTPError(f"401 Unauthorized with key {creds['api_key']}")

    monkeypatch.setattr(settings_api, "_ping_provider", boom)

    client.post("/api/settings/ai-provider", json={
        "provider": "openrouter", "api_key": FAKE_KEY,
    })
    r = client.post("/api/agent/test")
    body = r.json()
    assert body["ok"] is False
    # The key must NEVER appear in the error, even though the exception
    # contained it.
    assert FAKE_KEY not in r.text
    assert FAKE_KEY not in body["error"]
    assert "REDACTED" in body["error"]


# ============================================================================
# Runner resolution + redaction
# ============================================================================

def test_runner_resolves_stored_config(clean_ai_config, monkeypatch):
    from services import agent_runner, ai_provider

    # No env key, so only the stored config can satisfy the runner.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    ai_provider.save_config(provider="openrouter", api_key=FAKE_KEY,
                            model="anthropic/claude-sonnet-4.5")

    cfg = agent_runner._resolve_config()
    assert cfg is not None
    assert cfg["api_key"] == FAKE_KEY
    assert cfg["model"] == "anthropic/claude-sonnet-4.5"
    assert cfg["base_url"].endswith("/chat/completions")


def test_runner_falls_back_to_env(clean_ai_config, monkeypatch):
    from services import agent_runner

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-env-fallback")
    cfg = agent_runner._resolve_config()
    assert cfg["api_key"] == "sk-env-fallback"
    assert cfg["base_url"] == agent_runner.OPENROUTER_URL


def test_runner_no_config_anywhere_returns_none(clean_ai_config, monkeypatch):
    from services import agent_runner

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(agent_runner, "_load_api_key", lambda: None)
    assert agent_runner._resolve_config() is None


def test_runner_uses_stored_key_end_to_end(clean_ai_config, monkeypatch):
    """run_build with no explicit api_key should pull the stored config and
    never leak the key into events."""
    from services import agent_runner, ai_provider

    from tests.test_agent_tools import FakeRepo

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    ai_provider.save_config(provider="openrouter", api_key=FAKE_KEY)

    seen_keys = {}

    def fake_chat(*, api_key, model, messages, tools_schema, max_tokens,
                  url=None, timeout=60.0):
        seen_keys["api_key"] = api_key
        seen_keys["url"] = url
        # A final text answer -> the loop finishes immediately.
        return {"choices": [{"message": {"content": "done", "tool_calls": []}}]}

    monkeypatch.setattr(agent_runner, "_chat_completion", fake_chat)

    events = list(agent_runner.run_build(FakeRepo(), "build a tiny lab"))
    # The stored key was used for the call.
    assert seen_keys["api_key"] == FAKE_KEY
    # No event leaks the key.
    for ev in events:
        assert FAKE_KEY not in str(ev)
    assert events[-1]["type"] == "done"
