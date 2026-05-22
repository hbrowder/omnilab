"""
OmniLab Auto-Update Checker API
Privacy-first: only checks for updates, never installs.
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

CURRENT_VERSION = "1.0.0"
UPDATE_FEED_URL = "https://omnilab.io/api/releases/latest"
UPDATE_FEED_TIMEOUT = 5  # seconds
USER_AGENT = f"OmniLab/{CURRENT_VERSION}"

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPDATE_STATE_FILE = os.path.join(BACKEND_ROOT, ".updates_state.json")


def _load_state():
    """Load the saved update state (last check, snoozed version, etc)."""
    if not os.path.exists(UPDATE_STATE_FILE):
        return {
            "enabled": True,
            "frequency_days": 1,
            "last_check": None,
            "last_known_version": None,
            "snoozed_version": None,
        }
    try:
        with open(UPDATE_STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"enabled": True, "frequency_days": 1}


def _save_state(state):
    with open(UPDATE_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _parse_version(v):
    """Parse 'v1.2.3' or '1.2.3' into a tuple (1, 2, 3) for comparison."""
    if not v:
        return (0, 0, 0)
    v = v.lstrip("v")
    parts = re.findall(r"\d+", v)
    return tuple(int(p) for p in parts[:3]) + (0,) * max(0, 3 - len(parts))


def _is_newer(latest, current):
    """Return True if 'latest' is strictly newer than 'current'."""
    return _parse_version(latest) > _parse_version(current)


@router.get("/check")
async def check_for_updates(force: bool = False):
    """
    Check for a newer OmniLab version. Honors the configured frequency
    unless force=true. Returns cached result if checked recently.
    """
    state = _load_state()

    if not state.get("enabled", True):
        return {
            "current": CURRENT_VERSION,
            "available": False,
            "enabled": False,
            "message": "Update checks are disabled",
        }

    # Respect check frequency
    if not force and state.get("last_check"):
        try:
            last = datetime.fromisoformat(state["last_check"])
            if (datetime.now(timezone.utc) - last) < timedelta(days=state.get("frequency_days", 1)):
                # Return cached result
                cached_version = state.get("last_known_version")
                if cached_version:
                    return {
                        "current": CURRENT_VERSION,
                        "latest": cached_version,
                        "available": _is_newer(cached_version, CURRENT_VERSION),
                        "cached": True,
                        "last_check": state["last_check"],
                        "snoozed": state.get("snoozed_version") == cached_version,
                    }
        except Exception:
            pass

    # Make the actual check
    try:
        r = requests.get(
            UPDATE_FEED_URL,
            timeout=UPDATE_FEED_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        data = r.json()
        latest = data.get("version", CURRENT_VERSION)

        # Update state
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        state["last_known_version"] = latest
        _save_state(state)

        return {
            "current": CURRENT_VERSION,
            "latest": latest,
            "available": _is_newer(latest, CURRENT_VERSION),
            "released_at": data.get("released_at"),
            "notes_url": data.get("notes_url"),
            "download_url": data.get("download_url"),
            "highlights": data.get("highlights", []),
            "snoozed": state.get("snoozed_version") == latest,
            "cached": False,
        }
    except requests.RequestException as e:
        # Silent fail - don't bother user with network issues
        return {
            "current": CURRENT_VERSION,
            "available": False,
            "error": "Could not reach update server",
            "_debug": str(e),
        }


@router.get("/settings")
async def get_update_settings():
    """Get current auto-update check settings."""
    state = _load_state()
    return {
        "enabled": state.get("enabled", True),
        "frequency_days": state.get("frequency_days", 1),
        "last_check": state.get("last_check"),
        "feed_url": UPDATE_FEED_URL,
        "current_version": CURRENT_VERSION,
    }


class UpdateSettings(BaseModel):
    enabled: bool | None = None
    frequency_days: int | None = None


@router.post("/settings")
async def update_settings(payload: UpdateSettings):
    """Change update check preferences."""
    state = _load_state()
    if payload.enabled is not None:
        state["enabled"] = payload.enabled
    if payload.frequency_days is not None:
        if payload.frequency_days < 1 or payload.frequency_days > 30:
            raise HTTPException(status_code=400, detail="frequency_days must be between 1 and 30")
        state["frequency_days"] = payload.frequency_days
    _save_state(state)
    return {"status": "saved", "settings": state}


class SnoozeRequest(BaseModel):
    version: str


@router.post("/snooze")
async def snooze_version(payload: SnoozeRequest):
    """
    Hide the update notification for this specific version. User can still
    see it via System -> Updates, but the corner badge stops nagging.
    """
    state = _load_state()
    state["snoozed_version"] = payload.version
    _save_state(state)
    return {"status": "snoozed", "version": payload.version}


@router.post("/dismiss")
async def dismiss_session():
    """
    One-session dismissal. The frontend tracks this in sessionStorage,
    so this endpoint is purely a no-op acknowledgment.
    """
    return {"status": "ok"}
