# OmniLab backend test suite

Pytest baseline scaffolded by CRE-34.

## Running

```bash
~/netlab-env/bin/pytest                # full suite
~/netlab-env/bin/pytest tests/test_license.py -v
~/netlab-env/bin/pytest -k tier        # by keyword
```

All tests are isolated from your real install:
- `HOME` is redirected to a temp dir at import time, so `core.config`
  creates its `.omnilab/` runtime layout inside that tmp.
- `OMNILAB_LICENSE_DIR` points at a separate tmp dir so license artifacts
  never collide with the real `backend/.license_secret` / `.license.json`.

The `fresh_db` fixture wipes labs/nodes/links between tests that depend
on row counts.

## Coverage map

| File                       | What it covers                                |
| -------------------------- | --------------------------------------------- |
| `test_system_and_health.py`| App boot, route registration, /api/system/*   |
| `test_license.py`          | Key gen/verify, activate/deactivate, tier caps|
| `test_labs.py`             | CRUD, import roundtrip with CRE-26 seed JSON  |
| `test_billing.py`          | 503 envelopes + webhook dispatch (unsigned)   |
| `test_health_metrics.py`   | /api/health/* schema (incl. CRE-7 guard)      |

## What's intentionally NOT tested yet

- KVM/QEMU node lifecycle (needs `/dev/kvm` and root)
- Guacamole proxy (needs a live Guacamole on :8080)
- noVNC static mount (path-dependent)
- WebSocket consoles
- The frontend (separate ticket)

These are integration-test territory — the next pytest layer, behind a
`--integration` mark or a dedicated CI job with KVM enabled.
