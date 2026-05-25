# CRE-68: Traffic Filter API (Phase 1)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime
import aiosqlite

from core.database import get_db

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
    title: Optional[str] = None
    expr: Optional[str] = None
    color: Optional[str] = None
    timeout: Optional[int] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None

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
    updated_at: Optional[str] = None

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
    
    return {"status": "deleted", "id": filter_id}

@router.post("/{lab_id}/filters/{filter_id}/toggle")
async def toggle_filter(
    lab_id: str, 
    filter_id: str, 
    db: aiosqlite.Connection = Depends(get_db)
):
    """Toggle a filter's enabled state"""
    async with db.execute(
        "SELECT enabled FROM traffic_filters WHERE id=? AND lab_id=?",
        (filter_id, lab_id)
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Filter not found")
        
        new_state = not bool(row[0])
    
    await db.execute(
        "UPDATE traffic_filters SET enabled=?, updated_at=? WHERE id=? AND lab_id=?",
        (int(new_state), datetime.utcnow().isoformat(), filter_id, lab_id)
    )
    await db.commit()
    
    return {"enabled": new_state}
