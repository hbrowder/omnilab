# CRE-64: Drawing Tools API - Text Objects (rectangles, circles, text)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime
import aiosqlite

from core.database import get_db

router = APIRouter(prefix="/api/labs", tags=["textobjects"])

# ── Pydantic Models ──

class TextObjectCreate(BaseModel):
    type: str  # 'rectangle', 'circle', 'text'
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    fill: str = "rgba(88,166,255,0.3)"
    stroke: str = "rgba(88,166,255,1)"
    text: str = ""
    z_index: int = 0

class TextObjectUpdate(BaseModel):
    type: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    fill: Optional[str] = None
    stroke: Optional[str] = None
    text: Optional[str] = None
    z_index: Optional[int] = None

class TextObjectResponse(BaseModel):
    id: str
    lab_id: str
    type: str
    x: float
    y: float
    width: Optional[float]
    height: Optional[float]
    fill: str
    stroke: str
    text: str
    z_index: int
    created_at: str
    updated_at: Optional[str] = None

# ── CRUD Endpoints ──

@router.get("/{lab_id}/textobjects")
async def list_textobjects(lab_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """List all text objects (shapes + text annotations) for a lab"""
    async with db.execute(
        "SELECT * FROM textobjects WHERE lab_id=? ORDER BY z_index ASC, created_at",
        (lab_id,)
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

@router.post("/{lab_id}/textobjects")
async def create_textobject(
    lab_id: str,
    obj_data: TextObjectCreate,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Create a new text object (shape or annotation)"""
    obj_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    await db.execute(
        """INSERT INTO textobjects 
        (id, lab_id, type, x, y, width, height, fill, stroke, text, z_index, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (obj_id, lab_id, obj_data.type, obj_data.x, obj_data.y,
         obj_data.width, obj_data.height, obj_data.fill, obj_data.stroke,
         obj_data.text, obj_data.z_index, now, now)
    )
    await db.commit()
    
    return {"id": obj_id, "lab_id": lab_id, **obj_data.dict(), 
            "created_at": now, "updated_at": now}

@router.get("/{lab_id}/textobjects/{obj_id}")
async def get_textobject(
    lab_id: str, 
    obj_id: str, 
    db: aiosqlite.Connection = Depends(get_db)
):
    """Get a single text object"""
    async with db.execute(
        "SELECT * FROM textobjects WHERE id=? AND lab_id=?",
        (obj_id, lab_id)
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Text object not found")
        return dict(row)

@router.patch("/{lab_id}/textobjects/{obj_id}")
async def update_textobject(
    lab_id: str,
    obj_id: str,
    obj_data: TextObjectUpdate,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Update a text object"""
    # Build dynamic UPDATE query from non-None fields
    updates = {k: v for k, v in obj_data.dict(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in updates.keys())
    values = list(updates.values()) + [obj_id, lab_id]
    
    result = await db.execute(
        f"UPDATE textobjects SET {set_clause} WHERE id=? AND lab_id=?",
        values
    )
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Text object not found")
    
    # Return updated object
    async with db.execute(
        "SELECT * FROM textobjects WHERE id=?",
        (obj_id,)
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row)

@router.delete("/{lab_id}/textobjects/{obj_id}")
async def delete_textobject(
    lab_id: str,
    obj_id: str,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Delete a text object"""
    result = await db.execute(
        "DELETE FROM textobjects WHERE id=? AND lab_id=?",
        (obj_id, lab_id)
    )
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Text object not found")
    
    return {"success": True, "id": obj_id}
