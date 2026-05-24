import json
import shutil
import uuid

from core.database import get_db
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class LabCreate(BaseModel):
    name: str
    description: str | None = ""
    category: str | None = "general"

@router.get("/")
async def list_labs():
    async for db in get_db():
        async with db.execute("SELECT * FROM labs ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]

@router.post("/", status_code=201)
async def create_lab(data: LabCreate):
    # CRE-49: Pre-flight disk space check — refuse lab creation if <10% free
    try:
        disk = shutil.disk_usage("/")
        disk_free_percent = (disk.free / disk.total) * 100
        if disk_free_percent < 10:
            raise HTTPException(
                status_code=507,  # HTTP 507 Insufficient Storage
                detail=(
                    f"Cannot create lab: only {disk_free_percent:.1f}% disk space remaining. "
                    "Free space with 'docker system prune' or 'omnilab gc --apply' before creating new labs."
                )
            )
    except HTTPException:
        raise
    except Exception:
        # Never let disk check kill lab creation if shutil fails
        pass
    
    lab_id = str(uuid.uuid4())
    async for db in get_db():
        await db.execute("INSERT INTO labs (id, name, description, category) VALUES (?, ?, ?, ?)",
            (lab_id, data.name, data.description, data.category))
        await db.commit()
    return {"id": lab_id, "name": data.name, "status": "stopped"}

@router.get("/{lab_id}")
async def get_lab(lab_id: str):
    async for db in get_db():
        async with db.execute("SELECT * FROM labs WHERE id = ?", (lab_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Lab not found")
            return dict(row)

@router.delete("/{lab_id}", status_code=204)
async def delete_lab(lab_id: str):
    async for db in get_db():
        await db.execute("DELETE FROM labs WHERE id = ?", (lab_id,))
        await db.commit()

@router.get("/{lab_id}/topology")
async def get_topology(lab_id: str):
    async for db in get_db():
        async with db.execute("SELECT * FROM nodes WHERE lab_id = ?", (lab_id,)) as cur:
            nodes = [dict(r) for r in await cur.fetchall()]
        async with db.execute("SELECT * FROM links WHERE lab_id = ?", (lab_id,)) as cur:
            links = [dict(r) for r in await cur.fetchall()]
        return {"nodes": nodes, "links": links}


@router.get("/{lab_id}/export")
async def export_lab(lab_id: str):
    async for db in get_db():
        async with db.execute("SELECT * FROM labs WHERE id = ?", (lab_id,)) as cur:
            lab_row = await cur.fetchone()
            if not lab_row:
                raise HTTPException(status_code=404, detail="Lab not found")
            lab = dict(lab_row)
        async with db.execute("SELECT * FROM nodes WHERE lab_id = ?", (lab_id,)) as cur:
            node_rows = [dict(r) for r in await cur.fetchall()]
        async with db.execute("SELECT * FROM links WHERE lab_id = ?", (lab_id,)) as cur:
            link_rows = [dict(r) for r in await cur.fetchall()]
    node_by_id = {n["id"]: n for n in node_rows}
    export_nodes = []
    for n in node_rows:
        export_nodes.append({
            "name": n.get("name"),
            "type": n.get("type"),
            "image": n.get("image"),
            "x": n.get("x"),
            "y": n.get("y"),
            "config": n.get("config") or "{}",
        })
    export_links = []
    for link in link_rows:
        src_name = node_by_id.get(link.get("src_node_id"), {}).get("name")
        dst_name = node_by_id.get(link.get("dst_node_id"), {}).get("name")
        if src_name and dst_name:
            export_links.append({"src_name": src_name, "dst_name": dst_name})
    return {
        "schema_version": 1,
        "product": "OmniLab",
        "lab": {
            "name": lab.get("name"),
            "description": lab.get("description") or "",
            "category": lab.get("category") or "general",
        },
        "nodes": export_nodes,
        "links": export_links,
    }


class ImportPayload(BaseModel):
    schema_version: int
    product: str | None = "OmniLab"
    lab: dict
    nodes: list = []
    links: list = []


@router.post("/import", status_code=201)
async def import_lab(payload: ImportPayload):
    if payload.schema_version != 1:
        raise HTTPException(status_code=400,
            detail=f"Unsupported schema_version {payload.schema_version} (this server understands 1)")
    base_name = (payload.lab or {}).get("name") or "Imported Lab"
    description = (payload.lab or {}).get("description") or ""
    category = (payload.lab or {}).get("category") or "general"

    async for db in get_db():
        # Resolve name collision: append (2), (3) ... if needed.
        name = base_name
        suffix = 2
        while True:
            async with db.execute("SELECT 1 FROM labs WHERE name = ?", (name,)) as cur:
                if not await cur.fetchone():
                    break
            name = f"{base_name} ({suffix})"
            suffix += 1
            if suffix > 999:
                raise HTTPException(status_code=409, detail="Too many name collisions")

        lab_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO labs (id, name, description, category) VALUES (?, ?, ?, ?)",
            (lab_id, name, description, category))

        name_to_new_id = {}
        for n in payload.nodes or []:
            new_id = str(uuid.uuid4())
            n_name = n.get("name")
            n_type = n.get("type")
            if not n_name or not n_type:
                continue
            cfg = n.get("config")
            if isinstance(cfg, dict):
                cfg = json.dumps(cfg)
            if cfg is None:
                cfg = "{}"
            await db.execute(
                "INSERT INTO nodes (id, lab_id, name, type, image, config, x, y) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id, lab_id, n_name, n_type, n.get("image"), cfg,
                 n.get("x") or 100, n.get("y") or 100))
            name_to_new_id[n_name] = new_id

        for link in payload.links or []:
            sid = name_to_new_id.get(link.get("src_name"))
            did = name_to_new_id.get(link.get("dst_name"))
            if not sid or not did:
                continue
            await db.execute(
                "INSERT INTO links (id, lab_id, src_node_id, dst_node_id) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), lab_id, sid, did))

        await db.commit()
    return {"id": lab_id, "name": name, "status": "stopped",
            "imported_nodes": len(name_to_new_id),
            "imported_links": len(payload.links or [])}

