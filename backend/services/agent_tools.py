"""
backend/services/agent_tools.py  —  AI Lab Builder, Phase 2 (CRE-42)

Pure-Python tool functions the agent will call. NO LLM here. Every function
returns a JSON-serializable dict using the envelope from docs/ailb-tool-api.md.

Scope of CRE-42: read tools (list_inventory, get_lab_state, get_node_state) and
construction tools (create_lab, create_node, link_nodes).
Lifecycle tools (push_config, start_node, stop_node, delete_lab) are CRE-43.

The tools are SYNCHRONOUS and talk to the DB only through the `Repo` seam.
The production Repo (in api/agent.py) wraps a short-lived synchronous
``sqlite3`` connection; tests inject a fake Repo with the same shape. Keeping
DB access behind the Repo means these functions stay trivially unit-testable.
"""

from __future__ import annotations

from typing import Any

# ============================================================================
# Envelope + errors  (mirror docs/ailb-tool-api.md §1)
# ============================================================================

ERROR_CODES = {
    "NOT_FOUND", "INVALID_IMAGE", "INVALID_TYPE", "LINK_EXISTS", "IFACE_IN_USE",
    "NODE_NOT_RUNNING", "CAPACITY_EXCEEDED", "CONFIG_REJECTED", "TIMEOUT", "VALIDATION",
}


class AILBError(Exception):
    """Raised by tool internals; converted to an error envelope at the boundary."""
    def __init__(self, code: str, message: str, details: dict | None = None):
        assert code in ERROR_CODES, f"unknown error code {code!r}"
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")


def ok(data: Any) -> dict:
    return {"ok": True, "data": data, "error": None}


def err(code: str, message: str, details: dict | None = None) -> dict:
    return {"ok": False, "data": None,
            "error": {"code": code, "message": message, "details": details or {}}}


# ============================================================================
# Repo seam — lets tests inject a fake; prod impl wraps the real sqlite DB
# ============================================================================

class Repo:
    """Abstract adapter over the real backend. The concrete sqlite-backed impl
    lives in api/agent.py; tests subclass/duck-type this with an in-memory fake.

    Each method returns plain dicts/lists so the tool layer stays
    serialization-safe. Methods are NOT implemented here on purpose — this is a
    shape contract.
    """

    def inventory(self) -> dict:                                          # images + host capacity
        raise NotImplementedError

    def insert_lab(self, name: str, description: str) -> str:             # -> lab_id
        raise NotImplementedError

    def get_lab(self, lab_id: str) -> dict | None:
        raise NotImplementedError

    def insert_node(self, lab_id: str, name: str, image: str,
                    type_: str, options: dict) -> dict:                   # -> {node_id, ifaces}
        raise NotImplementedError

    def get_node(self, node_id: str) -> dict | None:
        raise NotImplementedError

    def free_iface(self, node_id: str) -> str | None:                  # next unlinked iface
        raise NotImplementedError

    def iface_in_use(self, node_id: str, iface: str) -> bool:
        raise NotImplementedError

    def link_exists(self, a_node: str, a_if: str, b_node: str, b_if: str) -> bool:
        raise NotImplementedError

    def insert_link(self, lab_id: str, a: dict, b: dict, options: dict) -> str:  # -> link_id
        raise NotImplementedError

    def lab_state(self, lab_id: str) -> dict:                            # full topology JSON
        raise NotImplementedError


# ============================================================================
# Read / introspection tools  (contract §2)
# ============================================================================

def list_inventory(repo: Repo) -> dict:
    """Available images/types + host capacity. Read-only."""
    return ok(repo.inventory())


def get_lab_state(repo: Repo, lab_id: str) -> dict:
    """Agent's single source of truth for the topology (decision D3)."""
    if repo.get_lab(lab_id) is None:
        raise AILBError("NOT_FOUND", f"lab {lab_id} does not exist")
    return ok(repo.lab_state(lab_id))


def get_node_state(repo: Repo, node_id: str) -> dict:
    """Fine-grained state for one node; primary polling tool after start_node."""
    node = repo.get_node(node_id)
    if node is None:
        raise AILBError("NOT_FOUND", f"node {node_id} does not exist")
    return ok({
        "node_id": node["node_id"], "name": node["name"], "state": node["state"],
        "started_at": node.get("started_at"), "ifaces": node.get("ifaces", []),
        "last_error": node.get("last_error"),
    })


# ============================================================================
# Construction tools  (contract §3)
# ============================================================================

def create_lab(repo: Repo, name: str, description: str = "") -> dict:
    if not name or not name.strip():
        raise AILBError("VALIDATION", "name is required")
    lab_id = repo.insert_lab(name.strip(), description)
    return ok({"lab_id": lab_id})


def create_node(repo: Repo, lab_id: str, name: str, image: str,
                type_: str | None = None, options: dict | None = None) -> dict:
    options = options or {}
    if not name or not name.strip():
        raise AILBError("VALIDATION", "name is required")
    if repo.get_lab(lab_id) is None:
        raise AILBError("NOT_FOUND", f"lab {lab_id} does not exist")

    inv = repo.inventory()
    match = next((i for i in inv["images"] if i["image"] == image), None)
    if match is None:
        raise AILBError("INVALID_IMAGE", f"{image} not in inventory",
                        {"available": [i["image"] for i in inv["images"]]})

    resolved_type = type_ or match["types"][0]
    if resolved_type not in match["types"]:
        raise AILBError("INVALID_TYPE", f"{image} does not support type {resolved_type}",
                        {"supported": match["types"]})

    host = inv["host"]
    if host["running_nodes"] >= host["max_nodes"]:
        raise AILBError("CAPACITY_EXCEEDED", "host node limit reached",
                        {"max_nodes": host["max_nodes"]})

    node = repo.insert_node(lab_id, name.strip(), image, resolved_type, options)  # does NOT start container
    return ok({"node_id": node["node_id"], "ifaces": node["ifaces"]})


def link_nodes(repo: Repo, lab_id: str, a: dict, b: dict,
               options: dict | None = None) -> dict:
    """a/b are {"node_id": "...", "iface"?: "..."}. Omitted iface -> next free."""
    options = options or {}
    if not isinstance(a, dict) or not isinstance(b, dict):
        raise AILBError("VALIDATION", "a and b must be {node_id, iface?} objects")
    if repo.get_lab(lab_id) is None:
        raise AILBError("NOT_FOUND", f"lab {lab_id} does not exist")

    endpoints = []
    for side in (a, b):
        node_id = side.get("node_id")
        if not node_id:
            raise AILBError("VALIDATION", "each endpoint requires a node_id")
        if repo.get_node(node_id) is None:
            raise AILBError("NOT_FOUND", f"node {node_id} does not exist")
        iface = side.get("iface") or repo.free_iface(node_id)
        if iface is None:
            raise AILBError("CAPACITY_EXCEEDED", f"node {node_id} has no free interface")
        if repo.iface_in_use(node_id, iface):
            raise AILBError("IFACE_IN_USE", f"{node_id}:{iface} already linked")
        endpoints.append({"node_id": node_id, "iface": iface})

    a_end, b_end = endpoints
    if repo.link_exists(a_end["node_id"], a_end["iface"], b_end["node_id"], b_end["iface"]):
        raise AILBError("LINK_EXISTS", "those interfaces are already linked")

    link_id = repo.insert_link(lab_id, a_end, b_end, options)  # also creates the L2 segment
    return ok({"link_id": link_id, "a_iface": a_end["iface"], "b_iface": b_end["iface"]})


# ============================================================================
# Dispatch table — used by the FastAPI wrappers in api/agent.py and by CRE-44
# ============================================================================

TOOLS = {
    "list_inventory": list_inventory,
    "get_lab_state": get_lab_state,
    "get_node_state": get_node_state,
    "create_lab": create_lab,
    "create_node": create_node,
    "link_nodes": link_nodes,
    # CRE-43 will register: push_config, start_node, stop_node, delete_lab
}
