import os
from pathlib import Path


class Settings:
    PORT: int = int(os.getenv("OMNILAB_PORT", 5000))
    DEBUG: bool = True
    BASE_DIR: Path = Path.home() / ".omnilab"
    LABS_DIR: Path = BASE_DIR / "labs"
    IMAGES_DIR: Path = BASE_DIR / "images"
    SNAPSHOTS_DIR: Path = BASE_DIR / "snapshots"
    DB_PATH: Path = BASE_DIR / "omnilab.db"
    QEMU_BIN: str = "/usr/bin/qemu-system-x86_64"
    KVM_ENABLED: bool = os.path.exists("/dev/kvm")
    OVS_VSCTL: str = "/usr/bin/ovs-vsctl"
    BRIDGE_PREFIX: str = "omnilab"
    CONSOLE_PORT_START: int = 5900
    FREE_TIER_NODE_LIMIT: int = 5
    FREE_TIER_LAB_LIMIT: int = 2
    def __init__(self):
        for path in [self.BASE_DIR, self.LABS_DIR, self.IMAGES_DIR, self.SNAPSHOTS_DIR]:
            path.mkdir(parents=True, exist_ok=True)

settings = Settings()
