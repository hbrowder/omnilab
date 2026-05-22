from pathlib import Path
import uvicorn, pathlib, logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.responses import Response
import httpx
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from api.labs import router as labs_router
from api.license import router as license_router
from api.billing import router as billing_router
from api.nodes import router as nodes_router
from api.networks import router as networks_router
from api.templates import router as templates_router
from api.system import router as system_router
from api.health import router as health_router
from api.backup import router as backup_router
from api.updates import router as updates_router
from api.console import router as console_router
from core.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnilab")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("OmniLab running!")
    yield

app = FastAPI(title="OmniLab", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=False)
