import asyncio
import json
import os

import ptyprocess
from core.database import get_db
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from services.docker_provisioner import (
    DockerProvisioner,
    DockerProvisionerError,
)

router = APIRouter()
_sessions: dict = {}
_active_websockets: int = 0  # Tracks currently connected console WebSockets


def get_active_websocket_count() -> int:
    """Return the count of active WebSocket console connections."""
    return _active_websockets


# ---------------------------------------------------------------------------
# Lazy docker provisioner — same pattern as api/nodes.py. Used to detect the
# right shell for a docker node's console. See _reset_provisioner_for_tests.
# ---------------------------------------------------------------------------
_provisioner: DockerProvisioner | None = None


def _get_provisioner() -> DockerProvisioner:
    global _provisioner
    if _provisioner is None:
        _provisioner = DockerProvisioner()
    return _provisioner


def _reset_provisioner_for_tests(p: DockerProvisioner | None = None) -> None:
    global _provisioner
    _provisioner = p


@router.get("/{node_id}/info")
async def console_info(node_id: str):
    async for db in get_db():
        async with db.execute(
            "SELECT id, type, console_type FROM nodes WHERE id = ?", (node_id,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Node not found")
    node_type = (row["type"] or "").lower()
    # Docker nodes always use the PTY-style WebSocket — same URL, the server
    # dispatches based on node.type.
    return {
        "node_id": node_id,
        "node_type": node_type,
        "console_type": row["console_type"] or "pty",
        "websocket_url": f"ws://localhost:5000/api/console/{node_id}/ws",
    }


def _read_pty(fd: int) -> bytes:
    import select
    r, _, _ = select.select([fd], [], [], 0.05)
    if r:
        try:
            return os.read(fd, 4096)
        except OSError:
            return b""
    return b""


async def _relay(proc, ws: WebSocket, stop: asyncio.Event):
    loop = asyncio.get_event_loop()
    fd = proc.fd
    while not stop.is_set():
        try:
            data = await loop.run_in_executor(None, _read_pty, fd)
            if data:
                await ws.send_bytes(data)
            if not proc.isalive():
                break
        except (OSError, WebSocketDisconnect):
            break
    stop.set()


# ---------------------------------------------------------------------------
# Docker console relay
#
# docker exec -i -t omnilab-<node_id> <shell>
# The docker SDK gives us a low-level socket; we run blocking reads in a
# thread and forward bytes to the WebSocket. Resize events translate to
# exec_resize on the SDK.
# ---------------------------------------------------------------------------

def _docker_exec_read(sock, n: int = 4096) -> bytes:
    """Blocking read from the docker exec socket. Returns b'' on EOF."""
    try:
        # docker SDK's SocketIO exposes ._sock for the underlying socket.
        underlying = getattr(sock, "_sock", sock)
        return underlying.recv(n) or b""
    except OSError:
        return b""


async def _docker_console_loop(node_id: str, ws: WebSocket):
    """Drive a docker-exec console over the given WebSocket."""
    try:
        p = _get_provisioner()
    except DockerProvisionerError as exc:
        await ws.send_text(f"ERROR: {exc}")
        return

    try:
        container_name, shell = await p.exec_console(node_id)
    except DockerProvisionerError as exc:
        await ws.send_text(f"ERROR: {exc}")
        return

    # Build an exec instance on the underlying low-level API. Using the SDK's
    # raw socket gives us the same bidirectional binary channel xterm.js
    # already expects.
    api = p.client.api
    container = p.client.containers.get(container_name)
    try:
        exec_id = api.exec_create(
            container.id,
            cmd=[shell],
            tty=True,
            stdin=True,
            stdout=True,
            stderr=True,
        )["Id"]
        sock = api.exec_start(exec_id, socket=True, tty=True, demux=False)
    except Exception as exc:  # noqa: BLE001 — any SDK error becomes a clean WS message
        await ws.send_text(f"ERROR: docker exec failed: {exc}")
        return

    loop = asyncio.get_event_loop()
    stop = asyncio.Event()

    async def _reader():
        try:
            while not stop.is_set():
                data = await loop.run_in_executor(None, _docker_exec_read, sock)
                if not data:
                    break
                try:
                    await ws.send_bytes(data)
                except Exception:
                    break
        finally:
            stop.set()

    reader_task = asyncio.create_task(_reader())
    try:
        while not stop.is_set():
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=0.05)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
            if msg.get("type") == "websocket.disconnect":
                break
            data = msg.get("bytes")
            if data:
                underlying = getattr(sock, "_sock", sock)
                try:
                    underlying.send(data)
                except OSError:
                    break
            text = msg.get("text")
            if text:
                try:
                    evt = json.loads(text)
                    if evt.get("type") == "resize":
                        api.exec_resize(
                            exec_id,
                            height=int(evt.get("rows", 24)),
                            width=int(evt.get("cols", 80)),
                        )
                except Exception:
                    # Bad resize payload / closed exec — ignore silently.
                    pass
    finally:
        stop.set()
        reader_task.cancel()
        try:
            await reader_task
        except asyncio.CancelledError:
            pass
        try:
            getattr(sock, "_sock", sock).close()
        except Exception:
            pass


@router.websocket("/{node_id}/ws")
async def console_ws(node_id: str, ws: WebSocket):
    global _active_websockets
    await ws.accept()
    _active_websockets += 1

    try:
        # Look up the node type so we can dispatch. For an unknown / missing
        # node we still send a clean error rather than crashing the handler.
        node_type = ""
        async for db in get_db():
            async with db.execute(
                "SELECT type, console_type FROM nodes WHERE id = ?", (node_id,)
            ) as cur:
                row = await cur.fetchone()
            if row:
                node_type = (row["type"] or "").lower()

        if node_type == "docker":
            await _docker_console_loop(node_id, ws)
            return

        # ----- legacy PTY path (host shell — kept for existing 'pty' nodes) -----
        proc = _sessions.get(node_id)
        if proc is None or not proc.isalive():
            shell = os.environ.get("SHELL", "/bin/bash")
            proc = ptyprocess.PtyProcess.spawn(
                [shell, "--login"],
                env={**os.environ, "TERM": "xterm-256color"},
            )
            _sessions[node_id] = proc
        stop = asyncio.Event()
        reader = asyncio.create_task(_relay(proc, ws, stop))
        try:
            while not stop.is_set():
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=0.05)
                except asyncio.TimeoutError:
                    if not proc.isalive():
                        break
                    continue
                except WebSocketDisconnect:
                    break
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes"):
                    try:
                        os.write(proc.fd, msg["bytes"])
                    except OSError:
                        break
                if msg.get("text"):
                    try:
                        evt = json.loads(msg["text"])
                        if evt.get("type") == "resize":
                            proc.setwinsize(int(evt.get("rows", 24)), int(evt.get("cols", 80)))
                    except Exception:
                        pass
        finally:
            stop.set()
            reader.cancel()
            try:
                await reader
            except asyncio.CancelledError:
                pass
    finally:
        _active_websockets -= 1


# ============================================================
# Phase 2: VNC WebSocket proxy
# Browser <-> FastAPI WS <-> QEMU TCP VNC server
# ============================================================

async def _relay_ws_to_tcp(ws: WebSocket, writer: asyncio.StreamWriter, stop: asyncio.Event):
    """Read binary frames from WebSocket and write to TCP."""
    try:
        while not stop.is_set():
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=0.05)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes"):
                writer.write(msg["bytes"])
                await writer.drain()
    finally:
        stop.set()


async def _relay_tcp_to_ws(reader: asyncio.StreamReader, ws: WebSocket, stop: asyncio.Event):
    """Read bytes from TCP and send binary frames to WebSocket."""
    try:
        while not stop.is_set():
            try:
                data = await asyncio.wait_for(reader.read(65536), timeout=0.05)
                if not data:
                    break
                await ws.send_bytes(data)
            except asyncio.TimeoutError:
                continue
            except (OSError, WebSocketDisconnect):
                break
    finally:
        stop.set()


@router.websocket("/{node_id}/vnc-ws")
async def vnc_ws(node_id: str, ws: WebSocket):
    """Raw WebSocket <-> TCP proxy to QEMU VNC server."""
    global _active_websockets
    await ws.accept()
    _active_websockets += 1

    try:
        # Look up the VNC port for this node
        vnc_port = None
        async for db in get_db():
            async with db.execute(
                "SELECT vnc_port, status FROM nodes WHERE id = ?", (node_id,)
            ) as cur:
                row = await cur.fetchone()
            if row:
                vnc_port = row["vnc_port"]

        if not vnc_port:
            await ws.send_text("ERROR: Node has no VNC port assigned. Start the node first.")
            await ws.close()
            return

        # Connect to QEMU VNC TCP server
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", vnc_port)
        except OSError as e:
            await ws.send_text(f"ERROR: Cannot connect to VNC server on port {vnc_port}: {e}")
            await ws.close()
            return

        stop = asyncio.Event()
        t1 = asyncio.create_task(_relay_ws_to_tcp(ws, writer, stop))
        t2 = asyncio.create_task(_relay_tcp_to_ws(reader, ws, stop))

        try:
            await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
        finally:
            stop.set()
            t1.cancel()
            t2.cancel()
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            for t in [t1, t2]:
                try:
                    await t
                except asyncio.CancelledError:
                    pass
    finally:
        _active_websockets -= 1


# ============================================================
# Phase 3: RDP via Guacamole WebSocket proxy
# Browser JS <-> FastAPI WS <-> Guacamole websocket tunnel
# ============================================================

@router.websocket("/{node_id}/rdp-ws")
async def rdp_ws(node_id: str, ws: WebSocket):
    """Proxy WebSocket frames between browser and Guacamole guacd tunnel."""
    await ws.accept()

    # Get RDP connection details from DB
    rdp_host = None
    rdp_port = 3389
    async for db in get_db():
        async with db.execute(
            "SELECT rdp_host, rdp_port, status FROM nodes WHERE id = ?",
            (node_id,)
        ) as cur:
            row = await cur.fetchone()
        if row:
            rdp_host = row["rdp_host"]
            rdp_port = row["rdp_port"] or 3389

    if not rdp_host:
        await ws.send_text("ERROR: Node has no RDP host configured.")
        await ws.close()
        return

    # Connect to guacd via TCP and speak the Guacamole protocol
    # guacd listens on port 4822
    GUACD_HOST = "127.0.0.1"
    GUACD_PORT = 4822

    try:
        reader, writer = await asyncio.open_connection(GUACD_HOST, GUACD_PORT)
    except OSError as e:
        await ws.send_text(f"ERROR: Cannot connect to guacd on {GUACD_HOST}:{GUACD_PORT}: {e}")
        await ws.close()
        return

    # Send Guacamole handshake: select RDP connection
    # Guacamole instruction format: LEN.DATA,LEN.DATA,...;
    def guac_instr(*parts):
        return ",".join(f"{len(p)}.{p}" for p in parts) + ";"

    # 1. Select RDP protocol
    writer.write(guac_instr("select", "rdp").encode())
    await writer.drain()

    # 2. Read server args list
    args_data = b""
    while not args_data.endswith(b";"):
        chunk = await asyncio.wait_for(reader.read(4096), timeout=5.0)
        args_data += chunk

    # Parse args — extract the parameter names guacd expects
    args_str = args_data.decode(errors="replace")
    # Format: LEN.args,LEN.name1,LEN.name2,...;
    parts = args_str.rstrip(";").split(",")
    param_names = [p.split(".", 1)[1] for p in parts[1:]]  # skip "args"

    # 3. Build connect instruction with our RDP params
    rdp_params = {
        "hostname": rdp_host,
        "port": str(rdp_port),
        "width": "1280",
        "height": "720",
        "dpi": "96",
        "color-depth": "24",
        "security": "any",
        "ignore-cert": "true",
        "disable-auth": "false",
        "enable-wallpaper": "false",
        "enable-theming": "false",
    }
    param_values = [rdp_params.get(n, "") for n in param_names]
    connect_instr = guac_instr("connect", *param_values)
    writer.write(connect_instr.encode())
    await writer.drain()

    # 4. Relay binary data bidirectionally
    # Guacamole protocol is text-based but we relay as binary
    stop = asyncio.Event()

    async def guacd_to_ws():
        try:
            while not stop.is_set():
                try:
                    data = await asyncio.wait_for(reader.read(65536), timeout=0.05)
                    if not data:
                        break
                    await ws.send_text(data.decode(errors="replace"))
                except asyncio.TimeoutError:
                    continue
                except (OSError, WebSocketDisconnect):
                    break
        finally:
            stop.set()

    async def ws_to_guacd():
        try:
            while not stop.is_set():
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=0.05)
                except asyncio.TimeoutError:
                    continue
                if msg.get("type") == "websocket.disconnect":
                    break
                text = msg.get("text", "")
                if text:
                    writer.write(text.encode())
                    await writer.drain()
                data = msg.get("bytes")
                if data:
                    writer.write(data)
                    await writer.drain()
        except WebSocketDisconnect:
            pass
        finally:
            stop.set()

    t1 = asyncio.create_task(guacd_to_ws())
    t2 = asyncio.create_task(ws_to_guacd())
    try:
        await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
    finally:
        stop.set()
        t1.cancel()
        t2.cancel()
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        for t in [t1, t2]:
            try:
                await t
            except asyncio.CancelledError:
                pass
