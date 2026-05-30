"""
backend/api/settings.py  —  Operator settings (CRE-45 / AILB-5)

Exposes the BYO-key AI provider config:
  - GET  /api/settings/ai-provider  -> config WITHOUT the key (api_key_set bool)
  - POST /api/settings/ai-provider  -> persist (api_key WRITE-ONLY, encrypted)
  - POST /api/agent/test            -> ping the configured provider {ok, latency_ms, model}

The api_key is never echoed in any response. The provider ping uses a single
mockable seam (``_ping_provider``) so tests never make a real paid call.
"""
from __future__ import annotations

import time

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field
from services import ai_provider

# /api/settings/ai-provider lives here.
router = APIRouter()

# /api/agent/test lives on its own router so it mounts under the agent prefix
# (same /api/agent/* family as /api/agent/build), keeping the runner-facing
# endpoints together.
agent_test_router = APIRouter(prefix="/api/agent", tags=["agent"])


# ============================================================================
# Models
# ============================================================================

class AIProviderUpdate(BaseModel):
    provider: str | None = Field(default=None)
    # WRITE-ONLY. None = leave existing key untouched; "" = clear; value = set.
    api_key: str | None = Field(default=None)
    model: str | None = Field(default=None)
    base_url: str | None = Field(default=None)


# ============================================================================
# GET / POST /api/settings/ai-provider
# ============================================================================

@router.get("/ai-provider")
def get_ai_provider() -> dict:
    """Return the stored AI-provider config WITHOUT the api_key.

    Fresh install with no key -> ``api_key_set: false`` so the UI can treat the
    AI builder as disabled and prompt the operator to configure a provider."""
    return ai_provider.get_config()


@router.post("/ai-provider")
def update_ai_provider(body: AIProviderUpdate) -> dict:
    """Persist the AI-provider config. The api_key is encrypted at rest and is
    NEVER echoed back — the response is the same redacted shape as GET."""
    try:
        return ai_provider.save_config(
            provider=body.provider,
            api_key=body.api_key,
            model=body.model,
            base_url=body.base_url,
        )
    except ValueError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# POST /api/agent/test  —  provider connectivity ping
# ============================================================================

def _ping_provider(creds: dict) -> dict:
    """Send a minimal request to the configured provider and return its model.

    This is the SINGLE network seam. Unit tests monkeypatch this so NO real
    (paid) call is made. Returns {"model": <model>}; raises on failure. The
    api_key is never included in any raised message (callers redact too).
    """
    provider = creds["provider"]
    api_key = creds["api_key"]
    model = creds["model"]
    base_url = (creds.get("base_url") or "").rstrip("/")

    if provider == "anthropic":
        # Anthropic Messages API: a tiny 1-token completion.
        url = f"{base_url}/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }
    else:
        # OpenAI-compatible (openrouter / openai / custom) chat/completions.
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://omnilab.local"
            headers["X-Title"] = "OmniLab Lab Builder"
        payload = {
            "model": model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }

    resp = httpx.post(url, headers=headers, json=payload, timeout=20.0)
    resp.raise_for_status()
    return {"model": model}


def _redact(text: str, api_key: str | None) -> str:
    if not text or not api_key:
        return text
    return text.replace(api_key, "***REDACTED***").replace(
        f"Bearer {api_key}", "Bearer ***REDACTED***"
    )


@agent_test_router.post("/test")
def test_ai_provider() -> dict:
    """Ping the configured provider. Returns {ok, latency_ms, model} on success
    or {ok: false, error} on failure. Never makes a real call in tests (the
    ``_ping_provider`` seam is mocked). The api_key never appears in output."""
    creds = ai_provider.resolve_credentials()
    if not creds:
        return {
            "ok": False,
            "error": "No AI provider configured. Configure your AI provider in Settings.",
        }

    api_key = creds["api_key"]
    start = time.perf_counter()
    try:
        result = _ping_provider(creds)
    except httpx.HTTPStatusError as e:
        msg = _redact(
            f"Provider returned HTTP {e.response.status_code}", api_key
        )
        return {"ok": False, "error": msg, "model": creds["model"]}
    except httpx.HTTPError as e:
        msg = _redact(f"Connection failed: {e}", api_key)
        return {"ok": False, "error": msg, "model": creds["model"]}
    except Exception as e:  # noqa: BLE001 — never leak the key on any failure
        msg = _redact(f"Unexpected error: {e}", api_key)
        return {"ok": False, "error": msg, "model": creds["model"]}

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    return {"ok": True, "latency_ms": latency_ms, "model": result["model"]}
