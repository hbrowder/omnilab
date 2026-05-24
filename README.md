# OmniLab

> A self-hostable network lab platform — design topologies in the browser,
> deploy them to real KVM/QEMU VMs, and manage everything from a single REST
> API.

Status: pre-launch, v1.0 in active development. Tracking board:
[Linear → Creator Buddy / OmniLab v1.0](https://linear.app/harold-browder/team/CRE).

---

## Tech stack

| Layer        | Tech                                                                  |
| ------------ | --------------------------------------------------------------------- |
| Backend      | Python 3, FastAPI, Uvicorn, SQLite (aiosqlite), httpx                 |
| Frontend     | React 18, Vite 5, Zustand, React Router, ReactFlow, Three.js, xterm.js|
| Virt         | KVM / QEMU                                                            |
| Remote view  | Apache Guacamole (mounted under `/guacamole/*` via reverse proxy)     |
| Distribution | `.deb` installer, CLI, auto-update checker                            |
| Billing      | Stripe Checkout                                                       |

---

## Repository layout

```
netlab/
├── backend/        FastAPI app — main.py + api/*.py routers, core/, services/
├── frontend/       Vite + React SPA — src/, dist/ (built bundle served by FastAPI)
├── docs/           Operator + developer docs
└── README.md       (this file)
```

Runtime data lives outside the repo at `~/.omnilab/` (database, snapshots, lab
state, VM images).

---

## Running locally

```bash
# Backend (Python venv lives at ~/omnilab-env)
source ~/omnilab-env/bin/activate
cd backend
python main.py                 # listens on :5000

# Or use the supervised loop:
~/start-omnilab.sh             # while-true respawn

# Frontend (dev mode with HMR)
cd frontend
npm install
npm run dev                    # listens on :5173
```

**⚠️ Security Notice (v1.0):**  
OmniLab v1.0 has **no authentication**. It is designed for **localhost-only** single-user deployments (similar to EVE-NG Community Edition). Do NOT expose port 5000 to:
- The internet (public IP)
- Your LAN (0.0.0.0 binding without firewall)
- Untrusted users

Multi-user authentication is coming in **v1.1**. For now, treat OmniLab like a local development tool.

Health check: `curl http://localhost:5000/api/system/health`

---

## Lab templates

OmniLab ships with 10 pre-configured "golden lab" templates that one-click
deploy into a working topology (Docker-backed nodes today, KVM-backed nodes
coming in v1.1). The full ledger of templates and their current status —
plus the smoke-test harness used to verify them — lives in
[docs/TEMPLATES.md](docs/TEMPLATES.md).

To verify all templates end-to-end against the live docker daemon:

```bash
~/omnilab-env/bin/python ~/omnilab/scripts/smoke_test_templates.py
```

This deploys each template, starts every node, verifies the containers are
actually running (not "exited-after-init"), hits the web-UI reverse proxy
for nodes that expose one, and cleans up between templates. Results land at
`/tmp/smoke_test_results.json`.

---

## Development workflow

See [docs/CLAUDE_TOOLING.md](docs/CLAUDE_TOOLING.md) for the canonical
session-start runbook (WeTTY + Claude Desktop Cowork) and the list of pitfalls
to avoid (FastAPI catch-all ordering, heredoc/JSX gotchas, backend respawn
behavior, etc.).

All work is tracked in Linear under the **CRE** team. Issues are assigned to
the engineer driving them and moved through `Backlog → Todo → In Progress →
Done`.

---

## License

Proprietary — © Harold Browder. All rights reserved (pending public license
decision before v1.0 launch).
