import logging
import pathlib
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from api.backup import router as backup_router
from api.billing import router as billing_router
from api.console import router as console_router
from api.health import router as health_router
from api.labs import router as labs_router
from api.license import router as license_router
from api.networks import router as networks_router
from api.nodes import router as nodes_router
from api.system import router as system_router
from api.templates import router as templates_router
from api.updates import router as updates_router
from api.web_proxy import router as web_proxy_router
from core.database import init_db
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnilab")

# Request timing stats for health metrics
_request_times: list[float] = []
_max_samples = 100


def get_avg_latency_ms() -> float:
    """Return average API latency in milliseconds over the last N requests."""
    if not _request_times:
        return 0.0
    return sum(_request_times) / len(_request_times)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # CRE-39 phase 4: surface docker socket reachability at startup. We don't
    # FAIL the boot on missing docker — the app still works for QEMU/PTY/VNC
    # nodes — but we log a loud, actionable hint so the user knows why
    # docker-typed nodes will 503 later.
    try:
        from services.docker_provisioner import (
            DockerProvisioner,
            DockerProvisionerError,
        )
        try:
            DockerProvisioner()
            logger.info("Docker daemon reachable — docker templates available.")
        except DockerProvisionerError as exc:
            logger.warning(
                "Docker daemon unreachable: %s "
                "Docker-typed nodes will 503 until this is fixed. "
                "If running as a non-root user, add yourself to the 'docker' "
                "group (sudo usermod -aG docker $USER && newgrp docker).",
                exc,
            )
    except Exception as exc:  # noqa: BLE001 — never let the docker check kill the app
        logger.warning("Docker reachability check skipped (%s)", exc)
    logger.info("OmniLab running!")
    yield

app = FastAPI(title="OmniLab", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# Request timing middleware for /api/health/metrics
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    # Only track API calls (ignore static files, websockets, health endpoint itself to avoid recursion)
    if request.url.path.startswith("/api") and "/health" not in request.url.path:
        _request_times.append(elapsed_ms)
        if len(_request_times) > _max_samples:
            _request_times.pop(0)
    
    return response

app.include_router(license_router, prefix="/api/license", tags=["license"])
app.include_router(billing_router, prefix="/api/billing", tags=["billing"])
app.include_router(labs_router,      prefix="/api/labs")
app.include_router(nodes_router,     prefix="/api/nodes")
app.include_router(networks_router,  prefix="/api/networks")
app.include_router(templates_router, prefix="/api/templates")
app.include_router(updates_router,  prefix="/api/updates",   tags=["updates"])
app.include_router(backup_router,   prefix="/api/backup",    tags=["backup"])
app.include_router(health_router,   prefix="/api/health",    tags=["health"])
app.include_router(system_router,    prefix="/api/system")
app.include_router(console_router,   prefix="/api/console")
# CRE-39: docker-node web-UI reverse proxy. Routes are
#   /labs/{lab_id}/nodes/{node_id}/web/*       (HTTP)
#   /labs/{lab_id}/nodes/{node_id}/web-ws/*    (WebSocket)
#   /api/labs/{lab_id}/nodes/{node_id}/web-info (metadata)
# MUST be included before the SPA catch-all below so requests aren't swallowed.
app.include_router(web_proxy_router)


# Reverse proxy for Guacamole web app
GUAC_BASE = "http://127.0.0.1:8080"

@app.api_route("/guacamole/{path:path}", methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD"])
async def guacamole_proxy(path: str, request: Request):
    url = f"{GUAC_BASE}/guacamole/{path}"
    qs = str(request.url.query)
    if qs:
        url = url + "?" + qs
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("content-length", None)
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
        media_type=resp.headers.get("content-type"),
    )

DIST = pathlib.Path.home() / "netlab/frontend/dist"

# Serve noVNC static files for VNC console
NOVNC_DIR = pathlib.Path.home() / "netlab/backend/static/novnc"
if NOVNC_DIR.exists():
    app.mount("/novnc", StaticFiles(directory=str(NOVNC_DIR)), name="novnc")

@app.get("/")
async def root():
    return FileResponse(str(DIST / "index.html"))

# CRE-21: serve the rebuilt Stripe checkout page
@app.get("/checkout", include_in_schema=False)
def serve_checkout():
    return FileResponse(str(Path(__file__).parent / "static" / "checkout.html"))

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    file_path = DIST / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    return FileResponse(str(DIST / "index.html"))

if __name__ == "__main__":
    import sys
    
    # Security banner for v1.0 (localhost-only deployment model)
    print("\n" + "="*70)
    print("  OmniLab v1.0 - Network Emulation Platform")
    print("="*70)
    print("  ⚠️  SECURITY NOTICE: No authentication enabled")
    print("     → Safe for: localhost-only deployments")
    print("     → Unsafe for: internet-exposed or LAN-wide deployments")
    print("     → Multi-user auth coming in v1.1")
    print("="*70 + "\n")
    
    # Warn if binding to 0.0.0.0 (accessible beyond localhost)
    host = sys.argv[sys.argv.index("--host") + 1] if "--host" in sys.argv else "0.0.0.0"
    if host in ("0.0.0.0", "0"):
        print("⚠️  WARNING: Binding to 0.0.0.0 exposes OmniLab to your network")
        print("   Anyone on your network can access this instance WITHOUT authentication.")
        print("   Press Ctrl+C within 5 seconds to cancel...\n")
        import time
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n✋ Startup cancelled by user\n")
            sys.exit(0)
    
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=False)
