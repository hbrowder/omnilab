import json
import os
import pathlib
import signal
import uuid

from core.database import get_db
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class NodeCreate(BaseModel):
    lab_id: str
    name: str
    type: str
    image: str | None = None
    x: float | None = 100
    y: float | None = 100
    config: dict | None = {}
    console_type: str | None = 'pty'

@router.post("/", status_code=201)
async def add_node(data: NodeCreate):
    node_id = str(uuid.uuid4())
    async for db in get_db():
        await db.execute(
            "INSERT INTO nodes (id, lab_id, name, type, image, config, x, y, console_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (node_id, data.lab_id, data.name, data.type, data.image, json.dumps(data.config), data.x, data.y, data.console_type or 'pty'))
        await db.commit()
    return {"id": node_id, "name": data.name, "type": data.type, "status": "stopped", "console_type": data.console_type or "pty"}

@router.get("/{node_id}")
async def get_node(node_id: str):
    async for db in get_db():
        async with db.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Node not found")
            return dict(row)

@router.delete("/{node_id}", status_code=204)
async def delete_node(node_id: str):
    async for db in get_db():
        await db.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        await db.commit()

import subprocess as _subprocess

# Track running QEMU processes: node_id -> process
_qemu_procs: dict = {}
_next_vnc_display = 10  # start at display :10 = port 5910 to avoid conflicts


def _alloc_vnc_display():
    global _next_vnc_display
    d = _next_vnc_display
    _next_vnc_display += 1
    return d, 5900 + d


@router.post("/{node_id}/start")
async def start_node(node_id: str):
    """Start a node. For VNC nodes, spawns QEMU and assigns a VNC port."""
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Node not found")

        node = dict(row)
        console_type = node.get("console_type", "pty")

        if console_type == "vnc":
            # Allocate VNC display and port
            display_num, vnc_port = _alloc_vnc_display()

            # Determine image path
            image = node.get("image") or ""
            if image and pathlib.Path(image).exists():
                disk_flag = "-cdrom" if image.lower().endswith((".iso",)) else "-hda"
                qemu_cmd = [
                    "/usr/bin/qemu-system-x86_64",
                    "-enable-kvm",
                    "-pidfile", f"/tmp/omnilab-qemu-{node_id}.pid",
                    "-m", "512",
                    disk_flag, image,
                    "-vnc", f"127.0.0.1:{display_num}",
                    "-display", "none",
                    "-no-reboot",
                    "-daemonize",
                ]
            else:
                # Demo mode: run QEMU with a tiny RAM disk, no image needed
                qemu_cmd = [
                    "/usr/bin/qemu-system-x86_64",
                    "-enable-kvm",
                    "-pidfile", f"/tmp/omnilab-qemu-{node_id}.pid",
                    "-m", "128",
                    "-vnc", f"127.0.0.1:{display_num}",
                    "-display", "none",
                    "-no-reboot",
                    "-daemonize",
                ]

            try:
                proc = _subprocess.Popen(
                    qemu_cmd,
                    stdout=_subprocess.DEVNULL,
                    stderr=_subprocess.DEVNULL,
                )
                _qemu_procs[node_id] = proc
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"QEMU launch failed: {e}") from e

            # Store vnc_port and update status
            await db.execute(
                "UPDATE nodes SET status = ?, vnc_port = ? WHERE id = ?",
                ("running", vnc_port, node_id),
            )
            await db.commit()
            return {"status": "running", "vnc_port": vnc_port, "display": display_num}
        else:
            # PTY nodes: just update status
            await db.execute(
                "UPDATE nodes SET status = ? WHERE id = ?", ("running", node_id)
            )
            await db.commit()
            return {"status": "running"}


@router.post("/{node_id}/stop")
async def stop_node(node_id: str):
    """Stop a node. For VNC nodes, kills the QEMU process."""
    async for db in get_db():
        proc = _qemu_procs.pop(node_id, None)
        # Kill QEMU via pidfile (works with -daemonize forks)
        pidfile = f"/tmp/omnilab-qemu-{node_id}.pid"
        try:
            if os.path.exists(pidfile):
                with open(pidfile) as _pf:
                    _vm_pid = int(_pf.read().strip())
                try:
                    os.kill(_vm_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                os.unlink(pidfile)
        except Exception:
            pass
        # Also try Popen handle (covers non-daemonized cases)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        await db.execute(
            "UPDATE nodes SET status = ?, vnc_port = NULL WHERE id = ?",
            ("stopped", node_id),
        )
        await db.commit()
        return {"status": "stopped"}




class NodeUpdate(BaseModel):
    name: str | None = None
    config: str | None = None
    x: int | None = None
    y: int | None = None


@router.patch("/{node_id}")
async def update_node(node_id: str, payload: NodeUpdate):
    """Update node fields: name, config (startup config), x, y position."""
    async for db in get_db():
        async with db.execute("SELECT id FROM nodes WHERE id = ?", (node_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Node not found")

        updates = []
        params = []
        if payload.name is not None:
            updates.append("name = ?")
            params.append(payload.name)
        if payload.config is not None:
            updates.append("config = ?")
            params.append(payload.config)
        if payload.x is not None:
            updates.append("x = ?")
            params.append(payload.x)
        if payload.y is not None:
            updates.append("y = ?")
            params.append(payload.y)

        if not updates:
            return {"status": "no changes"}

        params.append(node_id)
        await db.execute(
            f"UPDATE nodes SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        await db.commit()
        return {"status": "updated", "fields_updated": len(updates)}


class RdpConfig(BaseModel):
    host: str
    port: int = 3389


@router.post("/{node_id}/rdp-config")
async def set_rdp_config(node_id: str, cfg: RdpConfig):
    """Store RDP host/port for a node and mark it ready."""
    async for db in get_db():
        async with db.execute("SELECT id FROM nodes WHERE id = ?", (node_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Node not found")
        await db.execute(
            "UPDATE nodes SET rdp_host = ?, rdp_port = ?, status = ? WHERE id = ?",
            (cfg.host, cfg.port, "running", node_id),
        )
        await db.commit()
        return {"status": "ok", "rdp_host": cfg.host, "rdp_port": cfg.port}
