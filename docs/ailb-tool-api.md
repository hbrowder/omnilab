# AI Lab Builder — Tool API Contract

**Issue:** CRE-41 (AILB-1, spike) · **Status:** reviewed & refined — awaiting sign-off on D1/D3 · **Owner:** hbrowder
**Consumed by:** CRE-42 (read/construct tools), CRE-43 (lifecycle tools), CRE-44 (LLM loop)

This is the contract for the tools the LLM agent calls to build and run a lab from a
natural-language prompt. No implementation here — just shapes, side effects, error
modes, and a worked trace. The OSPF trace at the bottom is the **test-harness target
for CRE-44**.

> Three decisions were left open in CRE-41. Recommendations are in
> [§5 Open decisions](#5-open-decisions) and are marked **PROPOSED — needs sign-off**.
> Everything else assumes those proposals are accepted; revisit if you choose otherwise.

> **Review pass (CRE-41 refine, 2026-05-29).** This contract was cross-checked against
> the real backend (`core/database.py`, `api/labs.py`, `api/nodes.py`, `api/templates.py`,
> `services/docker_provisioner.py`, `api/console.py`) and against the CRE-42 draft in the
> tree. Refinements are folded in below and flagged **[refined]**. Net effect: **D2 holds
> as proposed; D1 and D3 still need your sign-off** (see [§5](#5-open-decisions)). The
> implementation realities CRE-42 must honor are gathered in
> [§8 Implementation notes](#8-implementation-notes-for-cre-42).

---

## 1. Conventions

**Transport.** All tools are synchronous request/response over the in-process tool
layer (`backend/services/agent_tools.py`), exposed for HTTP testing at
`POST /api/agent/tools/{name}` (CRE-42). The agent's *overall* progress streams to the
client via SSE from `/api/agent/build` (CRE-44) — that is separate from per-tool
transport. See decision D1.

**Response envelope.** Every tool returns the same shape:

```json
{
  "ok": true,
  "data": { },
  "error": null
}
```

On failure:

```json
{
  "ok": false,
  "data": null,
  "error": { "code": "NOT_FOUND", "message": "node nd_7f3 does not exist", "details": {} }
}
```

**Error codes (closed set):**

| code | meaning |
|---|---|
| `NOT_FOUND` | referenced lab/node/link id does not exist |
| `INVALID_IMAGE` | image not in inventory |
| `INVALID_TYPE` | node type not supported for that image |
| `LINK_EXISTS` | a link already joins those two interfaces |
| `IFACE_IN_USE` | requested interface already linked |
| `NODE_NOT_RUNNING` | operation needs a running node (e.g. live config push) |
| `CAPACITY_EXCEEDED` | host limits (RAM/CPU/node count) would be exceeded |
| `CONFIG_REJECTED` | node rejected the pushed config (syntax/apply error) |
| `TIMEOUT` | node did not reach target state within the deadline |
| `VALIDATION` | malformed arguments (missing field, bad enum) |

**IDs.** Opaque strings — **never** parse them. **[refined]** The live backend stores
bare `uuid4` strings with **no prefix** (`labs.id`, `nodes.id`, `links.id` in
`core/database.py`; both `api/labs.py` and `api/nodes.py` mint `str(uuid.uuid4())`). The
`lab_*/nd_*/lk_*` forms used throughout this doc are **illustrative for readability
only**. CRE-42 returns whatever the DB row's `id` is verbatim; agents must treat every id
as an opaque token. (The draft's `_id()` helper that synthesizes `lab_<hex8>` is dropped
in favor of the real `uuid4` ids — see §8.)

**Idempotency.** `create_*` and `link_nodes` are NOT idempotent (calling twice makes
two objects). `start_node`/`stop_node` ARE idempotent (starting a running node is a
no-op success). Agents should read state before retrying.

---

## 2. Read / introspection tools

### `list_inventory()`
What node images/types the host can run. Call this first; never hard-code image names.

- **Args:** none
- **Side effects:** none (read-only)
- **Returns:**

```json
{
  "images": [
    { "image": "frrouting/frr:latest", "kind": "router", "types": ["docker"],
      "default_ifaces": ["eth0","eth1","eth2","eth3"], "ram_mb": 256 },
    { "image": "kalilinux/kali-rolling", "kind": "host", "types": ["docker"], "ram_mb": 1024 },
    { "image": "ceos:4.32", "kind": "switch", "types": ["docker"], "ram_mb": 2048 }
  ],
  "host": { "free_ram_mb": 12000, "max_nodes": 64, "running_nodes": 3 }
}
```

- **Errors:** none expected.

> **[refined] mapping to the real backend.** No single inventory source exists today; CRE-42
> assembles this envelope:
> - `images[]` ← the `templates` table (`core/database.py`) + the built-in `TEMPLATES` dict in
>   `api/templates.py`. Real columns are `image`, `type` (**singular** — not a `types[]` array;
>   keep `types` as a one-element list derived from it), `ram`, `category`, `vendor`.
> - `kind` is **derived** (router/host/switch) from `category`/image name — there is no `kind`
>   column. CRE-42 owns the mapping table.
> - `default_ifaces` is **not stored anywhere** (no column on `templates` or `nodes`). CRE-42
>   supplies it from a per-image default map (e.g. FRR/cEOS → `eth0..eth3`, hosts → `eth0`). See §8.
> - `host.max_nodes` ← license tier (`api/license.py`), `host.running_nodes` ← `COUNT(*) FROM
>   nodes WHERE status='running'` (as `api/health.py` already does). `host.free_ram_mb` ← psutil
>   (`api/health.py` reads host RAM); if unavailable, return `null` rather than a fabricated number.

### `get_lab_state(lab_id)`  *(decision D3 — agent's view of the topology)*
The agent's single source of truth for what exists. Used between steps and for the
final summary.

- **Args:** `{ "lab_id": "lab_*" }`
- **Side effects:** none
- **Returns:**

```json
{
  "lab": { "lab_id": "lab_a1", "name": "OSPF Areas 0/1", "node_count": 4, "link_count": 3 },
  "nodes": [
    { "node_id": "nd_r1", "name": "r1", "image": "frrouting/frr:latest",
      "state": "running", "ifaces": ["eth0"] }
  ],
  "links": [
    { "link_id": "lk_1", "a": { "node_id": "nd_r1", "iface": "eth0" },
      "b": { "node_id": "nd_r2", "iface": "eth0" } }
  ]
}
```

- **Errors:** `NOT_FOUND`.

> **[refined] D3 — reuse, don't reinvent.** `api/labs.py` already exposes
> `GET /api/labs/{lab_id}/topology` returning `{nodes, links}` straight from the DB. CRE-42's
> `get_lab_state` should **wrap and reshape** that, not query in parallel. Three mappings the
> reshaper owns: (a) DB column is `status`; this contract exposes it as **`state`** — rename on
> the way out, and map any legacy status values onto the §2 `state` enum. (b) `node.ifaces` is
> **derived** — there is no ifaces column; compute it as the union of `src_interface`/`dst_interface`
> from `links` where the node is an endpoint, backfilled by the image's `default_ifaces`. (c) link
> rows are `{src_node_id, dst_node_id, src_interface, dst_interface}` → reshape to the `{a:{node_id,
> iface}, b:{node_id, iface}}` form above. `node_count`/`link_count` are `COUNT(*)`, not stored.

### `get_node_state(node_id)`
Fine-grained state for one node. Primary polling tool after `start_node`, and the seam
the future troubleshooter assistant reads from.

- **Args:** `{ "node_id": "nd_*" }`
- **Side effects:** none
- **Returns:**

```json
{ "node_id": "nd_r1", "name": "r1", "state": "running",
  "started_at": "2026-05-28T14:02:10Z", "ifaces": ["eth0","eth1"], "last_error": null }
```

- **`state` enum:** `created | starting | running | stopping | stopped | error`
- **Errors:** `NOT_FOUND`.

---

## 3. Construction tools (CRE-42)

### `create_lab(name, description?)`
- **Args:** `{ "name": "OSPF Areas 0/1", "description": "OSPF area 0 + area 1, FRR x4" }`
- **Side effects:** inserts a `labs` row. No nodes yet.
- **Returns:** `{ "lab_id": "lab_a1" }`
- **Errors:** `VALIDATION`.

### `create_node(lab_id, name, image, type?, options?)`
- **Args:**

```json
{ "lab_id": "lab_a1", "name": "r1", "image": "frrouting/frr:latest",
  "type": "docker", "options": { "ram_mb": 256, "x": 100, "y": 200 } }
```

- `type` defaults to the image's first supported type from `list_inventory`.
- `options.x/y` are optional canvas coordinates (kept consistent with the CRE-71 canvas).
- **Side effects:** inserts a `nodes` row. Does NOT start the container (Docker path from
  CRE-39 is invoked at `start_node`, not here).
- **Returns:** `{ "node_id": "nd_r1", "ifaces": ["eth0","eth1","eth2","eth3"] }`
- **Errors:** `NOT_FOUND` (lab), `INVALID_IMAGE`, `INVALID_TYPE`, `CAPACITY_EXCEEDED`, `VALIDATION`.

### `link_nodes(lab_id, a, b, options?)`
Connects two interfaces. Interfaces may be named explicitly or auto-assigned (next free).

- **Args:**

```json
{ "lab_id": "lab_a1",
  "a": { "node_id": "nd_r1", "iface": "eth0" },
  "b": { "node_id": "nd_r2", "iface": "eth0" },
  "options": { "style": "solid" } }
```

- If `iface` is omitted on a side, the backend assigns the next free interface and
  returns it.
- **Side effects:** inserts a `links` row; creates the underlying L2 segment (reuses the
  existing bridge networking path).
- **Returns:** `{ "link_id": "lk_1", "a_iface": "eth0", "b_iface": "eth0" }`
- **Errors:** `NOT_FOUND`, `IFACE_IN_USE`, `LINK_EXISTS`, `CAPACITY_EXCEEDED`, `VALIDATION`.

---

## 4. Lifecycle / mutation tools (CRE-43)

### `push_config(node_id, config_text, mode?)`
Sends configuration to a node. **No general shell** — see decision D2.

- **Args:** `{ "node_id": "nd_r1", "config_text": "...", "mode": "startup" }`
- **`mode` enum:** `startup` (written to the node's config volume, applied at/with boot)
  or `live` (applied to a running node via the node's native config channel — e.g. FRR
  vtysh, serial console for QEMU). `live` requires `state == running`.
- **Side effects:** writes/loads config. May restart the node's routing daemons for
  `startup` mode depending on image.
- **Returns:** `{ "applied": true, "mode": "startup", "warnings": [] }`
- **Errors:** `NOT_FOUND`, `NODE_NOT_RUNNING` (live mode on a stopped node),
  `CONFIG_REJECTED` (with `details.lines` pointing at offending lines), `VALIDATION`.

### `start_node(node_id)`  *(decision D1 — long-running)*
Boots the node. **PROPOSED:** blocks until `running` or a 60s deadline; if the deadline
passes it returns `state: "starting"` (not an error) and the agent polls
`get_node_state`. This keeps every tool a plain request/response and avoids a second
WS transport.

- **Args:** `{ "node_id": "nd_r1" }`
- **Side effects:** starts the container/VM (CRE-39 Docker path).
- **Returns:** `{ "node_id": "nd_r1", "state": "running" }` or `{ ..., "state": "starting" }`
- **Errors:** `NOT_FOUND`, `CAPACITY_EXCEEDED`, `TIMEOUT` (only on hard failure), `error` state in body.
- **Idempotent:** starting a running node returns `running` with no side effect.

> **[refined] D1 reality check.** Today `services/docker_provisioner.start_node` runs the docker
> SDK in `asyncio.to_thread` with `detach=True` and `container.reload()` — i.e. it returns once the
> container is **created**, not **ready**, and `api/nodes.py` then reports `running` unconditionally
> with **no polling loop**. So the "blocks ≤60s then returns `starting`" behavior is **not built yet**;
> it is CRE-43 work. Two things this contract must nail down now (they need your call — see §5/D1):
> (1) make **`starting`** a first-class third return value (the current text elsewhere implies only
> `running`-or-error); (2) the 60s deadline is too tight for a first-run image **pull** (frr ≈300MB
> can exceed it) — separate "pull" from "boot", or raise the deadline to ~120–300s, or stream. Until
> CRE-43 lands the deadline+poll, `start_node` returns immediately and the agent **must** poll
> `get_node_state` (the trace in §7 already does this — keep it).

### `stop_node(node_id)`
- **Args:** `{ "node_id": "nd_*" }`
- **Returns:** `{ "node_id": "nd_*", "state": "stopped" }`
- **Errors:** `NOT_FOUND`. Idempotent.

### `delete_lab(lab_id)`
Cleanup, including on agent error/abort. Stops and removes all nodes, links, and the lab row.

- **Args:** `{ "lab_id": "lab_*", "force": true }`
- **Side effects:** destructive and irreversible. Stops every node first.
- **Returns:** `{ "deleted": true, "nodes_removed": 4, "links_removed": 3 }`
- **Errors:** `NOT_FOUND`.
- **Note:** the CRE-44 loop should call this on unrecoverable failure so a half-built lab
  isn't left running and burning host RAM.

> **[refined].** The current `DELETE /api/labs/{lab_id}` (`api/labs.py`) only deletes the lab row
> (FK `ON DELETE CASCADE` drops nodes/links) — it does **not** stop running containers first, so
> raw use would orphan them. CRE-43's `delete_lab` must iterate `stop_node` over the lab's nodes
> **before** the row delete. The `force` arg in the example has no backend equivalent yet; treat it
> as "stop-then-delete unconditionally" (the only mode v1 needs) or drop it.

---

## 5. Open decisions

**D1 — Sync vs. streaming tool results. PROPOSED:** all tools synchronous;
`start_node` blocks-with-deadline then falls back to polling `get_node_state`. The
agent's overall run streams via SSE at `/api/agent/build` (CRE-44). *Rationale:* one
transport for tools = far simpler to unit-test (CRE-42 wants HTTP-level tests) and
avoids mixing WS + SSE. CRE-41 originally floated a WS for `start_node`; this proposal
overrides that — flag if you disagree.

> **⚠ Review verdict: NEEDS YOUR SIGN-OFF (revise).** The all-sync transport is sound and is
> exactly what CRE-42's HTTP tests want — keep it. But two sub-points are genuinely yours to
> decide because the codebase doesn't settle them: **(D1a)** the start deadline. The live docker
> path returns at container-*create*, not *ready*, and a first-run image pull can blow past 60s.
> Pick one: **(i)** keep sync, raise the deadline to ~120–300s and accept a blocked HTTP thread;
> **(ii)** keep sync at ~60s and rely on the agent polling `get_node_state` (the §7 trace already
> does); or **(iii)** add a narrow SSE/WS channel for `start_node` only. *Recommendation: (ii)* —
> cheapest, already reflected in the trace, deadline+poll formalized in CRE-43. **(D1b)** confirm
> `starting` is an accepted third return value (not an error). The async-DB bridge is **not** a
> decision — it's settled mechanics, see §8.

**D2 — Expose raw `run_command` (docker exec / QEMU console)? PROPOSED: no, not in
v1.** Scope tightly to `push_config` + lifecycle. *Rationale:* a general shell tool is a
security and blast-radius problem (an agent running arbitrary commands in containers),
and it's hard to test deterministically. The troubleshooter assistant (later phase) gets
a *read-only* `get_node_state` / log tool instead. If a future phase needs exec, add it
behind an explicit operator-enabled flag.

> **✅ Review verdict: HOLDS — no change needed.** The codebase backs this up: `api/console.py`
> already provides authenticated `docker exec`/console **for human operators**, so debugging access
> exists without handing the agent a shell. Note for CRE-43: `push_config` `mode:"live"` will use
> that same exec channel *internally* (e.g. FRR vtysh) — that is an implementation detail of
> `push_config`, **not** a new agent-facing tool, so D2 stays intact.

**D3 — How the agent sees the topology. PROPOSED: `get_lab_state(lab_id)` → JSON**
(defined in §2). Accepted as designed.

> **⚠ Review verdict: NEEDS YOUR SIGN-OFF (shape).** The *decision* (a JSON topology read) is
> right, but it overlaps an existing endpoint, so confirm the **shape policy**: `GET
> /api/labs/{lab_id}/topology` already returns `{nodes, links}` from the DB. Choose: **(i)** keep
> `get_lab_state` as a thin reshaper over that endpoint (recommended — single source of truth, the
> reshape rules are in §2's refined note: `status→state`, derived `ifaces`, `{a,b}` link form,
> counts), or **(ii)** let the agent consume the raw `/topology` shape directly and drop the bespoke
> envelope. *Recommendation: (i).*

---

## 6. Cost / safety rails (carry into CRE-44)

Per the Hermes incident (CRE-40), the build loop that drives these tools must:
- set a hard `max_tokens` per model call (do not inherit a 32k default),
- cap `max_iterations` (default ~20) and total tool calls per run,
- call `delete_lab` on unrecoverable error to avoid orphaned running nodes,
- prefer a cheaper model for non-reasoning phases where the script allows.

**[refined] additional rails surfaced by review:**
- **`push_config` deadline.** A hung config channel (vtysh / serial console) blocks the tool
  indefinitely. Give `push_config` a per-call timeout → `TIMEOUT` error (CRE-43).
- **Reuse existing disk safety.** `api/labs.py` already does a pre-flight `<10%` free-disk check
  and `docker_provisioner` raises on `ENOSPC` — surface those as `CAPACITY_EXCEEDED` rather than
  re-inventing, so the agent gets a clean failure instead of a 500.
- **Orphan GC.** If the agent process dies mid-run, `delete_lab`-on-error never fires. Consider a
  TTL/GC sweep or a manual cleanup endpoint (flag for CRE-44, not blocking).

---

## 7. Worked example trace

Prompt: **"build me an OSPF area 0/1 lab with 4 routers."**

Target topology: R1–R2 in area 0; R2 is the ABR; R2–R3 and R3–R4 in area 1.

```
1.  list_inventory()
      -> frrouting/frr:latest available (kind=router)

2.  create_lab(name="OSPF Areas 0/1", description="area 0 + area 1, FRR x4")
      -> lab_id=lab_a1

3.  create_node(lab_a1, "r1", "frrouting/frr:latest")   -> nd_r1
    create_node(lab_a1, "r2", "frrouting/frr:latest")   -> nd_r2   (ABR)
    create_node(lab_a1, "r3", "frrouting/frr:latest")   -> nd_r3
    create_node(lab_a1, "r4", "frrouting/frr:latest")   -> nd_r4

4.  link_nodes(lab_a1, {nd_r1,eth0}, {nd_r2,eth0})  -> lk_1   # 10.0.12.0/30  area 0
    link_nodes(lab_a1, {nd_r2,eth1}, {nd_r3,eth0})  -> lk_2   # 10.0.23.0/30  area 1
    link_nodes(lab_a1, {nd_r3,eth1}, {nd_r4,eth0})  -> lk_3   # 10.0.34.0/30  area 1

5.  push_config(nd_r1, "<frr: eth0 10.0.12.1/30; ospf router-id 1.1.1.1; net 10.0.12.0/30 area 0>", mode=startup)
    push_config(nd_r2, "<frr: eth0 10.0.12.2/30 area 0; eth1 10.0.23.1/30 area 1; router-id 2.2.2.2>", mode=startup)
    push_config(nd_r3, "<frr: eth0 10.0.23.2/30; eth1 10.0.34.1/30; net both area 1; router-id 3.3.3.3>", mode=startup)
    push_config(nd_r4, "<frr: eth0 10.0.34.2/30; net 10.0.34.0/30 area 1; router-id 4.4.4.4>", mode=startup)

6.  start_node(nd_r1) -> running
    start_node(nd_r2) -> running
    start_node(nd_r3) -> running
    start_node(nd_r4) -> running

7.  get_node_state(nd_*) x4 until all == running   (poll; deadline-backed)

8.  get_lab_state(lab_a1)
      -> 4 nodes running, 3 links; return summary to user
```

**Acceptance for CRE-44:** running this prompt produces 4 nodes, 2 OSPF areas, 3 links,
all nodes reach `running`, and (verification phase, CRE-48) OSPF adjacencies on the R2
ABR come up in both area 0 and area 1. The exact config strings above are illustrative;
the real FRR snippets live in the CRE-48 scenario fixtures.

---

## 8. Implementation notes for CRE-42

Not part of the contract surface — these are the **settled mechanics** the CRE-42 wiring must
honor (found by reviewing the draft `services/agent_tools.py` + `api/agent.py` against the real
backend). They are not open decisions; they're the seams to wire.

1. **Import convention.** The app puts `backend/` on `sys.path` (see `tests/conftest.py`,
   `main.py` uses `from api.labs import router`). The draft's `from backend.services import
   agent_tools` will **not** import under the test harness — use `from services import agent_tools`.
2. **Router registration.** `api/agent.py`'s router is **not yet** mounted in `main.py`. Mount it
   **above the SPA catch-all** (CRE-42's own pitfall note), e.g. `app.include_router(agent_router)`.
3. **Sync tools over an async DB — settled, not a decision.** The tool fns are sync; the DB
   (`core/database.py`) is async `aiosqlite`. The `Repo` impl bridges this. Two acceptable patterns:
   (a) the `Repo` opens its **own synchronous `sqlite3`** connection to the same `DB_PATH` (cleanest
   for sync tools — no event-loop juggling); or (b) tools become `async` and the FastAPI wrapper
   `await`s them. Pick (a) unless CRE-44 needs async tools anyway. Tests inject a fake `Repo`, so
   the choice is invisible to the tool logic.
4. **Drop the synthetic `_id()`.** Use the DB's `uuid4` ids verbatim (see §1).
5. **`default_ifaces` map lives in CRE-42.** Since neither `templates` nor `nodes` store interfaces,
   CRE-42 owns the per-image default-iface table; `free_iface`/`iface_in_use` compute against the
   `links` table.
6. **Docker is a lazy singleton.** Any capacity/inventory call that touches docker must reuse the
   lazy-singleton in `services/docker_provisioner.py` — do not construct a new client.
7. **Test bar.** Suite lives at repo-root `tests/` (`testpaths=["tests"]`), not `backend/tests/`.
   Add `tests/test_agent_tools.py` (success + failure per tool, fake `Repo`) and an
   `@pytest.mark.integration` 2-node lab build. Baseline at review time: **126 passed, 8 pre-existing
   failures** in `test_enospc_handling.py`/`test_first_run.py` (unrelated, billing/first-run paths) —
   do not regress the 126; the 8 are out of scope.
