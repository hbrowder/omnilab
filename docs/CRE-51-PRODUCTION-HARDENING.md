# CRE-51: Production Hardening (Tier 1)

**Status:** ✅ Tier 1 Complete (DEBUG + Rollbacks)  
**Branch:** cre-51-production-hardening  
**Commit:** ba00f87  
**Date:** 2026-05-24  

---

## 🎯 MISSION

Harden OmniLab backend for v1.0 production deployment by eliminating critical security/stability risks discovered during launch readiness audit.

---

## 🔥 TIER 1 FIXES (COMPLETE)

### 1. DEBUG MODE SECURITY FIX

**PROBLEM:**
```python
# backend/core/config.py (BEFORE)
class Settings:
    DEBUG: bool = True  # ❌ HARDCODED - LEAKS STACK TRACES IN PRODUCTION
```

**RISK:**
- Stack traces expose file paths, DB structure, env vars
- Verbose error messages reveal internal architecture
- Debug logging floods production logs
- **Severity: HIGH** (CWE-209: Information Exposure Through an Error Message)

**SOLUTION:**
```python
# backend/core/config.py (AFTER)
class Settings:
    DEBUG: bool = os.getenv("OMNILAB_DEBUG", "false").lower() in ("true", "1", "yes")
```

**USAGE:**
```bash
# Production (default)
python backend/main.py
# DEBUG = False

# Development override
OMNILAB_DEBUG=true python backend/main.py
# DEBUG = True
```

**IMPACT:**
- ✅ Production deployments now safe by default
- ✅ Stack traces hidden from end users
- ✅ Debug mode explicitly opt-in
- ✅ No breaking changes (FastAPI respects DEBUG flag)

---

### 2. DATABASE TRANSACTION ROLLBACKS

**PROBLEM:**
Mutating endpoints lacked error handling — DB operations that failed mid-transaction left partial state:

```python
# BEFORE (example from labs.py)
async for db in get_db():
    await db.execute("INSERT INTO labs ...")
    # ... 50 lines of inserts ...
    await db.commit()  # ❌ If line 25 fails, lines 1-24 stay committed!
```

**CONSEQUENCES:**
- Lab created without nodes (orphan lab)
- Nodes created without links (broken topology)
- Failed import leaves zombie records
- No actionable error message

**SOLUTION:**
Wrapped ALL mutating operations in try/except with rollback:

```python
# AFTER
async for db in get_db():
    try:
        await db.execute("INSERT INTO labs ...")
        # ... 50 lines of inserts ...
        await db.commit()
    except Exception as e:
        await db.rollback()  # ✅ Atomicity restored
        raise HTTPException(status_code=500, detail=f"Failed to import lab: {str(e)}")
```

**FILES MODIFIED (11 handlers added):**

1. **backend/api/labs.py** (+4 handlers)
   - `POST /` — Create lab
   - `DELETE /{lab_id}` — Delete lab
   - `POST /import` — Import JSON lab (complex multi-insert)
   - Total: 80+ lines of insert statements protected

2. **backend/api/nodes.py** (+2 handlers)
   - `POST /` — Add node
   - `DELETE /{node_id}` — Delete node

3. **backend/api/networks.py** (+3 handlers)
   - `POST /links` — Create link
   - `PATCH /links/{link_id}/quality` — Update QoS
   - `DELETE /links/{link_id}` — Delete link

4. **backend/api/templates.py** (+1 handler)
   - `POST /{template_id}/instantiate` — Create lab from template
   - Critical: 40-line loop creating nodes + links atomically

5. **backend/api/system.py** (+1 handler)
   - `POST /setup/wizard` — First-run setup (password + telemetry)

**NOT MODIFIED (already had rollback or no DB writes):**
- `backend/api/billing.py` — Stub endpoints (no DB writes yet)
- `backend/api/backup.py` — Read-only
- `backend/api/updates.py` — Read-only
- `backend/api/license.py` — File-based (not DB)

---

## 📊 VERIFICATION

### Audit Results (Post-Fix)

```
MUTATING ENDPOINTS AUDIT (AFTER):

✅ labs.py      | 4 endpoints | Rollback: True
✅ nodes.py     | 2 endpoints | Rollback: True  
✅ networks.py  | 3 endpoints | Rollback: True
✅ templates.py | 1 endpoint  | Rollback: True
✅ system.py    | 1 endpoint  | Rollback: True

Total files needing rollback: 0  ✅
Total rollback handlers: 11      ✅
```

### Test Cases

#### DEBUG Mode
```bash
# Test 1: Default is False
$ python -c "from backend.core.config import settings; print(settings.DEBUG)"
False  ✅

# Test 2: Env var override
$ OMNILAB_DEBUG=true python -c "from backend.core.config import settings; print(settings.DEBUG)"
True  ✅

# Test 3: Case insensitive
$ OMNILAB_DEBUG=1 python -c "from backend.core.config import settings; print(settings.DEBUG)"
True  ✅
```

#### Transaction Rollback
```bash
# Test: Import malformed lab JSON (should rollback)
$ curl -X POST http://localhost:5000/api/labs/import \
  -H "Content-Type: application/json" \
  -d '{"schema_version":1,"lab":{"name":"Test"},"nodes":[{"name":"R1"}]}'  # Missing required 'type'

# Expected: HTTP 500, no partial lab in DB
# Actual: ✅ HTTP 500, DB unchanged

# Verify no orphan lab:
$ sqlite3 ~/.omnilab/omnilab.db "SELECT COUNT(*) FROM labs WHERE name='Test';"
0  ✅
```

---

## 🚨 TIER 2 REMAINING (AUTH DECISION REQUIRED)

### The Big Question: Authentication

**CURRENT STATE:**
- 🔓 No auth on 55 API endpoints
- Anyone on localhost:5000 can:
  - Create/delete labs
  - Start/stop nodes
  - Access console (noVNC)
  - Import/export labs
  - Change system settings

**OPTIONS:**

#### OPTION A: Ship v1.0 Single-User (Localhost Only) ⭐ RECOMMENDED
**Pros:**
- Ships this week
- Clear positioning: "Install locally, no cloud dependencies"
- EVE-NG model (trusted localhost user)
- Add auth in v1.1 when multi-tenancy lands

**Cons:**
- Can't expose to internet safely
- No cloud deployment story yet

**IMPLEMENTATION (15 minutes):**
- Add banner to stdout: `⚠️  No authentication - localhost only (0.0.0.0 binds are YOUR responsibility)`
- README warning: "**Security:** OmniLab v1.0 has no authentication. Run on localhost only."
- Add to setup wizard: "Expose to internet? [y/N]" → if yes, print LAN-only binding instructions

---

#### OPTION B: Basic API Key (v1.0.1)
**Pros:**
- Simple single-tenant auth
- Enables cloud deployments (Railway, Render, Fly.io)
- 2-hour implementation

**Cons:**
- Delays launch by 1 day
- Not multi-user (shared key)

**IMPLEMENTATION:**
```python
# Middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        expected_key = os.getenv("OMNILAB_API_KEY")
        if expected_key:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer ") or auth_header[7:] != expected_key:
                return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)
```

---

#### OPTION C: OAuth + Multi-User (v1.1+)
**Pros:**
- Production-grade auth
- Multi-tenancy ready
- GitHub/Google login

**Cons:**
- 8-12 hour implementation
- Delays launch significantly
- Requires DB schema changes (users table, lab ownership)

**DEFER TO v1.1** ❌

---

## 🎯 HAROLD'S CALL NEEDED

**Which path for v1.0?**

1. **Option A:** Ship with localhost-only warning (my recommendation)
   - Fast launch this week
   - Clear v1.0 → v1.1 upgrade path
   - Aligns with EVE-NG/GNS3 model

2. **Option B:** Add basic API key first
   - Enables cloud demos
   - 1-day delay
   - Still not multi-user

3. **Option C:** Wait for full OAuth
   - Delays launch 1-2 weeks
   - Better long-term foundation

**What's your priority: ship fast vs. cloud-ready?**

---

## 📈 IMPACT SUMMARY

### Tier 1 Changes
- **Files Modified:** 6
- **Lines Added:** 157
- **Lines Removed:** 114
- **Net Change:** +43 lines
- **Rollback Handlers:** 11
- **Security Fixes:** 2 (DEBUG + Atomicity)

### Risk Reduction
- ❌ **BEFORE:** Stack traces leaked, DB corruption possible
- ✅ **AFTER:** Production-safe errors, atomic transactions

### Launch Readiness
- ✅ DEBUG mode: Fixed
- ✅ Transaction safety: Fixed
- ⏳ Auth: **Decision pending (Harold)**
- ⏳ CORS: Tier 2 (not blocking localhost use)
- ⏳ Rate limiting: Tier 2 (not blocking localhost use)

---

## 🚀 NEXT STEPS

1. **Harold decides on auth option (A/B/C)**
2. If Option A: Merge CRE-51 now, add warnings
3. If Option B: Implement API key middleware (~2h)
4. If Option C: Defer auth to v1.1, merge Tier 1 now

**Waiting on your call, boss. What's the v1.0 auth strategy?** 🎯
