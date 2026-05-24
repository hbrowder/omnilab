import uuid

from core.database import get_db
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class LinkCreate(BaseModel):
    lab_id: str
    src_node_id: str
    dst_node_id: str
    style: str | None = "solid"


class LinkQuality(BaseModel):
    delay_ms: int | None = 0
    jitter_ms: int | None = 0
    loss_pct: float | None = 0.0
    bandwidth_kbps: int | None = 0
    style: str | None = None


@router.get("/")
async def list_networks():
    return []


@router.get("/links/{lab_id}")
async def list_links(lab_id: str):
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM links WHERE lab_id = ?", (lab_id,)
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/links", status_code=201)
async def create_link(data: LinkCreate):
    link_id = str(uuid.uuid4())
    async for db in get_db():
        try:
            await db.execute(
                "INSERT INTO links (id, lab_id, src_node_id, dst_node_id, style) VALUES (?, ?, ?, ?, ?)",
                (link_id, data.lab_id, data.src_node_id, data.dst_node_id, data.style or "solid")
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create link: {str(e)}")
    return {"id": link_id, "lab_id": data.lab_id,
            "src_node_id": data.src_node_id, "dst_node_id": data.dst_node_id,
            "style": data.style or "solid",
            "delay_ms": 0, "jitter_ms": 0, "loss_pct": 0.0, "bandwidth_kbps": 0}


@router.patch("/links/{link_id}/quality")
async def set_link_quality(link_id: str, q: LinkQuality):
    """Update quality settings for a link (delay, jitter, loss, bandwidth, style)."""
    async for db in get_db():
        async with db.execute("SELECT * FROM links WHERE id = ?", (link_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Link not found")

        fields = []
        values = []
        if q.delay_ms is not None:
            fields.append("delay_ms = ?")
            values.append(q.delay_ms)
        if q.jitter_ms is not None:
            fields.append("jitter_ms = ?")
            values.append(q.jitter_ms)
        if q.loss_pct is not None:
            fields.append("loss_pct = ?")
            values.append(q.loss_pct)
        if q.bandwidth_kbps is not None:
            fields.append("bandwidth_kbps = ?")
            values.append(q.bandwidth_kbps)
        if q.style is not None:
            fields.append("style = ?")
            values.append(q.style)

        if fields:
            try:
                await db.execute(
                    "UPDATE links SET " + ", ".join(fields) + " WHERE id = ?",
                    values + [link_id]
                )
                await db.commit()
            except Exception as e:
                await db.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to update link quality: {str(e)}")

        async with db.execute("SELECT * FROM links WHERE id = ?", (link_id,)) as cur:
            updated = await cur.fetchone()
        return dict(updated)


@router.delete("/links/{link_id}", status_code=204)
async def delete_link(link_id: str):
    async for db in get_db():
        try:
            await db.execute("DELETE FROM links WHERE id = ?", (link_id,))
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete link: {str(e)}")
    return None
