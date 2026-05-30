"""
Authentication & User Management API (CRE-53)

Endpoints:
- POST /api/auth/register - Register new user (admin-only)
- POST /api/auth/login - Login and get JWT token
- POST /api/auth/logout - Logout (client-side token deletion)
- GET /api/auth/me - Get current user info
- POST /api/auth/refresh - Refresh JWT token

- GET /api/users/ - List all users (admin-only)
- GET /api/users/{user_id} - Get user details (admin or self)
- PUT /api/users/{user_id} - Update user (admin or self)
- DELETE /api/users/{user_id} - Delete user (admin-only)
- PATCH /api/users/{user_id}/password - Change password (admin or self)
- PATCH /api/users/{user_id}/activate - Activate/deactivate user (admin-only)
"""
import uuid
from datetime import datetime

from core.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from core.database import get_db
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "readonly"  # admin, power-user, readonly
    full_name: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None


class PasswordChange(BaseModel):
    current_password: str | None = None  # Not required if admin
    new_password: str


# ============================================================================
# Dependency: Get current user from JWT token
# ============================================================================

async def get_current_user(authorization: str | None = Header(None)):
    """
    Extract and validate JWT token from Authorization header.

    Returns user payload or raises 401.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Verify user still exists and is active
    async for db in get_db():
        async with db.execute(
            "SELECT id, username, role, is_active FROM users WHERE id = ?",
            (payload["sub"],)
        ) as cur:
            user = await cur.fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="User not found")

            if not user["is_active"]:
                raise HTTPException(status_code=403, detail="User account is disabled")

            return dict(user)


async def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency: Require admin role."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


# ============================================================================
# Auth Endpoints
# ============================================================================

@router.post("/register", status_code=201)
async def register_user(data: RegisterRequest, current_user: dict = Depends(require_admin)):
    """
    Register a new user (admin-only).

    First user (when no users exist) can self-register as admin.
    """
    # Validate role
    if data.role not in ["admin", "power-user", "readonly"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    user_id = str(uuid.uuid4())
    password_hash = hash_password(data.password)
    now = datetime.utcnow().isoformat()

    async for db in get_db():
        try:
            await db.execute(
                """INSERT INTO users (
                    id, username, email, password_hash, role, full_name,
                    is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (
                    user_id, data.username, data.email, password_hash,
                    data.role, data.full_name, now, now
                )
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(status_code=400, detail="Username or email already exists") from e
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}") from e

    return {
        "id": user_id,
        "username": data.username,
        "email": data.email,
        "role": data.role,
        "created_at": now,
    }


@router.post("/login")
async def login(data: LoginRequest):
    """
    Login with username/password and receive JWT token.
    """
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM users WHERE username = ?", (data.username,)
        ) as cur:
            user = await cur.fetchone()

            if not user:
                raise HTTPException(status_code=401, detail="Invalid credentials")

            if not user["is_active"]:
                raise HTTPException(status_code=403, detail="Account is disabled")

            if not verify_password(data.password, user["password_hash"]):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            # Update last_login
            await db.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), user["id"])
            )
            await db.commit()

    # Generate JWT
    token = create_access_token(user["id"], user["username"], user["role"])

    return LoginResponse(
        access_token=token,
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "full_name": user["full_name"],
        }
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout (client must delete token - stateless JWT).
    """
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user's info."""
    async for db in get_db():
        async with db.execute(
            "SELECT id, username, email, role, full_name, last_login, created_at FROM users WHERE id = ?",
            (current_user["id"],)
        ) as cur:
            user = await cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return dict(user)


@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """Refresh JWT token (extend expiry)."""
    token = create_access_token(
        current_user["id"],
        current_user["username"],
        current_user["role"]
    )
    return {"access_token": token, "token_type": "bearer"}


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.get("/users/")
async def list_users(current_user: dict = Depends(require_admin)):
    """List all users (admin-only)."""
    async for db in get_db():
        async with db.execute(
            "SELECT id, username, email, role, full_name, is_active, last_login, created_at FROM users ORDER BY created_at DESC"
        ) as cur:
            users = await cur.fetchall()
            return [dict(u) for u in users]


@router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get user details.

    Users can view their own profile, admins can view anyone.
    """
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Permission denied")

    async for db in get_db():
        async with db.execute(
            "SELECT id, username, email, role, full_name, is_active, last_login, created_at FROM users WHERE id = ?",
            (user_id,)
        ) as cur:
            user = await cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return dict(user)


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user profile.

    Users can update their own email/full_name.
    Admins can update anyone's role/email/full_name.
    """
    # Permission check
    is_admin = current_user["role"] == "admin"
    is_self = current_user["id"] == user_id

    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Non-admins cannot change role
    if data.role and not is_admin:
        raise HTTPException(status_code=403, detail="Cannot change your own role")

    updates = []
    params = []

    if data.email:
        updates.append("email = ?")
        params.append(data.email)

    if data.full_name is not None:
        updates.append("full_name = ?")
        params.append(data.full_name)

    if data.role and is_admin:
        if data.role not in ["admin", "power-user", "readonly"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        updates.append("role = ?")
        params.append(data.role)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = ?")
    params.append(datetime.utcnow().isoformat())
    params.append(user_id)

    async for db in get_db():
        try:
            await db.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(status_code=400, detail="Email already in use") from e
            raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}") from e

    return {"success": True, "message": "User updated"}


@router.patch("/users/{user_id}/password")
async def change_password(
    user_id: str,
    data: PasswordChange,
    current_user: dict = Depends(get_current_user)
):
    """
    Change user password.

    Users must provide current_password to change their own.
    Admins can reset anyone's password without current_password.
    """
    is_admin = current_user["role"] == "admin"
    is_self = current_user["id"] == user_id

    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Permission denied")

    async for db in get_db():
        # If changing own password, verify current password
        if is_self and not is_admin:
            async with db.execute(
                "SELECT password_hash FROM users WHERE id = ?", (user_id,)
            ) as cur:
                user = await cur.fetchone()
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")

                if not data.current_password:
                    raise HTTPException(status_code=400, detail="current_password required")

                if not verify_password(data.current_password, user["password_hash"]):
                    raise HTTPException(status_code=401, detail="Current password is incorrect")

        # Update password
        new_hash = hash_password(data.new_password)
        try:
            await db.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (new_hash, datetime.utcnow().isoformat(), user_id)
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Password change failed: {str(e)}") from e

    return {"success": True, "message": "Password updated"}


@router.patch("/users/{user_id}/activate")
async def toggle_user_activation(
    user_id: str,
    is_active: bool,
    current_user: dict = Depends(require_admin)
):
    """
    Activate or deactivate a user account (admin-only).

    Prevents user from logging in without deleting their data.
    """
    async for db in get_db():
        async with db.execute("SELECT id FROM users WHERE id = ?", (user_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="User not found")

        try:
            await db.execute(
                "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
                (1 if is_active else 0, datetime.utcnow().isoformat(), user_id)
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Activation toggle failed: {str(e)}") from e

    status = "activated" if is_active else "deactivated"
    return {"success": True, "message": f"User {status}"}


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str, current_user: dict = Depends(require_admin)):
    """
    Delete a user (admin-only).

    Cannot delete yourself (prevents lockout).
    """
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    async for db in get_db():
        async with db.execute("SELECT id FROM users WHERE id = ?", (user_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="User not found")

        try:
            await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}") from e
