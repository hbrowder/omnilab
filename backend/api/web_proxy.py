"""Web-UI reverse proxy for docker-node web interfaces (CRE-39 phase 3).

Mounts ``/labs/{lab_id}/nodes/{node_id}/web/{path}`` and proxies to
``http://<container-ip-on-lab-network>:<web_port>/<path>``.

Why a single backend-side reverse proxy instead of host port-publishing:
- The user only needs port 5000 reachable; we don't have to allocate
  20000-29999 host ports.
- Stable URL pattern, no per-deploy port lookup.
- Works behind NAT.
- Reuses the existing Guacamole proxy pattern in main.py.

The route lives in its own router so main.py mounts it ABOVE the SPA
catch-all. Both HTTP and WebSocket upgrades are handled — Wazuh, Open-WebUI,
Jenkins all use WS for live dashboards.

Per-node configuration: ``node.config["web_port"]`` (integer) declares the
container-internal port to proxy. Optional ``node.config["web_scheme"]``
(``"http"`` or ``"https"``) defaults to ``"http"``. Both are read by the
template-deploy step and persisted into the ``nodes.config`` JSON column.
"""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
from core.database import get_db
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from services.docker_provisioner import (
    DockerProvisioner,
    DockerProvisionerError,
)

logger = logging.getLogger("omnilab.web_proxy")

router = APIRouter()

# Lazy provisioner singleton — same pattern as nodes.py / console.py so the
# proxy stays usable on hosts without docker (the route just 503s instead of
# crashing at import time).
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


# Hop-by-hop headers per RFC 7230 §6.1 — must not be forwarded.
_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)


async def _lookup_node(node_id: str, lab_id: str) -> tuple[dict, dict]:
    """Return (node_row, parsed_config). Raises HTTPException on miss."""
    async for db in get_db():
        async with db.execute(
            "SELECT id, lab_id, type, image, status, config FROM nodes "
            "WHERE id = ? AND lab_id = ?",
            (node_id, lab_id),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Node not found in lab")
        node = dict(row)
        try:
            cfg = json.loads(node.get("config") or "{}") or {}
        except (TypeError, ValueError):
            cfg = {}
        return node, cfg
    # Shouldn't reach (get_db yields at least once), but pleases the type checker.
    raise HTTPException(status_code=500, detail="DB session unavailable")


def _filter_response_headers(headers: httpx.Headers) -> dict:
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in _HOP_BY_HOP:
            continue
        # Strip Content-Encoding too — httpx already decoded the body for us,
        # so forwarding the original gzip/br header would mis-describe the
        # bytes we send back.
        if k.lower() == "content-encoding":
            continue
        out[k] = v
    return out


def _filter_request_headers(headers) -> dict:
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in _HOP_BY_HOP:
            continue
        out[k] = v
    return out


def _backend_url(scheme: str, ip: str, port: int, path: str, query: str) -> str:
    url = f"{scheme}://{ip}:{port}/{path}"
    if query:
        url = f"{url}?{query}"
    return url


# ---------------------------------------------------------------- HTTP proxy


@router.api_route(
    "/labs/{lab_id}/nodes/{node_id}/web/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def web_proxy(lab_id: str, node_id: str, path: str, request: Request):
    """Proxy any HTTP method to the docker node's web port."""
    node, cfg = await _lookup_node(node_id, lab_id)

    if (node.get("type") or "").lower() != "docker":
        raise HTTPException(
            status_code=400, detail="Web proxy is only supported for docker nodes"
        )
    if node.get("status") != "running":
        raise HTTPException(status_code=409, detail="Node is not running")

    web_port = cfg.get("web_port")
    if not isinstance(web_port, int):
        raise HTTPException(
            status_code=404, detail="Node has no web_port configured"
        )
    scheme = cfg.get("web_scheme") or "http"
    if scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid web_scheme")

    try:
        p = _get_provisioner()
    except DockerProvisionerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        ip = await p.get_node_address(node_id, lab_id)
    except DockerProvisionerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not ip:
        raise HTTPException(
            status_code=502,
            detail="Node container has no IP on the lab network",
        )

    url = _backend_url(scheme, ip, web_port, path, str(request.url.query))
    headers = _filter_request_headers(request.headers)
    body = await request.body()

    # verify=False — lab containers commonly use self-signed certs.
    try:
        async with httpx.AsyncClient(
            timeout=30.0, follow_redirects=False, verify=False
        ) as client:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
            )
    except httpx.RequestError as exc:
        logger.warning("web_proxy backend error %s -> %s: %s", node_id, url, exc)
        raise HTTPException(status_code=502, detail=f"Backend unreachable: {exc}") from exc

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=_filter_response_headers(resp.headers),
        media_type=resp.headers.get("content-type"),
    )


# ----------------------------------------------------------------- WS proxy


async def _ws_pipe(read_fn, write_fn, stop: asyncio.Event) -> None:
    """One-direction pump. read_fn -> write_fn until either side errors."""
    try:
        while not stop.is_set():
            try:
                msg = await read_fn()
            except (WebSocketDisconnect, Exception):
                break
            if msg is None:
                break
            try:
                await write_fn(msg)
            except Exception:
                break
    finally:
        stop.set()


@router.websocket("/labs/{lab_id}/nodes/{node_id}/web-ws/{path:path}")
async def web_ws_proxy(
    lab_id: str, node_id: str, path: str, ws: WebSocket
):
    """Bidirectional WebSocket bridge to the docker node's web socket endpoint.

    Wazuh dashboard, Open-WebUI streaming chat, Jenkins build-log tailing all
    use WS — this is the channel for them. Browser opens
    ``ws://omnilab/labs/<id>/nodes/<id>/web-ws/<path>`` and frames flow
    transparently to the container's matching ``ws://<ip>:<port>/<path>``.
    """
    await ws.accept()

    try:
        node, cfg = await _lookup_node(node_id, lab_id)
    except HTTPException as exc:
        await ws.send_text(f"ERROR: {exc.detail}")
        await ws.close()
        return

    if (node.get("type") or "").lower() != "docker":
        await ws.send_text("ERROR: Web proxy is only supported for docker nodes")
        await ws.close()
        return
    if node.get("status") != "running":
        await ws.send_text("ERROR: Node is not running")
        await ws.close()
        return

    web_port = cfg.get("web_port")
    if not isinstance(web_port, int):
        await ws.send_text("ERROR: Node has no web_port configured")
        await ws.close()
        return
    ws_scheme = "wss" if (cfg.get("web_scheme") == "https") else "ws"

    try:
        p = _get_provisioner()
        ip = await p.get_node_address(node_id, lab_id)
    except DockerProvisionerError as exc:
        await ws.send_text(f"ERROR: {exc}")
        await ws.close()
        return
    if not ip:
        await ws.send_text("ERROR: Node container has no IP on the lab network")
        await ws.close()
        return

    target_url = f"{ws_scheme}://{ip}:{web_port}/{path}"

    # websockets library is already a transitive dep via uvicorn; import lazily
    # so the rest of the router doesn't pay for it when no one's using WS.
    try:
        import websockets  # type: ignore[import-untyped]
    except ImportError:  # pragma: no cover
        await ws.send_text("ERROR: websockets library not installed")
        await ws.close()
        return

    try:
        # Pass through the upgrade subprotocols the browser asked for.
        async with websockets.connect(target_url) as upstream:  # type: ignore[attr-defined]
            stop = asyncio.Event()

            async def _from_browser():
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    return None
                if "bytes" in msg and msg["bytes"] is not None:
                    return msg["bytes"]
                if "text" in msg and msg["text"] is not None:
                    return msg["text"]
                return None

            async def _from_upstream():
                try:
                    return await upstream.recv()
                except Exception:
                    return None

            async def _to_upstream(data):
                await upstream.send(data)

            async def _to_browser(data):
                if isinstance(data, bytes):
                    await ws.send_bytes(data)
                else:
                    await ws.send_text(data)

            t1 = asyncio.create_task(_ws_pipe(_from_browser, _to_upstream, stop))
            t2 = asyncio.create_task(_ws_pipe(_from_upstream, _to_browser, stop))
            try:
                await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
            finally:
                stop.set()
                for t in (t1, t2):
                    t.cancel()
                    try:
                        await t
                    except asyncio.CancelledError:
                        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("web_ws_proxy connect failed %s: %s", target_url, exc)
        try:
            await ws.send_text(f"ERROR: Upstream WS unreachable: {exc}")
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


# ------------------------------------------------------------- info endpoint


@router.get("/api/labs/{lab_id}/nodes/{node_id}/web-info")
async def web_info(lab_id: str, node_id: str):
    """Describe whether a node has a web UI, and what URL the frontend should hit."""
    node, cfg = await _lookup_node(node_id, lab_id)
    web_port: int | None = cfg.get("web_port") if isinstance(cfg.get("web_port"), int) else None
    return {
        "node_id": node_id,
        "lab_id": lab_id,
        "has_web_ui": web_port is not None,
        "web_port": web_port,
        "web_scheme": cfg.get("web_scheme") or "http",
        "proxy_url": (
            f"/labs/{lab_id}/nodes/{node_id}/web/" if web_port is not None else None
        ),
        "ws_proxy_url_prefix": (
            f"/labs/{lab_id}/nodes/{node_id}/web-ws/" if web_port is not None else None
        ),
    }
