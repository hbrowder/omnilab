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

import asyncio
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

    # -- lifecycle (CRE-43) --------------------------------------------------
    def node_row(self, node_id: str) -> dict | None:
        """Raw lifecycle fields for one node: {node_id, name, lab_id, type,
        image, status, config (parsed dict), ports?, docker_options?}. None if
        the node doesn't exist."""
        raise NotImplementedError

    def set_node_status(self, node_id: str, status: str) -> None:
        raise NotImplementedError

    def set_node_config(self, node_id: str, config: dict) -> None:
        """Persist the node's startup config JSON (nodes.config)."""
        raise NotImplementedError

    def lab_node_ids(self, lab_id: str) -> list[str]:
        raise NotImplementedError

    def running_docker_nodes_in_lab(self, lab_id: str, exclude_node_id: str) -> int:
        """Count docker nodes in the lab with status='running', excluding one."""
        raise NotImplementedError

    def delete_lab_rows(self, lab_id: str) -> dict:
        """Delete links, nodes, and the lab row. Returns
        {nodes_removed, links_removed}."""
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
# Lifecycle / mutation tools  (contract §4, CRE-43)
#
# These are the only tools with docker side effects. The single source of truth
# for docker behavior is DockerProvisioner; the start/stop *sequence* (the order
# of provisioner calls) lives in api/nodes.py (docker_start_sequence /
# docker_stop_sequence) and is shared with the async HTTP endpoints.
#
# Sync/async bridge: these tools are synchronous but the provisioner is async.
# We drive the coroutines from sync code via a private event loop
# (`_run(coro)`). This is safe because the sync /tools endpoint runs in a
# threadpool worker (no running loop) and CRE-44 calls tools via a thread too.
# We reuse the lazy provisioner singleton from api/nodes (_get_provisioner /
# _reset_provisioner_for_tests) so there is exactly one docker client and the
# test reset hook injects a mock for both the endpoints and the tools.
# ============================================================================


def _run(coro):
    """Run an async coroutine to completion from synchronous tool code.

    A fresh event loop per call keeps us independent of any ambient loop and
    avoids cross-test loop reuse problems. Safe only when there is no running
    loop on this thread (the case for the threadpool-backed /tools endpoint
    and the CRE-44 thread)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _provisioner():
    """The shared lazy DockerProvisioner singleton from api/nodes. Imported
    lazily so importing this module never requires a docker daemon."""
    from api.nodes import _get_provisioner
    return _get_provisioner()


def _docker_seq():
    """The shared start/stop sequence helpers (single source of truth)."""
    from api import nodes as nodes_mod
    return nodes_mod


def _node_or_404(repo: Repo, node_id: str) -> dict:
    node = repo.node_row(node_id)
    if node is None:
        raise AILBError("NOT_FOUND", f"node {node_id} does not exist")
    return node


def start_node(repo: Repo, node_id: str) -> dict:
    """Boot a node (decision D1: SYNC, agent polls).

    docker: ensure_image -> create_lab_network -> start_node (shared sequence),
    then flip the row to running. Idempotent — a running node is a no-op.
    Non-docker (qemu/pty): mirror the endpoint minimally — flip to running."""
    node = _node_or_404(repo, node_id)

    # Idempotent: already running -> no side effect.
    if (node.get("status") or "").lower() == "running":
        return ok({"node_id": node_id, "state": "running"})

    node_type = (node.get("type") or "").lower()

    if node_type != "docker":
        # qemu/pty path: the endpoint just flips status to running (QEMU/VNC
        # spawning is an HTTP-only concern). Mirror that minimally.
        repo.set_node_status(node_id, "running")
        return ok({"node_id": node_id, "state": "running"})

    image = node.get("image") or ""
    if not image:
        raise AILBError("VALIDATION", f"docker node {node_id} has no image configured")

    nodes_mod = _docker_seq()
    from services.docker_provisioner import (
        DiskFullError,
        DockerProvisionerError,
    )

    try:
        p = _provisioner()
    except DockerProvisionerError as exc:
        raise AILBError("TIMEOUT", f"docker daemon unreachable: {exc}") from exc

    try:
        _run(nodes_mod.docker_start_sequence(
            p,
            node_id=node_id,
            lab_id=node["lab_id"],
            image=image,
            name=node.get("name") or node_id,
            ports=node.get("ports"),
            docker_options=node.get("docker_options") or {},
        ))
    except DiskFullError as exc:
        raise AILBError("CAPACITY_EXCEEDED", str(exc)) from exc
    except DockerProvisionerError as exc:
        raise AILBError("TIMEOUT", f"node {node_id} failed to start: {exc}") from exc

    repo.set_node_status(node_id, "running")
    return ok({"node_id": node_id, "state": "running"})


def stop_node(repo: Repo, node_id: str) -> dict:
    """Stop a node. docker: stop_node + tear down the lab network if no other
    docker node in the lab is still running (shared sequence). Idempotent."""
    node = _node_or_404(repo, node_id)
    node_type = (node.get("type") or "").lower()

    if node_type != "docker":
        repo.set_node_status(node_id, "stopped")
        return ok({"node_id": node_id, "state": "stopped"})

    nodes_mod = _docker_seq()
    from services.docker_provisioner import DockerProvisionerError

    try:
        p = _provisioner()
    except DockerProvisionerError:
        # Docker gone — still flip the row so we don't show a phantom-running
        # node. Mirror the endpoint's resilience.
        repo.set_node_status(node_id, "stopped")
        return ok({"node_id": node_id, "state": "stopped"})

    # Mark stopped first so the "others running" count below excludes this node
    # consistently (the helper takes the count of OTHER running docker nodes).
    repo.set_node_status(node_id, "stopped")
    others = repo.running_docker_nodes_in_lab(node["lab_id"], exclude_node_id=node_id)
    _run(nodes_mod.docker_stop_sequence(
        p, node_id=node_id, lab_id=node["lab_id"], others_running=others,
    ))
    return ok({"node_id": node_id, "state": "stopped"})


def delete_lab(repo: Repo, lab_id: str) -> dict:
    """Destructive cleanup: stop every node, destroy the lab network, then
    delete links/nodes/labs rows. Returns counts removed."""
    if repo.get_lab(lab_id) is None:
        raise AILBError("NOT_FOUND", f"lab {lab_id} does not exist")

    # Stop every node first so no orphaned containers remain (contract §4).
    for nid in repo.lab_node_ids(lab_id):
        try:
            stop_node(repo, nid)
        except AILBError:
            # Best-effort — a missing/already-stopped node must not block delete.
            pass

    # Destroy the lab network explicitly (best-effort). stop_node already tears
    # it down once the last docker node stops, but be explicit/safe in case the
    # lab had no docker nodes running or the teardown was skipped.
    from services.docker_provisioner import DockerProvisionerError
    try:
        p = _provisioner()
        _run(p.destroy_lab_network(lab_id))
    except DockerProvisionerError:
        pass

    counts = repo.delete_lab_rows(lab_id)
    return ok({
        "deleted": True,
        "nodes_removed": counts["nodes_removed"],
        "links_removed": counts["links_removed"],
    })


def push_config(repo: Repo, node_id: str, config_text: str,
                mode: str = "startup") -> dict:
    """Apply configuration to a node. No general shell (decision D2).

    mode 'startup': persist config to the node's config (applied at/with boot).
    mode 'live': apply to a RUNNING node via its native config channel (docker
    exec into the container — FRR vtysh when present, else write to a file).
    """
    if mode not in ("startup", "live"):
        raise AILBError("VALIDATION", f"mode must be 'startup' or 'live', got {mode!r}")
    if config_text is None:
        raise AILBError("VALIDATION", "config_text is required")

    node = _node_or_404(repo, node_id)
    node_type = (node.get("type") or "").lower()
    warnings: list[str] = []

    if mode == "startup":
        # Persist into nodes.config under a 'startup_config' key, preserving any
        # existing config dict (e.g. docker_options).
        cfg = dict(node.get("config") or {})
        cfg["startup_config"] = config_text
        repo.set_node_config(node_id, cfg)
        return ok({"applied": True, "mode": "startup", "warnings": warnings})

    # --- live mode -----------------------------------------------------------
    if (node.get("status") or "").lower() != "running":
        raise AILBError("NODE_NOT_RUNNING",
                        f"node {node_id} must be running for a live config push")

    if node_type == "qemu":
        # Serial-console push is best-effort; we have no implemented path.
        # Don't fake success.
        raise AILBError("VALIDATION",
                        "live config push for qemu nodes (serial console) is not "
                        "implemented; use mode='startup'")

    if node_type != "docker":
        raise AILBError("VALIDATION",
                        f"live config push is only supported for docker nodes, "
                        f"got type {node_type!r}")

    # docker live push via exec.
    from services.docker_provisioner import DockerProvisionerError
    try:
        p = _provisioner()
    except DockerProvisionerError as exc:
        raise AILBError("NODE_NOT_RUNNING", f"docker daemon unreachable: {exc}") from exc

    rejected = _docker_live_push(p, node_id, node.get("image") or "", config_text)
    if rejected:
        raise AILBError("CONFIG_REJECTED", "node rejected the pushed config",
                        {"lines": rejected})

    return ok({"applied": True, "mode": "live", "warnings": warnings})


def _docker_live_push(provisioner, node_id: str, image: str,
                      config_text: str) -> list[str]:
    """Apply config_text to a running container via docker exec.

    FRR images: pipe each line through vtysh and collect any line vtysh
    rejects (non-zero exit / '% ' error marker). Other images: write the
    config to /etc/omnilab/startup.conf inside the container. Returns a list of
    rejected lines (empty == accepted)."""
    container_name = f"omnilab-{node_id}"

    def _apply() -> list[str]:
        container = provisioner.client.containers.get(container_name)
        is_frr = "frr" in (image or "").lower()
        rejected: list[str] = []
        if is_frr:
            for line in config_text.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                res = container.exec_run(["vtysh", "-c", stripped])
                exit_code = res[0] if isinstance(res, tuple) else res.exit_code
                output = res[1] if isinstance(res, tuple) else res.output
                text = (output or b"")
                if isinstance(text, bytes):
                    text = text.decode("utf-8", "replace")
                if exit_code != 0 or text.lstrip().startswith("%"):
                    rejected.append(stripped)
            return rejected
        # Generic: write the config to a file inside the container.
        import base64
        b64 = base64.b64encode(config_text.encode("utf-8")).decode("ascii")
        cmd = ["/bin/sh", "-c",
               "mkdir -p /etc/omnilab && "
               f"echo {b64} | base64 -d > /etc/omnilab/startup.conf"]
        res = container.exec_run(cmd)
        exit_code = res[0] if isinstance(res, tuple) else res.exit_code
        if exit_code != 0:
            # Treat a failed write as a full rejection.
            return config_text.splitlines() or ["<write failed>"]
        return []

    # The docker SDK calls here are synchronous; call directly (no loop needed).
    return _apply()


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
    # CRE-43 lifecycle / mutation tools:
    "start_node": start_node,
    "stop_node": stop_node,
    "delete_lab": delete_lab,
    "push_config": push_config,
}
