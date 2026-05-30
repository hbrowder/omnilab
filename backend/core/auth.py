"""
Authentication utilities for CRE-53 (Multi-User RBAC)

JWT token generation/validation + password hashing with bcrypt.
"""
import os
from datetime import datetime, timedelta

import bcrypt
import jwt

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET", "omnilab-dev-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str, username: str, role: str) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.

    Returns payload dict if valid, None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# Role hierarchy for permission checks
ROLE_HIERARCHY = {
    "admin": 3,
    "power-user": 2,
    "readonly": 1,
}


def has_permission(user_role: str, required_role: str) -> bool:
    """
    Check if user_role has sufficient permissions.

    Admin can do everything, power-user can do power-user + readonly actions,
    readonly can only do readonly actions.
    """
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level
