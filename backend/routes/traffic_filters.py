# CRE-68: Traffic Filter API (Phase 1 + Phase 3 Milestone 2)
import uuid
from datetime import datetime

import aiosqlite
from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.traffic_service import get_traffic_service  # CRE-68 Phase 3

router = APIRouter(prefix="/api/labs", tags=["traffic-filters"])

# ── Pydantic Models ──

class TrafficFilterCreate(BaseModel):
    title: str
    expr: str
    color: str = "#00ff00"
    timeout: int = 5000
    enabled: bool = True
    priority: int = 0

class TrafficFilterUpdate(BaseModel):
    title: str | None = None
    expr: str | None = None
    color: str | None = None
    timeout: int | None = None
    enabled: bool | None = None
    priority: int | None = None

class TrafficFilterResponse(BaseModel):
    id: str
    lab_id: str
    title: str
    expr: str
    color: str
    timeout: int
    enabled: bool
    priority: int
    created_at: str
    updated_at: str | None = None

# ── CRUD Endpoints ──

@router.get("/{lab_id}/filters")
async def list_filters(lab_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """List all traffic filters for a lab"""
    async with db.execute(
        "SELECT * FROM traffic_filters WHERE lab_id=? ORDER BY priority DESC, created_at",
        (lab_id,)
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

@router.post("/{lab_id}/filters")
async def create_filter(
    lab_id: str,
    filter_data: TrafficFilterCreate,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Create a new traffic filter"""
    filter_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    await db.execute(
        """INSERT INTO traffic_filters
        (id, lab_id, title, expr, color, timeout, enabled, priority, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (filter_id, lab_id, filter_data.title, filter_data.expr,
         filter_data.color, filter_data.timeout, int(filter_data.enabled),
         filter_data.priority, now, now)
    )
    await db.commit()

    return {"id": filter_id, "lab_id": lab_id, **filter_data.dict(),
            "created_at": now, "updated_at": now}

@router.get("/{lab_id}/filters/{filter_id}")
async def get_filter(
    lab_id: str,
    filter_id: str,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Get a single traffic filter"""
    async with db.execute(
        "SELECT * FROM traffic_filters WHERE id=? AND lab_id=?",
        (filter_id, lab_id)
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Filter not found")
        return dict(row)

@router.patch("/{lab_id}/filters/{filter_id}")
async def update_filter(
    lab_id: str,
    filter_id: str,
    filter_data: TrafficFilterUpdate,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Update a traffic filter"""
    # Get current filter state before update
    async with db.execute(
        "SELECT enabled, expr, color FROM traffic_filters WHERE id=? AND lab_id=?",
        (filter_id, lab_id)
    ) as cursor:
        old_row = await cursor.fetchone()
        if not old_row:
            raise HTTPException(status_code=404, detail="Filter not found")
        old_enabled = bool(old_row[0])
        old_expr = old_row[1]
        old_color = old_row[2]

    # Build dynamic UPDATE query
    updates = []
    values = []

    for field, value in filter_data.dict(exclude_unset=True).items():
        if field == "enabled":
            value = int(value)
        updates.append(f"{field}=?")
        values.append(value)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.extend([datetime.utcnow().isoformat(), filter_id, lab_id])

    await db.execute(
        f"""UPDATE traffic_filters
        SET {', '.join(updates)}, updated_at=?
        WHERE id=? AND lab_id=?""",
        tuple(values)
    )
    await db.commit()

    if db.total_changes == 0:
        raise HTTPException(status_code=404, detail="Filter not found")

    # CRE-68 Phase 3: Restart capture if expression or state changed
    traffic_service = get_traffic_service()
    update_dict = filter_data.dict(exclude_unset=True)

    # Get new values (use updated if provided, else old)
    new_enabled = update_dict.get('enabled', old_enabled)
    new_expr = update_dict.get('expr', old_expr)
    new_color = update_dict.get('color', old_color)

    # If expression changed or state changed, restart capture
    if old_enabled and (new_expr != old_expr or new_color != old_color):
        # Restart with new expression/color
        await traffic_service.stop_capture(filter_id)
        if new_enabled:
            await traffic_service.start_capture(lab_id, filter_id, new_expr, new_color)
    elif 'enabled' in update_dict:
        # State changed
        if new_enabled:
            await traffic_service.start_capture(lab_id, filter_id, new_expr, new_color)
        else:
            await traffic_service.stop_capture(filter_id)

    # Return updated filter
    return await get_filter(lab_id, filter_id, db)

@router.delete("/{lab_id}/filters/{filter_id}")
async def delete_filter(
    lab_id: str,
    filter_id: str,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Delete a traffic filter"""
    await db.execute(
        "DELETE FROM traffic_filters WHERE id=? AND lab_id=?",
        (filter_id, lab_id)
    )
    await db.commit()

    if db.total_changes == 0:
        raise HTTPException(status_code=404, detail="Filter not found")

    # CRE-68 Phase 3: Stop capture if it was running
    traffic_service = get_traffic_service()
    await traffic_service.stop_capture(filter_id)

    return {"status": "deleted", "id": filter_id}

@router.post("/{lab_id}/filters/{filter_id}/toggle")
async def toggle_filter(
    lab_id: str,
    filter_id: str,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Toggle a filter's enabled state"""
    # Get current filter state
    async with db.execute(
        "SELECT enabled, expr, color FROM traffic_filters WHERE id=? AND lab_id=?",
        (filter_id, lab_id)
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Filter not found")

        current_enabled = bool(row[0])
        expr = row[1]
        color = row[2]
        new_state = not current_enabled

    # Update database
    await db.execute(
        "UPDATE traffic_filters SET enabled=?, updated_at=? WHERE id=? AND lab_id=?",
        (int(new_state), datetime.utcnow().isoformat(), filter_id, lab_id)
    )
    await db.commit()

    # CRE-68 Phase 3: Start/stop packet capture
    traffic_service = get_traffic_service()
    if new_state:
        # Start capture
        await traffic_service.start_capture(lab_id, filter_id, expr, color)
    else:
        # Stop capture
        await traffic_service.stop_capture(filter_id)

    return {"enabled": new_state}
