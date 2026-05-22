import os, shutil, platform
from fastapi import APIRouter
from core.config import settings
router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "product": "OmniLab"}

@router.get("/info")
async def system_info():
    disk = shutil.disk_usage(str(settings.BASE_DIR))
    return {
        "platform": platform.system(), "arch": platform.machine(),
        "kvm_available": settings.KVM_ENABLED,
        "disk_free_gb": round(disk.free / (1024**3), 1),
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "images_dir": str(settings.IMAGES_DIR),
        "tier": "free"
    }
