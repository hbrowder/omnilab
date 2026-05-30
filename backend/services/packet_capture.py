"""
Packet capture service for OmniLab links.

CRE-57: Wireshark integration via tcpdump
- Start/stop packet capture on network links
- Download PCAP files
- Automatic cleanup of old captures
"""
import asyncio
import os
import time
import uuid
from pathlib import Path

# Active capture sessions: {capture_id: {"process": subprocess, "link_id": str, "pcap_path": Path, ...}}
_active_captures: dict[str, dict] = {}

# Storage for PCAP files (store in /tmp during dev/testing, configurable via env)
# tcpdump with cap_net_raw can't write to some home directories due to kernel restrictions
CAPTURE_DIR = Path(os.getenv("OMNILAB_CAPTURE_DIR", "/tmp/omnilab-captures"))
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)


class CaptureError(Exception):
    """Raised when packet capture operations fail."""
    pass


async def start_capture(
    link_id: str,
    lab_id: str,
    interface: str,
    filter_expr: str = "",
    max_packets: int = 0,
    max_duration_sec: int = 0,
) -> dict:
    """
    Start packet capture on a network interface.

    Args:
        link_id: Link UUID
        lab_id: Lab UUID
        interface: Network interface name (e.g., "br-lab-abc", "veth-node1")
        filter_expr: BPF filter expression (e.g., "tcp port 80", "icmp")
        max_packets: Stop after N packets (0 = unlimited)
        max_duration_sec: Stop after N seconds (0 = unlimited)

    Returns:
        dict with capture_id, pcap_path, status

    Raises:
        CaptureError: If capture cannot be started
    """
    # Check if tcpdump is available
    if not os.path.exists("/usr/sbin/tcpdump") and not os.path.exists("/usr/bin/tcpdump"):
        raise CaptureError("tcpdump not installed. Install with: sudo apt install tcpdump")

    # Check if we already have an active capture on this link
    for capture_id, capture in _active_captures.items():
        if capture["link_id"] == link_id:
            raise CaptureError(f"Capture already active on link {link_id} (capture_id: {capture_id})")

    capture_id = str(uuid.uuid4())
    timestamp = int(time.time())
    pcap_filename = f"capture_{capture_id[:8]}_{link_id[:8]}_{timestamp}.pcap"
    pcap_path = CAPTURE_DIR / pcap_filename

    # Build tcpdump command
    cmd = ["tcpdump", "-i", interface, "-w", str(pcap_path), "-U"]  # -U = packet-buffered (for live viewing)

    if filter_expr:
        cmd.append(filter_expr)

    if max_packets > 0:
        cmd.extend(["-c", str(max_packets)])

    # Start tcpdump process
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait briefly to check if tcpdump started successfully
        await asyncio.sleep(0.5)
        if process.returncode is not None:
            # Process already exited (error)
            stderr_output = await process.stderr.read()
            raise CaptureError(f"tcpdump failed to start: {stderr_output.decode('utf-8', errors='ignore')}")

    except PermissionError:
        raise CaptureError(
            "Permission denied. tcpdump requires root or CAP_NET_RAW capability. "
            "Run: sudo setcap cap_net_raw,cap_net_admin=eip $(which tcpdump)"
        ) from None
    except Exception as e:
        raise CaptureError(f"Failed to start tcpdump: {e}") from e

    # Store capture metadata
    _active_captures[capture_id] = {
        "process": process,
        "link_id": link_id,
        "lab_id": lab_id,
        "interface": interface,
        "pcap_path": pcap_path,
        "filter": filter_expr,
        "started_at": timestamp,
        "max_packets": max_packets,
        "max_duration_sec": max_duration_sec,
        "pid": process.pid,
    }

    # Auto-stop after max_duration_sec (if set)
    if max_duration_sec > 0:
        asyncio.create_task(_auto_stop_capture(capture_id, max_duration_sec))

    return {
        "capture_id": capture_id,
        "link_id": link_id,
        "interface": interface,
        "pcap_path": str(pcap_path),
        "filter": filter_expr,
        "status": "running",
        "started_at": timestamp,
        "pid": process.pid,
    }


async def _auto_stop_capture(capture_id: str, duration_sec: int):
    """Automatically stop a capture after duration_sec seconds."""
    await asyncio.sleep(duration_sec)
    if capture_id in _active_captures:
        await stop_capture(capture_id)


async def stop_capture(capture_id: str) -> dict:
    """
    Stop an active packet capture.

    Args:
        capture_id: Capture UUID

    Returns:
        dict with capture metadata and packet count

    Raises:
        CaptureError: If capture not found or stop fails
    """
    if capture_id not in _active_captures:
        raise CaptureError(f"Capture {capture_id} not found or already stopped")

    capture = _active_captures[capture_id]
    process = capture["process"]

    # Send SIGTERM to tcpdump
    try:
        if process.returncode is None:  # Process still running
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5.0)
        else:
            # Process already exited (e.g., hit max_packets limit)
            pass
    except asyncio.TimeoutError:
        # Force kill if it doesn't stop gracefully
        process.kill()
        await process.wait()
    except ProcessLookupError:
        # Process already gone - that's fine
        pass

    # Get packet count from PCAP file
    pcap_path = capture["pcap_path"]
    packet_count = 0
    file_size = 0
    if pcap_path.exists():
        file_size = pcap_path.stat().st_size
        # Quick estimate: typical packet ~100 bytes, PCAP header 24 bytes
        # For accurate count, would need to parse PCAP or use capinfos
        if file_size > 24:
            packet_count = (file_size - 24) // 100  # Rough estimate

    # Remove from active captures
    del _active_captures[capture_id]

    return {
        "capture_id": capture_id,
        "link_id": capture["link_id"],
        "interface": capture["interface"],
        "pcap_path": str(pcap_path),
        "status": "stopped",
        "duration_sec": int(time.time() - capture["started_at"]),
        "file_size_bytes": file_size,
        "packet_count_estimate": packet_count,
    }


def list_captures() -> list:
    """
    List all active packet captures.

    Returns:
        list of capture metadata dicts
    """
    captures = []
    for capture_id, capture in _active_captures.items():
        captures.append({
            "capture_id": capture_id,
            "link_id": capture["link_id"],
            "lab_id": capture["lab_id"],
            "interface": capture["interface"],
            "filter": capture["filter"],
            "started_at": capture["started_at"],
            "duration_sec": int(time.time() - capture["started_at"]),
            "status": "running",
            "pid": capture["pid"],
        })
    return captures


def get_capture_file(capture_id: str) -> Path:
    """
    Get path to PCAP file for a capture (active or stopped).

    Args:
        capture_id: Capture UUID

    Returns:
        Path to PCAP file

    Raises:
        CaptureError: If capture not found or file doesn't exist
    """
    # Check active captures
    if capture_id in _active_captures:
        pcap_path = _active_captures[capture_id]["pcap_path"]
        if pcap_path.exists():
            return pcap_path

    # Check for stopped captures (scan CAPTURE_DIR for matching files)
    for pcap_file in CAPTURE_DIR.glob("*.pcap"):
        if capture_id[:8] in pcap_file.name or capture_id in pcap_file.name:
            return pcap_file

    raise CaptureError(f"PCAP file for capture {capture_id} not found")


async def cleanup_old_captures(max_age_hours: int = 24):
    """
    Delete PCAP files older than max_age_hours.

    Args:
        max_age_hours: Maximum age in hours (default: 24)

    Returns:
        int: Number of files deleted
    """
    cutoff_time = time.time() - (max_age_hours * 3600)
    deleted_count = 0

    for pcap_file in CAPTURE_DIR.glob("*.pcap"):
        if pcap_file.stat().st_mtime < cutoff_time:
            pcap_file.unlink()
            deleted_count += 1

    return deleted_count


async def stop_all_captures_for_lab(lab_id: str):
    """
    Stop all active captures for a specific lab.
    Called when a lab is stopped or deleted.

    Args:
        lab_id: Lab UUID
    """
    capture_ids = [
        cid for cid, cap in _active_captures.items()
        if cap["lab_id"] == lab_id
    ]

    for capture_id in capture_ids:
        try:
            await stop_capture(capture_id)
        except Exception:
            pass  # Best effort cleanup
