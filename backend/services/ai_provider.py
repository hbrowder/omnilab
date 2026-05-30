"""
backend/services/ai_provider.py  —  BYO-key AI provider config (CRE-45 / AILB-5)

Operators bring their own LLM key so we never bake ours into the .deb. The
config (provider, model, base_url, and the WRITE-ONLY api_key) is persisted to
``~/.omnilab/.ai_provider.json``, with the api_key encrypted at rest using
**Fernet**. The Fernet key is *derived* from the same ``.license_secret`` the
license code manages (we only READ that secret; we never touch license logic).

Security invariants:
- The api_key is encrypted at rest (Fernet), never stored in plaintext.
- The file is written with 0600 perms.
- The api_key is NEVER echoed by the GET endpoint — only ``api_key_set`` (bool)
  and (optionally) a ``last4`` derived from the decrypted key.
- The key is never logged.

This module is intentionally framework-free (no FastAPI) so the agent runner can
import it without pulling in the web layer.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

# ============================================================================
# Paths — mirror api/license.py's secret-file pattern.
# ============================================================================

# The license secret lives under OMNILAB_LICENSE_DIR (default: backend/), and
# is created on first run by api/license.py exactly as below. We mirror that
# pattern so we work whether or not license.py has been imported yet.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LICENSE_DIR = os.environ.get("OMNILAB_LICENSE_DIR", _BACKEND_DIR)
SECRET_FILE = os.path.join(LICENSE_DIR, ".license_secret")

# Config file lives under the user data dir (~/.omnilab), like the rest of the
# runtime state. Honors HOME redirection used by the test harness.
CONFIG_DIR = Path.home() / ".omnilab"
CONFIG_FILE = CONFIG_DIR / ".ai_provider.json"

# ============================================================================
# Provider catalog — per-provider sensible model defaults.
# ============================================================================

PROVIDERS = ("openrouter", "anthropic", "openai", "custom")

DEFAULT_MODELS: dict[str, str] = {
    "openrouter": "anthropic/claude-sonnet-4.5",
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4o",
    "custom": "",
}

DEFAULT_BASE_URLS: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "openai": "https://api.openai.com/v1",
    "custom": "",
}

DEFAULT_PROVIDER = "openrouter"


# ============================================================================
# Fernet key derivation from .license_secret
# ============================================================================

def _read_license_secret() -> bytes:
    """Read the .license_secret, creating it the SAME way api/license.py does
    if it's missing. We only ever read/create the secret file — we never touch
    license/billing/auth logic."""
    os.makedirs(LICENSE_DIR, exist_ok=True)
    if not os.path.exists(SECRET_FILE):
        # Mirror api/license.py: 64 hex chars (32 bytes) of randomness.
        import secrets

        with open(SECRET_FILE, "w") as f:
            f.write(secrets.token_hex(32))
    with open(SECRET_FILE) as f:
        return f.read().strip().encode()


def _fernet() -> Fernet:
    """Derive a stable 32-byte urlsafe-base64 Fernet key from the license
    secret. The secret is high-entropy already; we hash it (with a domain-
    separation label) to get exactly 32 bytes for Fernet."""
    secret = _read_license_secret()
    digest = hashlib.sha256(b"omnilab.ai_provider.v1:" + secret).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def _decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        return None


# ============================================================================
# Persistence
# ============================================================================

def _read_raw() -> dict[str, Any]:
    """Read the on-disk config (with the encrypted key). Returns {} if absent
    or corrupt."""
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_raw(data: dict[str, Any]) -> None:
    """Write the config atomically with 0600 perms."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".json.tmp")
    # Create with restrictive perms from the start (umask-independent).
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    os.replace(tmp, CONFIG_FILE)
    os.chmod(CONFIG_FILE, 0o600)


# ============================================================================
# Public API
# ============================================================================

def get_config() -> dict[str, Any]:
    """Return the stored config WITHOUT the api_key.

    Shape: {provider, model, base_url, api_key_set, last4?}. The api_key is
    NEVER included — only the boolean ``api_key_set`` (and ``last4`` if a key
    is present, to help the operator confirm which key is stored)."""
    raw = _read_raw()
    provider = raw.get("provider") or DEFAULT_PROVIDER
    if provider not in PROVIDERS:
        provider = DEFAULT_PROVIDER
    model = raw.get("model") or DEFAULT_MODELS.get(provider, "")
    base_url = raw.get("base_url") or DEFAULT_BASE_URLS.get(provider, "")

    out: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key_set": False,
    }
    enc = raw.get("api_key_enc")
    if enc:
        out["api_key_set"] = True
        key = _decrypt(enc)
        if key:
            out["last4"] = key[-4:]
    return out


def save_config(*, provider: str | None = None, api_key: str | None = None,
                model: str | None = None, base_url: str | None = None) -> dict[str, Any]:
    """Persist the config. The api_key is encrypted at rest.

    - ``provider`` defaults the model/base_url if those are not supplied.
    - ``api_key``: if a non-empty string is given it is encrypted and stored;
      if ``None`` the existing stored key is preserved; if an empty string the
      stored key is CLEARED.
    Returns the same redacted shape as ``get_config()``."""
    raw = _read_raw()

    if provider is not None:
        if provider not in PROVIDERS:
            raise ValueError(f"unknown provider {provider!r}")
        raw["provider"] = provider

    eff_provider = raw.get("provider") or DEFAULT_PROVIDER

    if model is not None:
        raw["model"] = model.strip()
    if not raw.get("model"):
        raw["model"] = DEFAULT_MODELS.get(eff_provider, "")

    if base_url is not None:
        raw["base_url"] = base_url.strip()
    if not raw.get("base_url"):
        raw["base_url"] = DEFAULT_BASE_URLS.get(eff_provider, "")

    if api_key is not None:
        if api_key.strip():
            raw["api_key_enc"] = _encrypt(api_key.strip())
        else:
            # Empty string -> explicit clear.
            raw.pop("api_key_enc", None)

    _write_raw(raw)
    return get_config()


def resolve_credentials() -> dict[str, Any] | None:
    """Return decrypted credentials for the runner, or None if no key is set.

    Shape: {provider, api_key, model, base_url}. This is the ONLY function that
    returns the plaintext key, and only in-process to the runner — it is never
    serialized to a client."""
    raw = _read_raw()
    enc = raw.get("api_key_enc")
    if not enc:
        return None
    key = _decrypt(enc)
    if not key:
        return None
    provider = raw.get("provider") or DEFAULT_PROVIDER
    if provider not in PROVIDERS:
        provider = DEFAULT_PROVIDER
    model = raw.get("model") or DEFAULT_MODELS.get(provider, "")
    base_url = raw.get("base_url") or DEFAULT_BASE_URLS.get(provider, "")
    return {
        "provider": provider,
        "api_key": key,
        "model": model,
        "base_url": base_url,
    }
