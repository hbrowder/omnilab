"""
Template/Image Management API (CRE-55)

CRUD operations for node templates - both built-in (Docker-based labs)
and user-uploaded (QEMU/KVM vendor images like Cisco IOS, Juniper vMX).

Built-in templates (is_builtin=1) cannot be deleted, only hidden.
User templates can be fully managed (create, update, delete).

Endpoints:
- GET /api/template-library/ - List all templates (filterable by visible/category)
- POST /api/template-library/ - Create custom template
- GET /api/template-library/{id} - Get template details
- PUT /api/template-library/{id} - Update template
- PATCH /api/template-library/{id}/visibility - Toggle visibility
- DELETE /api/template-library/{id} - Delete user template
- POST /api/template-library/upload - Upload QEMU image (qcow2/vmdk/ova)
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from core.config import settings
from core.database import get_db
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()

# Image storage directory (QEMU images uploaded by users)
IMAGE_DIR = Path.home() / ".omnilab" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)


class TemplateCreate(BaseModel):
    name: str
    vendor: str | None = None
    category: str
    description: str | None = None
    type: str = "docker"  # docker, qemu, lxc
    image: str  # Docker image ref or path to QEMU disk
    cpu: int = 1
    ram: int = 512  # MB
    disk: int = 10  # GB
    console_type: str = "telnet"  # telnet, ssh, vnc, rdp
    icon: str | None = None
    visible: bool = True
    config: dict = {}


class TemplateUpdate(BaseModel):
    name: str | None = None
    vendor: str | None = None
    category: str | None = None
    description: str | None = None
    image: str | None = None
    cpu: int | None = None
    ram: int | None = None
    disk: int | None = None
    console_type: str | None = None
    icon: str | None = None
    visible: bool | None = None
    config: dict | None = None


@router.get("/")
async def list_templates(
    visible_only: bool = False,
    category: str | None = None,
    type: str | None = None,
):
    """List all templates with optional filtering."""
    async for db in get_db():
        query = "SELECT * FROM templates WHERE 1=1"
        params = []
        
        if visible_only:
            query += " AND visible = 1"
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if type:
            query += " AND type = ?"
            params.append(type)
        
        query += " ORDER BY is_builtin DESC, vendor ASC, name ASC"
        
        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [
                {
                    **dict(row),
                    "config": json.loads(row["config"]) if row["config"] else {}
                }
                for row in rows
            ]


@router.post("/", status_code=201)
async def create_template(data: TemplateCreate):
    """Create a new template (user-uploaded images only, is_builtin=0)."""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    async for db in get_db():
        try:
            await db.execute(
                """INSERT INTO templates (
                    id, name, vendor, category, description, type, image,
                    cpu, ram, disk, console_type, icon, visible, is_builtin,
                    config, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
                (
                    template_id, data.name, data.vendor, data.category, data.description,
                    data.type, data.image, data.cpu, data.ram, data.disk,
                    data.console_type, data.icon, 1 if data.visible else 0,
                    json.dumps(data.config), now, now
                )
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return {
        "id": template_id,
        "name": data.name,
        "vendor": data.vendor,
        "category": data.category,
        "type": data.type,
        "created_at": now,
    }


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get template details by ID."""
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM templates WHERE id = ?", (template_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Template not found")
            return {
                **dict(row),
                "config": json.loads(row["config"]) if row["config"] else {}
            }


@router.put("/{template_id}")
async def update_template(template_id: str, data: TemplateUpdate):
    """
    Update template metadata.
    
    Built-in templates (is_builtin=1) can only update visibility and icon.
    User templates can update everything.
    """
    async for db in get_db():
        # Check if template exists and if it's built-in
        async with db.execute(
            "SELECT is_builtin FROM templates WHERE id = ?", (template_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Template not found")
            is_builtin = row["is_builtin"]
        
        # Build UPDATE query dynamically based on what's provided
        updates = []
        params = []
        
        if data.name is not None and not is_builtin:
            updates.append("name = ?")
            params.append(data.name)
        
        if data.vendor is not None and not is_builtin:
            updates.append("vendor = ?")
            params.append(data.vendor)
        
        if data.category is not None and not is_builtin:
            updates.append("category = ?")
            params.append(data.category)
        
        if data.description is not None and not is_builtin:
            updates.append("description = ?")
            params.append(data.description)
        
        if data.image is not None and not is_builtin:
            updates.append("image = ?")
            params.append(data.image)
        
        if data.cpu is not None and not is_builtin:
            updates.append("cpu = ?")
            params.append(data.cpu)
        
        if data.ram is not None and not is_builtin:
            updates.append("ram = ?")
            params.append(data.ram)
        
        if data.disk is not None and not is_builtin:
            updates.append("disk = ?")
            params.append(data.disk)
        
        if data.console_type is not None and not is_builtin:
            updates.append("console_type = ?")
            params.append(data.console_type)
        
        if data.icon is not None:
            updates.append("icon = ?")
            params.append(data.icon)
        
        if data.visible is not None:
            updates.append("visible = ?")
            params.append(1 if data.visible else 0)
        
        if data.config is not None and not is_builtin:
            updates.append("config = ?")
            params.append(json.dumps(data.config))
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(template_id)
        
        try:
            await db.execute(
                f"UPDATE templates SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return {"success": True, "message": "Template updated"}


@router.patch("/{template_id}/visibility")
async def toggle_visibility(template_id: str, visible: bool):
    """Toggle template visibility (show/hide in UI)."""
    async for db in get_db():
        async with db.execute(
            "SELECT id FROM templates WHERE id = ?", (template_id,)
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Template not found")
        
        try:
            await db.execute(
                "UPDATE templates SET visible = ?, updated_at = ? WHERE id = ?",
                (1 if visible else 0, datetime.utcnow().isoformat(), template_id)
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return {"success": True, "visible": visible}


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: str):
    """
    Delete a user template.
    
    Built-in templates (is_builtin=1) cannot be deleted.
    """
    async for db in get_db():
        async with db.execute(
            "SELECT is_builtin, image FROM templates WHERE id = ?", (template_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Template not found")
            
            if row["is_builtin"]:
                raise HTTPException(
                    status_code=403,
                    detail="Built-in templates cannot be deleted (use visibility toggle instead)"
                )
            
            image_path = row["image"]
        
        try:
            await db.execute("DELETE FROM templates WHERE id = ?", (template_id,))
            await db.commit()
            
            # If image is a local file (not a Docker image ref), delete it
            if image_path and not image_path.startswith(("docker://", "http://", "https://")):
                image_file = Path(image_path)
                if image_file.exists() and IMAGE_DIR in image_file.parents:
                    image_file.unlink()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    name: str | None = None,
    vendor: str | None = None,
    category: str = "networking",
):
    """
    Upload a QEMU/KVM disk image (qcow2, vmdk, ova).
    
    Returns the file path to use in template creation.
    Supports chunked upload for large files (vendor images can be 1-10GB).
    """
    # Validate file extension
    allowed_extensions = {".qcow2", ".vmdk", ".ova", ".raw", ".img"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique filename
    upload_id = str(uuid.uuid4())[:8]
    safe_name = "".join(c for c in (name or file.filename) if c.isalnum() or c in "._- ")
    image_filename = f"{upload_id}_{safe_name}{file_ext}"
    image_path = IMAGE_DIR / image_filename
    
    # Write file in chunks (handle large files)
    try:
        with open(image_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                f.write(chunk)
    except Exception as e:
        # Cleanup partial file on error
        if image_path.exists():
            image_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    return {
        "success": True,
        "image_path": str(image_path),
        "size_bytes": image_path.stat().st_size,
        "filename": image_filename,
        "message": f"Upload complete. Use '{image_path}' as the image path when creating a template."
    }


@router.get("/categories")
async def list_categories():
    """List all unique template categories."""
    async for db in get_db():
        async with db.execute(
            "SELECT DISTINCT category FROM templates WHERE visible = 1 ORDER BY category"
        ) as cur:
            rows = await cur.fetchall()
            return [row["category"] for row in rows if row["category"]]


@router.get("/vendors")
async def list_vendors():
    """List all unique vendors."""
    async for db in get_db():
        async with db.execute(
            "SELECT DISTINCT vendor FROM templates WHERE visible = 1 ORDER BY vendor"
        ) as cur:
            rows = await cur.fetchall()
            return [row["vendor"] for row in rows if row["vendor"]]
