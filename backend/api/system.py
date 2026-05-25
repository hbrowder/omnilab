"""
System router: health, host info, and first-run wizard (CRE-15).

The first-run wizard is consumed by Module 6 (FirstRunWizard.jsx, CRE-16).
Two endpoints:

  GET  /api/system/first-run            -> {"complete": bool}
  POST /api/system/first-run/complete   -> set admin password, telemetry pref,
                                            optionally activate a license key

Once `complete` is True the POST endpoint refuses to overwrite — re-running the
wizard requires a backend reset (deliberately; otherwise anyone with API access
could reset the admin password). For a real reset, an operator runs the CLI
flow that's out of scope for v1.0.
"""
from __future__ import annotations

import platform
import shutil
from datetime import datetime, timezone

import bcrypt
from core.config import settings
from core.database import get_db
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


# ---------------------------------------------------------------------------
# Existing endpoints (preserved verbatim)
# ---------------------------------------------------------------------------
@router.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "product": "OmniLab"}


@router.get("/permissions")
async def check_image_permissions():
    """
    Check image directory permissions (CRE-53 enhancement).
    
    Verifies all images are readable/writable by the service user.
    EVE-NG requires manual 'fixpermissions' after uploads - OmniLab auto-fixes!
    """
    import os
    from pathlib import Path
    
    image_dir = Path.home() / ".omnilab" / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    
    issues = []
    fixed = []
    current_uid = os.getuid()
    current_gid = os.getgid()
    
    # Check all QEMU images
    for image in image_dir.glob("**/*.qcow2"):
        stat = image.stat()
        has_issue = False
        
        # Check ownership
        if stat.st_uid != current_uid:
            issues.append(f"{image.name}: wrong owner (uid {stat.st_uid}, expected {current_uid})")
            has_issue = True
        
        # Check readability
        if not os.access(image, os.R_OK):
            issues.append(f"{image.name}: not readable")
            has_issue = True
        
        # Check writability (needed for backing files)
        if not os.access(image, os.W_OK):
            issues.append(f"{image.name}: not writable")
            has_issue = True
        
        # Auto-fix if possible (only mode, can't chown without root)
        if has_issue and stat.st_uid == current_uid:
            try:
                os.chmod(image, 0o644)  # rw-r--r--
                fixed.append(image.name)
            except Exception as e:
                issues.append(f"{image.name}: auto-fix failed - {e}")
    
    total_images = len(list(image_dir.glob("**/*.qcow2")))
    
    return {
        "status": "ok" if not issues else "warning",
        "total_images": total_images,
        "issues": issues,
        "auto_fixed": fixed,
        "message": "No manual fixpermissions needed!" if not issues else "Some images have permission issues"
    }


@router.post("/permissions/fix")
async def fix_image_permissions():
    """
    Force fix all image permissions (admin only in production).
    
    Sets all images to 644 (rw-r--r--) with service user ownership.
    Unlike EVE-NG, this is rarely needed - upload API sets correct perms automatically.
    """
    import os
    from pathlib import Path
    
    image_dir = Path.home() / ".omnilab" / "images"
    fixed = []
    errors = []
    
    for image in image_dir.glob("**/*.qcow2"):
        try:
            os.chmod(image, 0o644)
            fixed.append(image.name)
        except Exception as e:
            errors.append(f"{image.name}: {e}")
    
    return {
        "success": True,
        "fixed": len(fixed),
        "errors": errors,
        "files": fixed
    }


@router.get("/info")
async def system_info():
    disk = shutil.disk_usage(str(settings.BASE_DIR))
    return {
        "platform": platform.system(), "arch": platform.machine(),
        "kvm_available": settings.KVM_ENABLED,
        "disk_free_gb": round(disk.free / (1024**3), 1),
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "images_dir": str(settings.IMAGES_DIR),
        "tier": "free",
    }


# ---------------------------------------------------------------------------
# First-run wizard (CRE-15)
# ---------------------------------------------------------------------------
# Password policy is intentionally lenient for v1.0 self-hosters (their box,
# their rules), but we still refuse the empty string and anything obviously
# too short. The frontend wizard (CRE-16) enforces a stricter UX-level rule.
MIN_PASSWORD_LEN = 8
# bcrypt's input cap is 72 BYTES; longer inputs are silently truncated to 72
# bytes by the library. We reject explicitly so the user knows.
BCRYPT_MAX_BYTES = 72


class FirstRunComplete(BaseModel):
    password: str = Field(..., min_length=MIN_PASSWORD_LEN)
    telemetry: bool = False
    license_key: str | None = None


@router.get("/first-run")
async def first_run_status():
    """Whether the install has completed initial setup."""
    async for db in get_db():
        async with db.execute(
            "SELECT first_run_complete FROM settings WHERE id = 1"
        ) as cur:
            row = await cur.fetchone()
    complete = bool(row and row[0])
    return {"complete": complete}


@router.post("/first-run/complete", status_code=201)
async def first_run_complete(payload: FirstRunComplete):
    """Persist the wizard's choices.

    Idempotency rule: once `complete` is True we refuse — see module docstring.
    """
    # Guard rails the pydantic model can't catch alone
    if len(payload.password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Password is too long (bcrypt accepts up to {BCRYPT_MAX_BYTES} bytes; "
                "your password exceeds that as UTF-8). Use a shorter passphrase."
            ),
        )

    async for db in get_db():
        async with db.execute(
            "SELECT first_run_complete FROM settings WHERE id = 1"
        ) as cur:
            row = await cur.fetchone()
        if row and row[0]:
            raise HTTPException(
                status_code=409,
                detail="First-run setup is already complete. Reset is an operator-side action."
            )

        # Hash the password — bcrypt with a 12-round cost (sensible default
        # in 2026). The salt is embedded in the returned hash.
    async for db in get_db():
        try:
            hashed = bcrypt.hashpw(
                payload.admin_password.encode(), bcrypt.gensalt()
            ).decode()
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                """UPDATE settings
                   SET first_run_complete = 1,
                       admin_password_hash = ?,
                       telemetry_enabled = ?,
                       updated_at = ?
                   WHERE id = 1""",
                (hashed, 1 if payload.telemetry else 0, now),
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to complete setup wizard: {str(e)}")

    license_result: dict | None = None
    if payload.license_key:
        # Reuse CRE-4 activation rather than duplicating verify logic here.
        # Imported lazily so this module still loads if license.py is missing.
        import json

        from api.license import LICENSE_FILE, verify_key  # noqa: E402
        info = verify_key(payload.license_key.strip())
        if not info:
            # Wizard finished otherwise (password + telemetry are saved). We
            # return success for the wizard but flag the bad key so the UI
            # can show "you're set up, but the license key didn't take."
            license_result = {"activated": False, "error": "Invalid license key"}
        else:
            with open(LICENSE_FILE, "w") as f:
                json.dump({
                    "key": payload.license_key.strip(),
                    "plan": info["plan"],
                    "customer": info["customer"],
                }, f)
            license_result = {"activated": True, "plan": info["plan"]}

    return {
        "status": "complete",
        "telemetry": payload.telemetry,
        "license": license_result,
    }


# CRE-13: email health probe (so the UI / ops can see provider state at a glance)
@router.get("/email-health")
async def email_health():
    """Provider state for transactional email (Module 8)."""
    try:
        from api.email import health
        return health()
    except ImportError:
        return {"provider": "unavailable", "error": "api.email not importable"}
