"""
Shared pytest fixtures for the OmniLab backend test suite (CRE-34).

Key isolation strategy:
- HOME is redirected to a per-session tmp dir BEFORE backend modules import,
  so `core.config.Settings.BASE_DIR = Path.home() / ".omnilab"` lands in tmp.
- OMNILAB_LICENSE_DIR points at a per-session tmp dir so license artifacts
  (.license_secret, .license.json) never touch the real backend/ dir.
- The backend dir is added to sys.path so `from main import app` works.
- A fresh SQLite DB is created per test session via init_db().
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# --- isolation: redirect HOME and license dir BEFORE backend imports ---
_TEST_HOME = tempfile.mkdtemp(prefix="omnilab-test-home-")
_TEST_LICENSE_DIR = tempfile.mkdtemp(prefix="omnilab-test-lic-")
os.environ["HOME"] = _TEST_HOME
os.environ["OMNILAB_LICENSE_DIR"] = _TEST_LICENSE_DIR

# Stop Stripe init from doing anything real
os.environ.pop("STRIPE_SECRET_KEY", None)
os.environ.pop("STRIPE_WEBHOOK_SECRET", None)

# Make the backend importable as a top-level package set
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _REPO_ROOT / "backend"
sys.path.insert(0, str(_BACKEND))

# Now import the app (this triggers core.config.Settings() which mkdir's
# under our redirected HOME, and license.py which reads OMNILAB_LICENSE_DIR).
from core.database import init_db  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_database():
    """Initialize the SQLite schema once per test session."""
    import asyncio
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(init_db())
    yield


@pytest.fixture()
def client():
    """A FastAPI TestClient bound to the real app.

    TestClient uses httpx under the hood and runs the lifespan handler, so
    init_db() executes again here — that's fine, CREATE TABLE IF NOT EXISTS
    is idempotent.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def clean_license():
    """Ensure no .license.json exists before/after a test that activates one."""
    from api.license import LICENSE_FILE
    if os.path.exists(LICENSE_FILE):
        os.remove(LICENSE_FILE)
    yield
    if os.path.exists(LICENSE_FILE):
        os.remove(LICENSE_FILE)


@pytest.fixture()
def fresh_db():
    """Drop and re-create all tables between tests that need a clean slate."""
    import asyncio

    import aiosqlite
    from core.config import settings

    async def _wipe():
        async with aiosqlite.connect(str(settings.DB_PATH)) as db:
            for table in ("links", "nodes", "labs"):
                await db.execute(f"DELETE FROM {table}")
            await db.commit()

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_wipe())
    yield
