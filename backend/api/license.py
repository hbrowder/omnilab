"""
OmniLab License API
Handles license key validation and tier enforcement.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import hmac
import hashlib
import base64
import secrets
import json
import os

router = APIRouter()

# Secret used to sign license keys. In production this would be embedded
# in the binary/package and not in source. For now, generated on first run.
SECRET_FILE = os.path.join(os.path.dirname(__file__), '..', '.license_secret')
if not os.path.exists(SECRET_FILE):
    with open(SECRET_FILE, 'w') as f:
        f.write(secrets.token_hex(32))
with open(SECRET_FILE, 'r') as f:
    LICENSE_SECRET = f.read().strip().encode()

# Free tier limits
FREE_TIER_NODES = 2
FREE_TIER_LABS = 1


def sign_payload(payload: str) -> str:
    """Generate HMAC-SHA256 signature, return first 16 chars base32."""
    sig = hmac.new(LICENSE_SECRET, payload.encode(), hashlib.sha256).digest()
    return base64.b32encode(sig).decode()[:16].upper()


def generate_key(plan: str, customer: str = "user") -> str:
    """Generate a license key. plan = 'free' or 'pro'."""
    payload = f"{plan}:{customer}"
    sig = sign_payload(payload)
    # Format: OMNI-XXXX-XXXX-XXXX-XXXX
    grouped = '-'.join([sig[i:i+4] for i in range(0, 16, 4)])
    return f"OMNI-{grouped}"


def verify_key(key: str) -> Optional[dict]:
    """Verify a license key. Returns {plan, customer} if valid, None if not."""
    if not key or not key.startswith('OMNI-'):
        return None
    # Strip "OMNI-" and dashes
    sig = key[5:].replace('-', '')
    if len(sig) != 16:
        return None
    # Try matching against known plans
    for plan in ['free', 'pro', 'enterprise']:
        for customer in ['user', 'admin', 'beta']:
            payload = f"{plan}:{customer}"
            if hmac.compare_digest(sign_payload(payload), sig):
                return {'plan': plan, 'customer': customer}
    return None


class LicenseActivate(BaseModel):
    key: str


@router.get("/status")
async def get_license_status():
    """Get current license info."""
    # Read stored license
    license_file = os.path.join(os.path.dirname(__file__), '..', '.license.json')
    if not os.path.exists(license_file):
        return {
            'plan': 'free',
            'activated': False,
            'limits': {
                'max_nodes': FREE_TIER_NODES,
                'max_labs': FREE_TIER_LABS,
            },
            'features': {
                'export_import': True,
                'templates': True,
                'console': True,
                'config_editor': True,
                'multi_lab': False,
                'unlimited_nodes': False,
            }
        }
    with open(license_file, 'r') as f:
        license_data = json.load(f)
    plan = license_data.get('plan', 'free')
    return {
        'plan': plan,
        'activated': True,
        'customer': license_data.get('customer'),
        'key_last4': license_data.get('key', '')[-4:],
        'limits': {
            'max_nodes': -1 if plan in ('pro', 'enterprise') else FREE_TIER_NODES,
            'max_labs': -1 if plan in ('pro', 'enterprise') else FREE_TIER_LABS,
        },
        'features': {
            'export_import': True,
            'templates': True,
            'console': True,
            'config_editor': True,
            'multi_lab': plan in ('pro', 'enterprise'),
            'unlimited_nodes': plan in ('pro', 'enterprise'),
        }
    }


@router.post("/activate")
async def activate_license(payload: LicenseActivate):
    """Activate a license key."""
    info = verify_key(payload.key.strip())
    if not info:
        raise HTTPException(status_code=400, detail="Invalid license key")
    
    # Store activated license
    license_file = os.path.join(os.path.dirname(__file__), '..', '.license.json')
    with open(license_file, 'w') as f:
        json.dump({
            'key': payload.key.strip(),
            'plan': info['plan'],
            'customer': info['customer'],
        }, f)
    
    return {
        'status': 'activated',
        'plan': info['plan'],
        'customer': info['customer'],
    }


@router.post("/deactivate")
async def deactivate_license():
    """Remove the activated license (revert to free tier)."""
    license_file = os.path.join(os.path.dirname(__file__), '..', '.license.json')
    if os.path.exists(license_file):
        os.remove(license_file)
    return {'status': 'deactivated', 'plan': 'free'}


@router.post("/generate")
async def generate_license_key(plan: str = 'pro', customer: str = 'user'):
    """
    Generate a new license key. 
    In production, this endpoint should be removed or require admin auth.
    For now, useful for testing.
    """
    if plan not in ('free', 'pro', 'enterprise'):
        raise HTTPException(status_code=400, detail="Invalid plan")
    if customer not in ('user', 'admin', 'beta'):
        raise HTTPException(status_code=400, detail="Invalid customer")
    key = generate_key(plan, customer)
    return {'key': key, 'plan': plan, 'customer': customer}


def check_tier_limit(current_count: int, resource: str) -> bool:
    """Returns True if action is allowed, False if blocked by free tier."""
    license_file = os.path.join(os.path.dirname(__file__), '..', '.license.json')
    if not os.path.exists(license_file):
        plan = 'free'
    else:
        with open(license_file, 'r') as f:
            plan = json.load(f).get('plan', 'free')
    
    if plan in ('pro', 'enterprise'):
        return True
    
    # Free tier
    if resource == 'nodes':
        return current_count < FREE_TIER_NODES
    if resource == 'labs':
        return current_count < FREE_TIER_LABS
    return True
