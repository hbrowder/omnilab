#!/usr/bin/env python3
"""
CRE-53: Bootstrap first admin user.

Run once to create the initial admin account.
"""
import asyncio
import getpass
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from core.auth import hash_password
from core.database import get_db


async def create_admin():
    """Create first admin user interactively."""
    print("\n🔐 OmniLab Admin Bootstrap")
    print("=" * 50)
    
    # Check if users already exist
    async for db in get_db():
        async with db.execute("SELECT COUNT(*) as count FROM users") as cur:
            result = await cur.fetchone()
            if result["count"] > 0:
                print(f"❌ Users already exist ({result['count']} found).")
                print("   Use the API to create additional users.")
                return
    
    # Collect admin details
    print("\nCreate your admin account:\n")
    
    username = input("Username: ").strip()
    if not username:
        print("❌ Username cannot be empty")
        return
    
    email = input("Email: ").strip()
    if not email:
        print("❌ Email cannot be empty")
        return
    
    full_name = input("Full name (optional): ").strip() or None
    
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm password: ")
    
    if password != password_confirm:
        print("❌ Passwords do not match")
        return
    
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return
    
    # Create admin user
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    now = datetime.utcnow().isoformat()
    
    async for db in get_db():
        try:
            await db.execute(
                """INSERT INTO users (
                    id, username, email, password_hash, role, full_name,
                    is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'admin', ?, 1, ?, ?)""",
                (user_id, username, email, password_hash, full_name, now, now)
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"❌ Failed to create admin: {e}")
            return
    
    print("\n✅ Admin user created successfully!")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Role: admin")
    print("\n🚀 You can now login via: POST /api/auth/login")


if __name__ == "__main__":
    asyncio.run(create_admin())
