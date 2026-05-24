"""
System health and metrics API.
"""
import os
import platform
import time

from fastapi import APIRouter

router = APIRouter()

# Try psutil for metrics; degrade gracefully if not installed
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Try docker for container info; degrade gracefully if unavailable
try:
    import docker
    docker_client = docker.from_env()
    HAS_DOCKER = True
except Exception:
    docker_client = None
    HAS_DOCKER = False

# Track API stats
_start_time = time.time()
_request_count = 0
_error_count_hour = 0


@router.get("/metrics")
async def get_system_metrics():
    """Combined system + backend process + API health metrics."""
    if not HAS_PSUTIL:
        return {"error": "psutil not installed", "api_healthy": True, "version": "1.0.0"}

    p = psutil.Process(os.getpid())
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    # CRE-49: Disk space warnings for ENOSPC prevention
    disk_free_gb = disk.free / (1024**3)
    disk_warning = None
    disk_critical = False
    
    if disk.percent >= 95:
        disk_critical = True
        disk_warning = f"CRITICAL: Only {disk_free_gb:.1f}GB free. New labs will fail. Run 'docker system prune' or 'omnilab gc --apply' immediately."
    elif disk.percent >= 90:
        disk_warning = f"WARNING: Only {disk_free_gb:.1f}GB free ({100-disk.percent:.0f}% remaining). Free space soon to prevent failures."
    elif disk.percent >= 80:
        disk_warning = f"Low disk space: {disk_free_gb:.1f}GB free. Consider cleaning up old images/labs."

    return {
        "cpu": psutil.cpu_percent(interval=None),
        "cpu_cores": psutil.cpu_count(),
        "ram": mem.percent,
        "ram_total": mem.total,
        "ram_used": mem.used,
        "disk": disk.percent,
        "disk_total": disk.total,
        "disk_used": disk.used,
        "disk_free": disk.free,
        "disk_free_gb": round(disk_free_gb, 2),
        "disk_warning": disk_warning,
        "disk_critical": disk_critical,
        "uptime": int(time.time() - _start_time),
        "api_healthy": True,
        "ws_connections": 0,  # TODO: integrate with console.py WebSocket tracker
        "requests_per_min": _request_count,
        "avg_latency_ms": 0,  # TODO: integrate with middleware
        "errors_last_hour": _error_count_hour,
        "version": "1.0.0",
        "python_version": platform.python_version(),
        "process_ram": p.memory_info().rss,
        "process_cpu": p.cpu_percent(interval=None),
        "threads": p.num_threads(),
        "open_files": len(p.open_files()),
        "recent_logs": _get_recent_logs(),
    }


@router.get("/docker")
async def get_docker_info():
    """Docker daemon stats."""
    if not HAS_DOCKER:
        return {
            "containers_running": 0,
            "containers_total": 0,
            "images_count": 0,
            "storage_bytes": 0,
            "pulling": [],
            "error": "Docker not reachable",
        }

    try:
        containers = docker_client.containers.list(all=True)
        running = [c for c in containers if c.status == "running"]
        images = docker_client.images.list()
        df = docker_client.df()
        storage = sum(img.get("Size", 0) for img in df.get("Images", []))

        return {
            "containers_running": len(running),
            "containers_total": len(containers),
            "images_count": len(images),
            "storage_bytes": storage,
            "pulling": [],  # TODO: track pull progress via events stream
        }
    except Exception as e:
        return {
            "containers_running": 0,
            "containers_total": 0,
            "images_count": 0,
            "storage_bytes": 0,
            "pulling": [],
            "error": str(e),
        }


@router.get("/network")
async def get_network_info():
    """Network: OVS bridges, interfaces."""
    bridges = []
    interfaces_up = 0
    interfaces_down = 0

    if HAS_PSUTIL:
        stats = psutil.net_if_stats()
        for _name, s in stats.items():
            if s.isup:
                interfaces_up += 1
            else:
                interfaces_down += 1

    # Try to query OVS via subprocess
    try:
        import subprocess
        result = subprocess.run(
            ["ovs-vsctl", "list-br"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            for br_name in result.stdout.strip().split("\n"):
                if br_name:
                    ports_result = subprocess.run(
                        ["ovs-vsctl", "list-ports", br_name],
                        capture_output=True, text=True, timeout=2
                    )
                    port_count = len(ports_result.stdout.strip().split("\n")) if ports_result.stdout.strip() else 0
                    bridges.append({"name": br_name, "port_count": port_count})
    except Exception:
        pass  # OVS may not be installed

    return {
        "bridges": bridges,
        "interfaces_up": interfaces_up,
        "interfaces_down": interfaces_down,
        "active_links": 0,  # TODO: query from DB
    }


@router.get("/lab-stats")
async def get_lab_stats():
    """Lab and node statistics from the database."""
    from core.database import get_db

    stats = {
        "total_labs": 0,
        "active_labs": 0,
        "total_nodes": 0,
        "running_nodes": 0,
        "stopped_nodes": 0,
        "by_category": {},
    }

    async for db in get_db():
        # Lab counts
        async with db.execute("SELECT COUNT(*) FROM labs") as cur:
            row = await cur.fetchone()
            stats["total_labs"] = row[0] if row else 0

        # Active labs (any running nodes)
        async with db.execute(
            "SELECT COUNT(DISTINCT lab_id) FROM nodes WHERE status = ?",
            ("running",)
        ) as cur:
            row = await cur.fetchone()
            stats["active_labs"] = row[0] if row else 0

        # Node counts
        async with db.execute("SELECT status, COUNT(*) FROM nodes GROUP BY status") as cur:
            async for row in cur:
                if row[0] == "running":
                    stats["running_nodes"] = row[1]
                elif row[0] == "stopped":
                    stats["stopped_nodes"] = row[1]
                stats["total_nodes"] += row[1]

        # By category
        async with db.execute("SELECT category, COUNT(*) FROM labs GROUP BY category") as cur:
            async for row in cur:
                if row[0]:
                    stats["by_category"][row[0]] = row[1]

    return stats


def _get_recent_logs():
    """Read the last few lines from the OmniLab log."""
    log_path = "/tmp/omnilab.log"
    if not os.path.exists(log_path):
        return []
    try:
        with open(log_path) as f:
            lines = f.readlines()[-20:]
        logs = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Naive parse: assume "TIME LEVEL message" format
            parts = line.split(None, 2)
            if len(parts) >= 3:
                level = "INFO"
                if "ERROR" in parts[1].upper():
                    level = "ERROR"
                elif "WARN" in parts[1].upper():
                    level = "WARN"
                logs.append({
                    "time": parts[0][-8:],  # last 8 chars
                    "level": level,
                    "message": parts[2][:80],
                })
            else:
                logs.append({"time": "—", "level": "INFO", "message": line[:80]})
        return logs[-10:]  # most recent 10
    except Exception:
        return []
