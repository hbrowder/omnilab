"""
backend/api/agent.py  —  AI Lab Builder, Phase 2 (CRE-42)

Thin FastAPI wrappers exposing the pure-Python tools from services/agent_tools.py
at POST /api/agent/tools/{name}, purely for HTTP-level testing before the LLM loop
(CRE-44) exists. No agent logic here — just arg-passing and envelope conversion.

The /api/agent/build endpoint (the SSE LLM loop) is added later in CRE-44; this file
intentionally stops at the tool surface.

The production ``Repo`` (``SqliteRepo``) is implemented here: it opens a
short-lived synchronous ``sqlite3`` connection per method against
``settings.DB_PATH``. The tools are synchronous; we deliberately do NOT touch
the app's async aiosqlite path. ``get_repo`` is a FastAPI dependency so tests
can override it via ``app.dependency_overrides[get_repo]``.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from core.config import settings
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services import agent_runner
from services import agent_tools as tools
from services.agent_tools import AILBError, err

router = APIRouter(prefix="/api/agent", tags=["agent"])


# ============================================================================
# Inventory derivation helpers (contract §2 list_inventory)
# ============================================================================

# Per-kind default interface map. Routers/switches get four ports; hosts two.
_DEFAULT_IFACES = {
    "router": ["eth0", "eth1", "eth2", "eth3"],
    "switch": ["eth0", "eth1", "eth2", "eth3"],
    "host": ["eth0", "eth1"],
}


def _derive_kind(image: str) -> str:
    """Classify an image into router|switch|host by name keyword."""
    name = (image or "").lower()
    if any(k in name for k in ("frr", "ceos", "cisco", "juniper", "router")):
        return "router"
    if any(k in name for k in ("switch", "ovs")):
        return "switch"
    return "host"


def _default_ifaces_for(image: str) -> list[str]:
    return list(_DEFAULT_IFACES[_derive_kind(image)])


# ============================================================================
# Production Repo — short-lived synchronous sqlite3 connections
# ============================================================================

class SqliteRepo(tools.Repo):
    """Concrete Repo backed by synchronous sqlite3 against settings.DB_PATH.

    Every method opens its own short-lived connection (sets Row factory +
    foreign_keys pragma), runs one query, and returns plain dicts/lists.
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or str(settings.DB_PATH)

    # -- connection plumbing -------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # -- inventory -----------------------------------------------------------
    def _max_nodes(self, conn: sqlite3.Connection) -> int:
        """Node cap from the license tier. free -> FREE_TIER_NODES from
        api/license.py; pro/enterprise -> generous default. The license DB row
        is the source of truth; we never edit license code from here."""
        tier = "free"
        try:
            row = conn.execute("SELECT tier FROM license WHERE id = 1").fetchone()
            if row and row["tier"]:
                tier = row["tier"]
        except sqlite3.Error:
            pass
        if tier in ("pro", "enterprise"):
            return 64
        try:
            from api.license import FREE_TIER_NODES
            return int(FREE_TIER_NODES)
        except Exception:
            return 64

    def inventory(self) -> dict:
        # Build the image set from the templates table UNION the images
        # referenced by the built-in scenario TEMPLATES dict (so a fresh DB is
        # never empty). Each image is classified by keyword and given a per-kind
        # default-iface list + ram_mb (best-effort from templates.ram).
        ram_by_image: dict[str, int | None] = {}
        ordered: list[str] = []

        def _add(image: str | None, ram: int | None = None) -> None:
            if not image or not image.strip():
                return
            if image not in ram_by_image:
                ram_by_image[image] = ram
                ordered.append(image)
            elif ram is not None and ram_by_image[image] is None:
                ram_by_image[image] = ram

        with self._connect() as conn:
            try:
                rows = conn.execute(
                    "SELECT image, ram FROM templates WHERE image IS NOT NULL"
                ).fetchall()
                for r in rows:
                    _add(r["image"], r["ram"])
            except sqlite3.Error:
                pass

            # UNION in the built-in scenario images.
            try:
                from api.templates import TEMPLATES
                for tmpl in TEMPLATES.values():
                    for node in tmpl.get("nodes", []):
                        _add(node.get("image"))
            except Exception:
                pass

            running = conn.execute(
                "SELECT COUNT(*) AS n FROM nodes WHERE status = 'running'"
            ).fetchone()["n"]
            max_nodes = self._max_nodes(conn)

        images = []
        for image in ordered:
            kind = _derive_kind(image)
            images.append({
                "image": image,
                "kind": kind,
                "types": ["docker"],
                "default_ifaces": list(_DEFAULT_IFACES[kind]),
                "ram_mb": ram_by_image.get(image),
            })

        free_ram_mb: int | None = None
        try:
            import psutil
            free_ram_mb = psutil.virtual_memory().available // (1024 * 1024)
        except Exception:
            free_ram_mb = None

        return {
            "images": images,
            "host": {
                "free_ram_mb": free_ram_mb,
                "max_nodes": max_nodes,
                "running_nodes": running,
            },
        }

    # -- labs ----------------------------------------------------------------
    def insert_lab(self, name: str, description: str) -> str:
        lab_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO labs (id, name, description) VALUES (?, ?, ?)",
                (lab_id, name, description),
            )
            conn.commit()
        return lab_id

    def get_lab(self, lab_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM labs WHERE id = ?", (lab_id,)
            ).fetchone()
            return dict(row) if row else None

    # -- nodes ---------------------------------------------------------------
    def insert_node(self, lab_id: str, name: str, image: str,
                    type_: str, options: dict) -> dict:
        node_id = str(uuid.uuid4())
        options = options or {}
        x = options.get("x", 100)
        y = options.get("y", 100)
        console_type = options.get("console_type", "pty")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO nodes (id, lab_id, name, type, image, config, x, y, console_type)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (node_id, lab_id, name, type_, image, "{}", x, y, console_type),
            )
            conn.commit()
        return {"node_id": node_id, "ifaces": _default_ifaces_for(image)}

    def get_node(self, node_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()
            if not row:
                return None
            node = dict(row)
        return {
            "node_id": node["id"],
            "name": node["name"],
            "state": _map_state(node.get("status")),
            "started_at": node.get("started_at"),
            "ifaces": self._node_ifaces(node["id"], node.get("image")),
            "last_error": node.get("last_error"),
        }

    # -- ifaces / links ------------------------------------------------------
    def _node_used_ifaces(self, conn: sqlite3.Connection, node_id: str) -> set[str]:
        used: set[str] = set()
        rows = conn.execute(
            "SELECT src_node_id, dst_node_id, src_interface, dst_interface FROM links"
            " WHERE src_node_id = ? OR dst_node_id = ?",
            (node_id, node_id),
        ).fetchall()
        for r in rows:
            if r["src_node_id"] == node_id and r["src_interface"]:
                used.add(r["src_interface"])
            if r["dst_node_id"] == node_id and r["dst_interface"]:
                used.add(r["dst_interface"])
        return used

    def _node_image(self, conn: sqlite3.Connection, node_id: str) -> str | None:
        row = conn.execute(
            "SELECT image FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        return row["image"] if row else None

    def _node_ifaces(self, node_id: str, image: str | None) -> list[str]:
        """Union of the node's linked interfaces, backfilled by image defaults."""
        with self._connect() as conn:
            used = self._node_used_ifaces(conn, node_id)
        defaults = _default_ifaces_for(image or "")
        ifaces = list(defaults)
        for i in sorted(used):
            if i not in ifaces:
                ifaces.append(i)
        return ifaces

    def free_iface(self, node_id: str) -> str | None:
        with self._connect() as conn:
            used = self._node_used_ifaces(conn, node_id)
            image = self._node_image(conn, node_id)
        for iface in _default_ifaces_for(image or ""):
            if iface not in used:
                return iface
        return None

    def iface_in_use(self, node_id: str, iface: str) -> bool:
        with self._connect() as conn:
            return iface in self._node_used_ifaces(conn, node_id)

    def link_exists(self, a_node: str, a_if: str, b_node: str, b_if: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM links WHERE"
                " (src_node_id = ? AND src_interface = ? AND dst_node_id = ? AND dst_interface = ?)"
                " OR (src_node_id = ? AND src_interface = ? AND dst_node_id = ? AND dst_interface = ?)"
                " LIMIT 1",
                (a_node, a_if, b_node, b_if, b_node, b_if, a_node, a_if),
            ).fetchone()
            return row is not None

    def insert_link(self, lab_id: str, a: dict, b: dict, options: dict) -> str:
        link_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO links (id, lab_id, src_node_id, dst_node_id, src_interface, dst_interface)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (link_id, lab_id, a["node_id"], b["node_id"], a["iface"], b["iface"]),
            )
            conn.commit()
        return link_id

    # -- lab state -----------------------------------------------------------
    def lab_state(self, lab_id: str) -> dict:
        with self._connect() as conn:
            lab = conn.execute(
                "SELECT * FROM labs WHERE id = ?", (lab_id,)
            ).fetchone()
            lab = dict(lab) if lab else {}
            node_rows = [dict(r) for r in conn.execute(
                "SELECT * FROM nodes WHERE lab_id = ?", (lab_id,)
            ).fetchall()]
            link_rows = [dict(r) for r in conn.execute(
                "SELECT * FROM links WHERE lab_id = ?", (lab_id,)
            ).fetchall()]

        # Derive each node's ifaces from the links it participates in,
        # backfilled by the image default-iface list.
        used_by_node: dict[str, set[str]] = {}
        for link in link_rows:
            s, d = link.get("src_node_id"), link.get("dst_node_id")
            if link.get("src_interface"):
                used_by_node.setdefault(s, set()).add(link["src_interface"])
            if link.get("dst_interface"):
                used_by_node.setdefault(d, set()).add(link["dst_interface"])

        nodes = []
        for n in node_rows:
            defaults = _default_ifaces_for(n.get("image") or "")
            ifaces = list(defaults)
            for i in sorted(used_by_node.get(n["id"], set())):
                if i not in ifaces:
                    ifaces.append(i)
            nodes.append({
                "node_id": n["id"],
                "name": n["name"],
                "image": n.get("image"),
                "state": _map_state(n.get("status")),
                "ifaces": ifaces,
            })

        links = []
        for link in link_rows:
            links.append({
                "link_id": link["id"],
                "a": {"node_id": link.get("src_node_id"), "iface": link.get("src_interface")},
                "b": {"node_id": link.get("dst_node_id"), "iface": link.get("dst_interface")},
            })

        return {
            "lab": {
                "lab_id": lab_id,
                "name": lab.get("name"),
                "node_count": len(node_rows),
                "link_count": len(link_rows),
            },
            "nodes": nodes,
            "links": links,
            "node_count": len(node_rows),
            "link_count": len(link_rows),
        }

    # -- lifecycle (CRE-43) --------------------------------------------------
    def node_row(self, node_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()
            if not row:
                return None
            n = dict(row)
        import json as _json
        try:
            cfg = _json.loads(n.get("config") or "{}") or {}
        except (TypeError, ValueError):
            cfg = {}
        return {
            "node_id": n["id"],
            "name": n.get("name"),
            "lab_id": n.get("lab_id"),
            "type": n.get("type"),
            "image": n.get("image"),
            "status": n.get("status"),
            "config": cfg,
            "ports": cfg.get("ports"),
            "docker_options": cfg.get("docker_options") or {},
        }

    def set_node_status(self, node_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE nodes SET status = ? WHERE id = ?", (status, node_id)
            )
            conn.commit()

    def set_node_config(self, node_id: str, config: dict) -> None:
        import json as _json
        with self._connect() as conn:
            conn.execute(
                "UPDATE nodes SET config = ? WHERE id = ?",
                (_json.dumps(config or {}), node_id),
            )
            conn.commit()

    def lab_node_ids(self, lab_id: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM nodes WHERE lab_id = ?", (lab_id,)
            ).fetchall()
        return [r["id"] for r in rows]

    def running_docker_nodes_in_lab(self, lab_id: str, exclude_node_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM nodes "
                "WHERE lab_id = ? AND lower(type) = 'docker' "
                "AND status = 'running' AND id != ?",
                (lab_id, exclude_node_id),
            ).fetchone()
        return row["n"] if row else 0

    def delete_lab_rows(self, lab_id: str) -> dict:
        with self._connect() as conn:
            n_links = conn.execute(
                "SELECT COUNT(*) AS n FROM links WHERE lab_id = ?", (lab_id,)
            ).fetchone()["n"]
            n_nodes = conn.execute(
                "SELECT COUNT(*) AS n FROM nodes WHERE lab_id = ?", (lab_id,)
            ).fetchone()["n"]
            # Explicit deletes (FK cascade may also cover links/nodes, but be safe).
            conn.execute("DELETE FROM links WHERE lab_id = ?", (lab_id,))
            conn.execute("DELETE FROM nodes WHERE lab_id = ?", (lab_id,))
            conn.execute("DELETE FROM labs WHERE id = ?", (lab_id,))
            conn.commit()
        return {"nodes_removed": n_nodes, "links_removed": n_links}


# Map the DB nodes.status text onto the contract state enum.
_STATE_MAP = {
    "created": "created",
    "starting": "starting",
    "running": "running",
    "stopping": "stopping",
    "stopped": "stopped",
    "error": "error",
}


def _map_state(status: str | None) -> str:
    if not status:
        return "created"
    return _STATE_MAP.get(status.lower(), "error")


def get_repo() -> tools.Repo:
    """Construct the production Repo (sqlite-backed). Tests override this via
    ``app.dependency_overrides[get_repo]``."""
    return SqliteRepo()


class ToolRequest(BaseModel):
    """Generic body: {"args": { ...tool-specific kwargs... }}."""
    args: dict[str, Any] = {}


# The contract uses "type" in create_node args; the tool param is type_ (type is
# a builtin). Remap at the boundary so the public contract stays "type".
def _normalize_args(name: str, args: dict) -> dict:
    if name == "create_node" and "type" in args:
        args = dict(args)
        args["type_"] = args.pop("type")
    return args


@router.post("/tools/{name}")
def call_tool(name: str, body: ToolRequest, repo: tools.Repo = Depends(get_repo)) -> dict:
    """Dispatch a single tool by name. Returns the standard envelope.

    Unknown tool -> VALIDATION error envelope (404-style, but kept in-envelope so the
    agent in CRE-44 sees a uniform shape). Tool-raised AILBError -> error envelope.
    """
    fn = tools.TOOLS.get(name)
    if fn is None:
        return err("VALIDATION", f"unknown tool {name!r}",
                   {"available": sorted(tools.TOOLS)})

    args = _normalize_args(name, body.args)
    try:
        return fn(repo, **args)
    except AILBError as e:
        return err(e.code, e.message, e.details)
    except TypeError as e:
        # bad/missing kwargs for the tool — treat as a validation error, not a 500
        return err("VALIDATION", f"bad arguments for {name}: {e}")


@router.get("/tools")
def list_tools() -> dict:
    """Discovery endpoint — names the agent loop (CRE-44) can introspect."""
    return tools.ok({"tools": sorted(tools.TOOLS)})


# ============================================================================
# CRE-44 — the LLM tool-calling loop, streamed to the client as SSE.
# ============================================================================

class BuildRequest(BaseModel):
    prompt: str
    model: str | None = None
    max_iterations: int | None = None


@router.post("/build")
def build_lab(body: BuildRequest, repo: tools.Repo = Depends(get_repo)) -> StreamingResponse:
    """Run the lab-builder agent for ``prompt`` and stream its events as SSE.

    Each event from ``agent_runner.run_build`` is serialized as one SSE frame
    (``data: {json}\\n\\n``). The runner enforces the CRE-40 cost rails and
    redacts the API key from any error it surfaces."""
    kwargs: dict[str, Any] = {}
    if body.model:
        kwargs["model"] = body.model
    if body.max_iterations is not None:
        kwargs["max_iterations"] = body.max_iterations

    def _event_stream():
        try:
            for event in agent_runner.run_build(repo, body.prompt, **kwargs):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001 — never leak; never 500 mid-stream
            safe = agent_runner._redact(str(exc), agent_runner._load_api_key())
            yield f"data: {json.dumps({'type': 'error', 'message': safe})}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")
