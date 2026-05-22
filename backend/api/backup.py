"""
OmniLab Backup & Restore API
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import tarfile
import tempfile
import json
import os
import io
import shutil
import sqlite3
from datetime import datetime, timezone
import socket

router = APIRouter()

# Use the actual OmniLab data directory (~/.omnilab) from config
from core.config import settings as _settings
BASE_DIR = str(_settings.BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "omnilab.db")
# License module stores in backend/ not BASE_DIR (legacy quirk)
_LIC_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LICENSE_FILE = os.path.join(_LIC_BACKEND_ROOT, ".license.json")
LICENSE_SECRET = os.path.join(_LIC_BACKEND_ROOT, ".license_secret")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

ARCHIVE_VERSION = 1


@router.post("/export")
async def export_backup():
    """Create a .omnilab archive of all OmniLab state."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".omnilab")
    tmp.close()
    
    try:
        with tarfile.open(tmp.name, "w:gz") as tar:
            # Manifest
            manifest = _build_manifest()
            manifest_bytes = json.dumps(manifest, indent=2).encode()
            info = tarfile.TarInfo(name="manifest.json")
            info.size = len(manifest_bytes)
            tar.addfile(info, io.BytesIO(manifest_bytes))
            
            # SQLite database
            if os.path.exists(DB_PATH):
                tar.add(DB_PATH, arcname="omnilab.db")
            
            # License (if any)
            if os.path.exists(LICENSE_FILE):
                tar.add(LICENSE_FILE, arcname="license.json")
            if os.path.exists(LICENSE_SECRET):
                tar.add(LICENSE_SECRET, arcname="license_secret")
            
            # Settings
            if os.path.exists(SETTINGS_FILE):
                tar.add(SETTINGS_FILE, arcname="settings.json")
            
            # Individual lab JSON exports (redundant safety net)
            labs_data = _export_all_labs()
            for lab_id, lab_json in labs_data.items():
                lab_bytes = json.dumps(lab_json, indent=2).encode()
                info = tarfile.TarInfo(name=f"labs/lab-{lab_id}.json")
                info.size = len(lab_bytes)
                tar.addfile(info, io.BytesIO(lab_bytes))
        
        # Stream the file
        def iterfile():
            with open(tmp.name, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
            os.unlink(tmp.name)  # cleanup
        
        filename = f"omnilab-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.omnilab"
        return StreamingResponse(
            iterfile(),
            media_type="application/gzip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview")
async def preview_backup(file: UploadFile = File(...)):
    """Inspect a .omnilab archive without applying it."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".omnilab")
    tmp.write(await file.read())
    tmp.close()
    
    try:
        with tarfile.open(tmp.name, "r:gz") as tar:
            names = tar.getnames()
            
            # Read manifest
            try:
                manifest_member = tar.getmember("manifest.json")
                manifest_bytes = tar.extractfile(manifest_member).read()
                manifest = json.loads(manifest_bytes.decode())
            except (KeyError, Exception):
                manifest = {"warning": "No manifest found - older archive?"}
            
            # Count what's inside
            has_db = "omnilab.db" in names
            has_license = "license.json" in names
            has_settings = "settings.json" in names
            lab_files = [n for n in names if n.startswith("labs/")]
            
            return {
                "manifest": manifest,
                "contents": {
                    "database": has_db,
                    "license": has_license,
                    "settings": has_settings,
                    "lab_count": len(lab_files),
                    "total_files": len(names),
                },
                "size_bytes": os.path.getsize(tmp.name),
                "compatible": manifest.get("archive_version", 0) <= ARCHIVE_VERSION,
            }
    finally:
        os.unlink(tmp.name)


class RestoreOptions(BaseModel):
    overwrite_database: bool = True
    overwrite_license: bool = False
    overwrite_settings: bool = False


@router.post("/import")
async def restore_backup(file: UploadFile = File(...), 
                         overwrite_database: bool = True,
                         overwrite_license: bool = False,
                         overwrite_settings: bool = False):
    """Restore from a .omnilab archive. Be careful - this can overwrite data."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".omnilab")
    tmp.write(await file.read())
    tmp.close()
    
    restored = {"database": False, "license": False, "settings": False, "labs": 0}
    
    try:
        with tarfile.open(tmp.name, "r:gz") as tar:
            # Verify manifest
            try:
                manifest_bytes = tar.extractfile(tar.getmember("manifest.json")).read()
                manifest = json.loads(manifest_bytes.decode())
                if manifest.get("archive_version", 0) > ARCHIVE_VERSION:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Archive version {manifest['archive_version']} is newer than this OmniLab supports (max {ARCHIVE_VERSION})"
                    )
            except KeyError:
                raise HTTPException(status_code=400, detail="Invalid archive: no manifest")
            
            # Restore database
            if overwrite_database and "omnilab.db" in tar.getnames():
                db_member = tar.getmember("omnilab.db")
                # Backup current first
                if os.path.exists(DB_PATH):
                    shutil.copy(DB_PATH, DB_PATH + ".pre-restore.bak")
                with open(DB_PATH, "wb") as f:
                    f.write(tar.extractfile(db_member).read())
                restored["database"] = True
            
            # Restore license
            if overwrite_license:
                for member_name, target_path in [("license.json", LICENSE_FILE), ("license_secret", LICENSE_SECRET)]:
                    if member_name in tar.getnames():
                        with open(target_path, "wb") as f:
                            f.write(tar.extractfile(tar.getmember(member_name)).read())
                        restored["license"] = True
            
            # Restore settings
            if overwrite_settings and "settings.json" in tar.getnames():
                with open(SETTINGS_FILE, "wb") as f:
                    f.write(tar.extractfile(tar.getmember("settings.json")).read())
                restored["settings"] = True
            
            # Count restored labs (from labs/ folder)
            restored["labs"] = len([n for n in tar.getnames() if n.startswith("labs/")])
        
        return {
            "status": "restored",
            "restored": restored,
            "manifest": manifest,
            "note": "Restart the backend to fully apply database changes",
        }
    finally:
        os.unlink(tmp.name)


def _build_manifest():
    """Build the archive manifest."""
    lab_count = 0
    node_count = 0
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM labs")
            lab_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM nodes")
            node_count = cur.fetchone()[0]
            conn.close()
        except Exception:
            pass
    
    return {
        "archive_version": ARCHIVE_VERSION,
        "omnilab_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "lab_count": lab_count,
        "node_count": node_count,
        "platform": sys.platform if "sys" in dir() else "unknown",
    }


def _export_all_labs():
    """Get a dict of {lab_id: full_lab_export_json}."""
    if not os.path.exists(DB_PATH):
        return {}
    result = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, name, category, description, created_at FROM labs")
        for row in cur.fetchall():
            lab_id = row["id"]
            # Get nodes
            cur2 = conn.cursor()
            cur2.execute("SELECT * FROM nodes WHERE lab_id = ?", (lab_id,))
            nodes = [dict(r) for r in cur2.fetchall()]
            # Get links
            cur2.execute("SELECT * FROM links WHERE src_node_id IN (SELECT id FROM nodes WHERE lab_id = ?)", (lab_id,))
            links = [dict(r) for r in cur2.fetchall()]
            
            result[lab_id] = {
                "lab": dict(row),
                "nodes": nodes,
                "links": links,
            }
        conn.close()
    except Exception as e:
        result["_error"] = str(e)
    return result


# Need this at the bottom for the manifest helper
import sys
