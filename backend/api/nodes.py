import asyncio
import json
import os
import pathlib
import signal
import uuid

from core.database import get_db
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from services.docker_provisioner import (
    DockerProvisioner,
    DockerProvisionerError,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Docker provisioner: lazy singleton.
#
# We don't construct the client at import time — that would fail-fast at app
# startup on hosts without docker, which is correct for production but breaks
# CI / dev machines that legitimately don't have a daemon. Instead, the first
# request that needs docker constructs it and caches it. Failures surface as a
# clear 503 to the caller, not a 500 stack trace.
# ---------------------------------------------------------------------------
_provisioner: DockerProvisioner | None = None


def _get_provisioner() -> DockerProvisioner:
    global _provisioner
    if _provisioner is None:
        _provisioner = DockerProvisioner()
    return _provisioner


def _reset_provisioner_for_tests(p: DockerProvisioner | None = None) -> None:
    """Test hook — inject a mock or clear the cached singleton."""
    global _provisioner
    _provisioner = p


# ---------------------------------------------------------------------------
# Shared docker start/stop sequences — the SINGLE SOURCE OF TRUTH for the
# order of provisioner calls a docker node goes through. Both the async HTTP
# endpoints below and the synchronous agent tools (services/agent_tools.py,
# CRE-43) funnel through these coroutines so the two layers can never drift.
#
# These are pure async helpers over a provisioner: they perform NO database
# writes (each caller owns its own DB row update — aiosqlite for the endpoint,
# sqlite3 via the Repo for the tools). The agent tools drive them from sync
# code via a private event loop (safe: the sync /tools endpoint and the CRE-44
# loop both run in a threadpool worker with no running loop).
# ---------------------------------------------------------------------------


async def docker_start_sequence(
    provisioner: DockerProvisioner,
    *,
    node_id: str,
    lab_id: str,
    image: str,
    name: str,
    ports: dict | None = None,
    docker_options: dict | None = None,
    progress_cb=None,
) -> dict:
    """ensure_image -> create_lab_network -> start_node. Returns start result."""
    await provisioner.ensure_image(image, progress_cb=progress_cb)
    await provisioner.create_lab_network(lab_id)
    return await provisioner.start_node(
        node_id=node_id,
        lab_id=lab_id,
        image=image,
        name=name,
        ports=ports,
        docker_options=docker_options,
    )


async def docker_stop_sequence(
    provisioner: DockerProvisioner,
    *,
    node_id: str,
    lab_id: str,
    others_running: int,
) -> None:
    """stop_node, then destroy the lab network iff no other docker node in the
    lab is still running. ``others_running`` is the count of *other* running
    docker nodes in the lab (caller computes it from its own DB)."""
    await provisioner.stop_node(node_id)
    if others_running == 0:
        try:
            await provisioner.destroy_lab_network(lab_id)
        except DockerProvisionerError:
            # Best-effort — a transient network-destroy error must not fail stop.
            pass


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
        try:
            await db.execute(
                "INSERT INTO nodes (id, lab_id, name, type, image, config, x, y, console_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (node_id, data.lab_id, data.name, data.type, data.image, json.dumps(data.config), data.x, data.y, data.console_type or 'pty'))
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create node: {str(e)}") from e
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
        try:
            await db.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete node: {str(e)}") from e

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
    """Start a node. Branches on node.type:
    - 'docker': pulls image (if needed), ensures lab network, runs container.
    - everything else (with console_type=='vnc'): spawns QEMU and assigns VNC port.
    - PTY nodes: just flips status to running.
    """
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Node not found")

        node = dict(row)
        console_type = node.get("console_type", "pty")
        node_type = (node.get("type") or "").lower()

        # ----------------------------------------------------------- docker
        if node_type == "docker":
            image = node.get("image") or ""
            if not image:
                raise HTTPException(
                    status_code=400,
                    detail="Docker node has no image configured",
                )

            try:
                p = _get_provisioner()
            except DockerProvisionerError as exc:
                # Docker daemon unreachable / SDK missing — surface as 503 so
                # the UI can render the docker-group-hint message.
                raise HTTPException(status_code=503, detail=str(exc)) from exc

            # Per-template docker_options is stored in nodes.config JSON
            # under the "docker_options" key. Templates may also set
            # "ports" there. Both are optional.
            try:
                cfg = json.loads(node.get("config") or "{}") or {}
            except (TypeError, ValueError):
                cfg = {}
            docker_options = cfg.get("docker_options") or {}
            ports = cfg.get("ports") or None

            try:
                _loop = asyncio.get_running_loop()

                def _emit(event: dict, *, _l=_loop, _nid=node_id) -> None:
                    # Called from the docker-SDK pull thread — hop back to the
                    # request's event loop and broadcast. Default-arg binding
                    # captures _loop/node_id at definition time so ruff B023
                    # is satisfied and we're safe against late-binding bugs.
                    def _schedule():
                        asyncio.create_task(
                            _broadcast_provision(_nid, {"type": "pull", **event})
                        )

                    _l.call_soon_threadsafe(_schedule)

                result = await docker_start_sequence(
                    p,
                    node_id=node_id,
                    lab_id=node["lab_id"],
                    image=image,
                    name=node.get("name") or node_id,
                    ports=ports,
                    docker_options=docker_options,
                    progress_cb=_emit,
                )
            except DockerProvisionerError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            await db.execute(
                "UPDATE nodes SET status = ? WHERE id = ?",
                ("running", node_id),
            )
            await db.commit()
            return {
                "status": "running",
                "container_id": result.get("container_id"),
                "ip_address": result.get("ip_address"),
                "ports": result.get("ports"),
            }

        # ------------------------------------------------------------ vnc
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
    """Stop a node. For docker nodes, removes the container and tears down the
    lab network if no other docker nodes in the same lab are still running.
    For VNC nodes, kills the QEMU process.
    """
    async for db in get_db():
        # Look up the node first so we can branch on type and remember its lab.
        async with db.execute(
            "SELECT id, lab_id, type FROM nodes WHERE id = ?", (node_id,)
        ) as cur:
            node_row = await cur.fetchone()
        if not node_row:
            raise HTTPException(status_code=404, detail="Node not found")

        node_type = (node_row["type"] or "").lower()
        lab_id = node_row["lab_id"]

        # ----------------------------------------------------------- docker
        if node_type == "docker":
            try:
                p = _get_provisioner()
            except DockerProvisionerError as exc:
                # If docker is gone we still flip the DB row to stopped so the
                # UI doesn't show a phantom-running node.
                await db.execute(
                    "UPDATE nodes SET status = ? WHERE id = ?",
                    ("stopped", node_id),
                )
                await db.commit()
                raise HTTPException(status_code=503, detail=str(exc)) from exc

            # Stop the container first (no DB write yet so a transient docker
            # error doesn't leave the row in a weird state).
            try:
                await p.stop_node(node_id)
            except DockerProvisionerError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            await db.execute(
                "UPDATE nodes SET status = ? WHERE id = ?",
                ("stopped", node_id),
            )
            await db.commit()

            # Was this the last running docker node in the lab? If so, tear
            # down the lab network (best-effort). We compute "others running"
            # AFTER the commit above so this node is already counted as stopped.
            async with db.execute(
                "SELECT COUNT(*) AS n FROM nodes "
                "WHERE lab_id = ? AND lower(type) = 'docker' AND status = 'running'",
                (lab_id,),
            ) as cur:
                remaining = await cur.fetchone()
            others_running = remaining["n"] if remaining else 0
            if others_running == 0:
                try:
                    await p.destroy_lab_network(lab_id)
                except DockerProvisionerError:
                    pass

            return {"status": "stopped"}

        # ------------------------------------------------------------ qemu
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


# ============================================================
# CRE-39 phase 2: docker pull-progress WebSocket
#
# Browser opens /api/nodes/{node_id}/provision-ws BEFORE clicking start, then
# the start-node endpoint streams docker pull events to all connected sockets
# for that node. This is decoupled from the start endpoint via an in-memory
# fan-out registry so a slow client doesn't block the pull.
# ============================================================

import asyncio as _asyncio  # noqa: F811 — local alias for clarity in the WS handler

_provision_listeners: dict[str, set[WebSocket]] = {}


async def _broadcast_provision(node_id: str, event: dict) -> None:
    listeners = list(_provision_listeners.get(node_id, set()))
    for ws in listeners:
        try:
            await ws.send_json(event)
        except Exception:
            # Listener gone — drop it silently; the disconnect handler cleans up.
            pass


@router.websocket("/{node_id}/provision-ws")
async def provision_ws(node_id: str, ws: WebSocket):
    """Subscribe to docker pull-progress events for one node.

    Phase 2 ships the channel; the actual progress streaming from
    DockerProvisioner.ensure_image hooks in via ``progress_cb=_emit_provision``
    in a follow-up commit (kept separate for reviewability — this commit
    proves the channel works end-to-end with no events, the next one wires
    the producer).
    """
    await ws.accept()
    _provision_listeners.setdefault(node_id, set()).add(ws)
    try:
        # Keep the socket open. The client sends nothing; we only broadcast.
        while True:
            try:
                msg = await _asyncio.wait_for(ws.receive(), timeout=30.0)
            except _asyncio.TimeoutError:
                # Heartbeat so proxies don't drop the connection.
                try:
                    await ws.send_json({"type": "ping"})
                except Exception:
                    break
                continue
            if msg.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        bucket = _provision_listeners.get(node_id)
        if bucket is not None:
            bucket.discard(ws)
            if not bucket:
                _provision_listeners.pop(node_id, None)
