"""
Tests for the AI Lab Builder tool layer (CRE-42).

Three layers:
  1. Unit tests for every tool against an in-memory FakeRepo — success AND
     failure path (NOT_FOUND, INVALID_IMAGE, INVALID_TYPE, IFACE_IN_USE,
     LINK_EXISTS, VALIDATION, CAPACITY_EXCEEDED).
  2. HTTP-level tests via the `client` fixture, injecting the fake through
     app.dependency_overrides[get_repo] — asserts the envelope shape and the
     unknown-tool VALIDATION envelope.
  3. An @pytest.mark.integration test that builds a real 2-node DVWA lab
     through the tools using the real sqlite-backed Repo.
"""
from __future__ import annotations

import uuid

import pytest

from services import agent_tools as tools
from services.agent_tools import AILBError


# ============================================================================
# Fake in-memory Repo
# ============================================================================

class FakeRepo(tools.Repo):
    """In-memory Repo for unit/HTTP tests. Mirrors SqliteRepo's return shapes."""

    DEFAULT_IFACES = {
        "router": ["eth0", "eth1", "eth2", "eth3"],
        "host": ["eth0", "eth1"],
    }

    def __init__(self, *, max_nodes: int = 64, running_nodes: int = 0):
        self.labs: dict[str, dict] = {}
        self.nodes: dict[str, dict] = {}   # node_id -> {node_id,name,image,kind,state,lab_id}
        self.links: list[dict] = []        # {link_id, a:{node_id,iface}, b:{node_id,iface}, lab_id}
        self._max_nodes = max_nodes
        self._running_nodes = running_nodes

    # -- helpers
    @staticmethod
    def _kind(image: str) -> str:
        name = (image or "").lower()
        if any(k in name for k in ("frr", "router")):
            return "router"
        return "host"

    def _defaults(self, image: str) -> list[str]:
        return list(self.DEFAULT_IFACES[self._kind(image)])

    def _used(self, node_id: str) -> set[str]:
        used: set[str] = set()
        for ln in self.links:
            if ln["a"]["node_id"] == node_id:
                used.add(ln["a"]["iface"])
            if ln["b"]["node_id"] == node_id:
                used.add(ln["b"]["iface"])
        return used

    # -- Repo interface
    def inventory(self) -> dict:
        return {
            "images": [
                {"image": "frrouting/frr:latest", "kind": "router", "types": ["docker"],
                 "default_ifaces": ["eth0", "eth1", "eth2", "eth3"], "ram_mb": 256},
                {"image": "vulnerables/web-dvwa", "kind": "host", "types": ["docker"],
                 "default_ifaces": ["eth0", "eth1"], "ram_mb": 512},
            ],
            "host": {"free_ram_mb": 12000, "max_nodes": self._max_nodes,
                     "running_nodes": self._running_nodes},
        }

    def insert_lab(self, name: str, description: str) -> str:
        lab_id = str(uuid.uuid4())
        self.labs[lab_id] = {"id": lab_id, "name": name, "description": description}
        return lab_id

    def get_lab(self, lab_id: str):
        return self.labs.get(lab_id)

    def insert_node(self, lab_id: str, name: str, image: str, type_: str, options: dict) -> dict:
        node_id = str(uuid.uuid4())
        self.nodes[node_id] = {
            "node_id": node_id, "name": name, "image": image, "type": type_,
            "state": "stopped", "lab_id": lab_id,
        }
        return {"node_id": node_id, "ifaces": self._defaults(image)}

    def get_node(self, node_id: str):
        n = self.nodes.get(node_id)
        if not n:
            return None
        return {**n, "ifaces": self._defaults(n["image"]), "started_at": None, "last_error": None}

    def free_iface(self, node_id: str):
        n = self.nodes[node_id]
        used = self._used(node_id)
        for i in self._defaults(n["image"]):
            if i not in used:
                return i
        return None

    def iface_in_use(self, node_id: str, iface: str) -> bool:
        return iface in self._used(node_id)

    def link_exists(self, a_node, a_if, b_node, b_if) -> bool:
        for ln in self.links:
            pair = {(ln["a"]["node_id"], ln["a"]["iface"]), (ln["b"]["node_id"], ln["b"]["iface"])}
            if pair == {(a_node, a_if), (b_node, b_if)}:
                return True
        return False

    def insert_link(self, lab_id: str, a: dict, b: dict, options: dict) -> str:
        link_id = str(uuid.uuid4())
        self.links.append({"link_id": link_id, "a": dict(a), "b": dict(b), "lab_id": lab_id})
        return link_id

    def lab_state(self, lab_id: str) -> dict:
        nodes = [n for n in self.nodes.values() if n["lab_id"] == lab_id]
        links = [ln for ln in self.links if ln["lab_id"] == lab_id]
        return {
            "lab": {"lab_id": lab_id, "name": self.labs[lab_id]["name"],
                    "node_count": len(nodes), "link_count": len(links)},
            "nodes": [{"node_id": n["node_id"], "name": n["name"], "image": n["image"],
                       "state": n["state"], "ifaces": self._defaults(n["image"])} for n in nodes],
            "links": [{"link_id": ln["link_id"], "a": ln["a"], "b": ln["b"]} for ln in links],
            "node_count": len(nodes), "link_count": len(links),
        }

    # -- lifecycle (CRE-43). In this fake, node "state" doubles as "status".
    def node_row(self, node_id: str):
        n = self.nodes.get(node_id)
        if not n:
            return None
        return {
            "node_id": n["node_id"], "name": n["name"], "lab_id": n["lab_id"],
            "type": n.get("type", "docker"), "image": n["image"],
            "status": n["state"], "config": dict(n.get("config", {})),
            "ports": n.get("config", {}).get("ports"),
            "docker_options": n.get("config", {}).get("docker_options") or {},
        }

    def set_node_status(self, node_id: str, status: str) -> None:
        self.nodes[node_id]["state"] = status

    def set_node_config(self, node_id: str, config: dict) -> None:
        self.nodes[node_id]["config"] = dict(config)

    def lab_node_ids(self, lab_id: str):
        return [nid for nid, n in self.nodes.items() if n["lab_id"] == lab_id]

    def running_docker_nodes_in_lab(self, lab_id: str, exclude_node_id: str) -> int:
        return sum(
            1 for nid, n in self.nodes.items()
            if n["lab_id"] == lab_id and nid != exclude_node_id
            and n.get("type", "docker") == "docker" and n["state"] == "running"
        )

    def delete_lab_rows(self, lab_id: str) -> dict:
        node_ids = [nid for nid, n in self.nodes.items() if n["lab_id"] == lab_id]
        link_ids = [ln for ln in self.links if ln["lab_id"] == lab_id]
        for nid in node_ids:
            del self.nodes[nid]
        self.links = [ln for ln in self.links if ln["lab_id"] != lab_id]
        self.labs.pop(lab_id, None)
        return {"nodes_removed": len(node_ids), "links_removed": len(link_ids)}


@pytest.fixture()
def repo():
    return FakeRepo()


def _seed_lab_with_two_routers(repo: FakeRepo):
    lab_id = tools.create_lab(repo, "L")["data"]["lab_id"]
    n1 = tools.create_node(repo, lab_id, "r1", "frrouting/frr:latest")["data"]["node_id"]
    n2 = tools.create_node(repo, lab_id, "r2", "frrouting/frr:latest")["data"]["node_id"]
    return lab_id, n1, n2


# ============================================================================
# Unit tests — read tools
# ============================================================================

def test_list_inventory_ok(repo):
    res = tools.list_inventory(repo)
    assert res["ok"] is True
    assert {"images", "host"} <= res["data"].keys()
    assert any(i["image"] == "frrouting/frr:latest" for i in res["data"]["images"])


def test_get_lab_state_ok(repo):
    lab_id, n1, n2 = _seed_lab_with_two_routers(repo)
    tools.link_nodes(repo, lab_id, {"node_id": n1}, {"node_id": n2})
    res = tools.get_lab_state(repo, lab_id)
    assert res["ok"] is True
    assert res["data"]["lab"]["node_count"] == 2
    assert res["data"]["lab"]["link_count"] == 1
    assert len(res["data"]["nodes"]) == 2
    assert len(res["data"]["links"]) == 1


def test_get_lab_state_not_found(repo):
    with pytest.raises(AILBError) as ei:
        tools.get_lab_state(repo, "nope")
    assert ei.value.code == "NOT_FOUND"


def test_get_node_state_ok(repo):
    lab_id, n1, _ = _seed_lab_with_two_routers(repo)
    res = tools.get_node_state(repo, n1)
    assert res["ok"] is True
    assert res["data"]["node_id"] == n1
    assert res["data"]["state"] == "stopped"
    assert res["data"]["ifaces"] == ["eth0", "eth1", "eth2", "eth3"]
    assert res["data"]["last_error"] is None


def test_get_node_state_not_found(repo):
    with pytest.raises(AILBError) as ei:
        tools.get_node_state(repo, "nope")
    assert ei.value.code == "NOT_FOUND"


# ============================================================================
# Unit tests — create_lab
# ============================================================================

def test_create_lab_ok(repo):
    res = tools.create_lab(repo, "My Lab")
    assert res["ok"] is True
    assert res["data"]["lab_id"] in repo.labs


def test_create_lab_validation(repo):
    with pytest.raises(AILBError) as ei:
        tools.create_lab(repo, "   ")
    assert ei.value.code == "VALIDATION"


# ============================================================================
# Unit tests — create_node
# ============================================================================

def test_create_node_ok(repo):
    lab_id = tools.create_lab(repo, "L")["data"]["lab_id"]
    res = tools.create_node(repo, lab_id, "r1", "frrouting/frr:latest")
    assert res["ok"] is True
    assert res["data"]["ifaces"] == ["eth0", "eth1", "eth2", "eth3"]


def test_create_node_lab_not_found(repo):
    with pytest.raises(AILBError) as ei:
        tools.create_node(repo, "nope", "r1", "frrouting/frr:latest")
    assert ei.value.code == "NOT_FOUND"


def test_create_node_invalid_image(repo):
    lab_id = tools.create_lab(repo, "L")["data"]["lab_id"]
    with pytest.raises(AILBError) as ei:
        tools.create_node(repo, lab_id, "x", "no/such-image")
    assert ei.value.code == "INVALID_IMAGE"
    assert "available" in ei.value.details


def test_create_node_invalid_type(repo):
    lab_id = tools.create_lab(repo, "L")["data"]["lab_id"]
    with pytest.raises(AILBError) as ei:
        tools.create_node(repo, lab_id, "x", "frrouting/frr:latest", type_="qemu")
    assert ei.value.code == "INVALID_TYPE"


def test_create_node_validation_blank_name(repo):
    lab_id = tools.create_lab(repo, "L")["data"]["lab_id"]
    with pytest.raises(AILBError) as ei:
        tools.create_node(repo, lab_id, "  ", "frrouting/frr:latest")
    assert ei.value.code == "VALIDATION"


def test_create_node_capacity_exceeded():
    repo = FakeRepo(max_nodes=2, running_nodes=2)
    lab_id = tools.create_lab(repo, "L")["data"]["lab_id"]
    with pytest.raises(AILBError) as ei:
        tools.create_node(repo, lab_id, "r1", "frrouting/frr:latest")
    assert ei.value.code == "CAPACITY_EXCEEDED"


# ============================================================================
# Unit tests — link_nodes
# ============================================================================

def test_link_nodes_ok_auto_iface(repo):
    lab_id, n1, n2 = _seed_lab_with_two_routers(repo)
    res = tools.link_nodes(repo, lab_id, {"node_id": n1}, {"node_id": n2})
    assert res["ok"] is True
    assert res["data"]["a_iface"] == "eth0"
    assert res["data"]["b_iface"] == "eth0"


def test_link_nodes_lab_not_found(repo):
    with pytest.raises(AILBError) as ei:
        tools.link_nodes(repo, "nope", {"node_id": "a"}, {"node_id": "b"})
    assert ei.value.code == "NOT_FOUND"


def test_link_nodes_node_not_found(repo):
    lab_id, n1, _ = _seed_lab_with_two_routers(repo)
    with pytest.raises(AILBError) as ei:
        tools.link_nodes(repo, lab_id, {"node_id": n1}, {"node_id": "ghost"})
    assert ei.value.code == "NOT_FOUND"


def test_link_nodes_iface_in_use(repo):
    lab_id, n1, n2 = _seed_lab_with_two_routers(repo)
    tools.link_nodes(repo, lab_id, {"node_id": n1, "iface": "eth0"}, {"node_id": n2, "iface": "eth0"})
    with pytest.raises(AILBError) as ei:
        tools.link_nodes(repo, lab_id, {"node_id": n1, "iface": "eth0"}, {"node_id": n2, "iface": "eth1"})
    assert ei.value.code == "IFACE_IN_USE"


def test_link_nodes_link_exists(repo):
    lab_id, n1, n2 = _seed_lab_with_two_routers(repo)
    tools.link_nodes(repo, lab_id, {"node_id": n1, "iface": "eth0"}, {"node_id": n2, "iface": "eth0"})
    # Same pair again -> LINK_EXISTS (both interfaces already in use would trip
    # IFACE_IN_USE first; use a fresh pair of interfaces that we force-mark as a
    # duplicate by re-linking the exact same endpoints via a repo with the
    # iface check stubbed out).

    class NoIfaceCheck(FakeRepo):
        def iface_in_use(self, node_id, iface):
            return False

    repo2 = NoIfaceCheck()
    lab2 = tools.create_lab(repo2, "L")["data"]["lab_id"]
    a = tools.create_node(repo2, lab2, "r1", "frrouting/frr:latest")["data"]["node_id"]
    b = tools.create_node(repo2, lab2, "r2", "frrouting/frr:latest")["data"]["node_id"]
    tools.link_nodes(repo2, lab2, {"node_id": a, "iface": "eth0"}, {"node_id": b, "iface": "eth0"})
    with pytest.raises(AILBError) as ei:
        tools.link_nodes(repo2, lab2, {"node_id": a, "iface": "eth0"}, {"node_id": b, "iface": "eth0"})
    assert ei.value.code == "LINK_EXISTS"


def test_link_nodes_validation_missing_node_id(repo):
    lab_id, n1, _ = _seed_lab_with_two_routers(repo)
    with pytest.raises(AILBError) as ei:
        tools.link_nodes(repo, lab_id, {"node_id": n1}, {})
    assert ei.value.code == "VALIDATION"


# ============================================================================
# HTTP-level tests via the client fixture + dependency override
# ============================================================================

@pytest.fixture()
def http_repo(client):
    """Inject a shared FakeRepo into the app for the duration of the test."""
    from main import app
    from api.agent import get_repo

    fake = FakeRepo()
    app.dependency_overrides[get_repo] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_repo, None)


def test_http_list_tools(client):
    r = client.get("/api/agent/tools")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "create_lab" in body["data"]["tools"]
    assert "link_nodes" in body["data"]["tools"]


def test_http_unknown_tool_validation(client):
    r = client.post("/api/agent/tools/does_not_exist", json={"args": {}})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "VALIDATION"


def test_http_create_lab_and_node(client, http_repo):
    r = client.post("/api/agent/tools/create_lab", json={"args": {"name": "HTTP Lab"}})
    body = r.json()
    assert body["ok"] is True
    lab_id = body["data"]["lab_id"]

    # create_node using the contract "type" key (boundary remaps -> type_)
    r = client.post("/api/agent/tools/create_node", json={
        "args": {"lab_id": lab_id, "name": "r1", "image": "frrouting/frr:latest", "type": "docker"}})
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["ifaces"] == ["eth0", "eth1", "eth2", "eth3"]


def test_http_error_envelope(client, http_repo):
    r = client.post("/api/agent/tools/get_lab_state", json={"args": {"lab_id": "nope"}})
    body = r.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["data"] is None


def test_http_bad_arguments_validation(client, http_repo):
    # create_lab requires `name`; omit it -> TypeError -> VALIDATION envelope
    r = client.post("/api/agent/tools/create_lab", json={"args": {}})
    body = r.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "VALIDATION"


# ============================================================================
# Integration test — real sqlite-backed Repo (deselected by default)
# ============================================================================

@pytest.mark.integration
def test_integration_build_two_node_dvwa_lab():
    """Build a real 2-node DVWA lab through the tools against the real DB."""
    from api.agent import SqliteRepo

    repo = SqliteRepo()

    lab_id = tools.create_lab(repo, "DVWA Integration", "two dvwa nodes")["data"]["lab_id"]

    n1 = tools.create_node(repo, lab_id, "dvwa-1", "vulnerables/web-dvwa")["data"]["node_id"]
    n2 = tools.create_node(repo, lab_id, "dvwa-2", "vulnerables/web-dvwa")["data"]["node_id"]

    link = tools.link_nodes(repo, lab_id, {"node_id": n1}, {"node_id": n2})["data"]
    assert link["a_iface"] == "eth0"
    assert link["b_iface"] == "eth0"

    state = tools.get_lab_state(repo, lab_id)["data"]
    assert state["lab"]["node_count"] == 2
    assert state["lab"]["link_count"] == 1
    assert len(state["nodes"]) == 2
    assert len(state["links"]) == 1
    found = {n["node_id"] for n in state["nodes"]}
    assert {n1, n2} == found
    # The single link wires eth0<->eth0 between the two nodes.
    ln = state["links"][0]
    assert {ln["a"]["node_id"], ln["b"]["node_id"]} == {n1, n2}
    assert ln["a"]["iface"] == "eth0" and ln["b"]["iface"] == "eth0"


@pytest.mark.integration
def test_integration_full_lifecycle_two_node_lab():
    """CRE-43 acceptance: build + START a real 2-node lab end-to-end through the
    tools (Python only — no HTTP, no LLM), confirm both running, stop both,
    then delete the lab and assert containers + network are gone and the rows
    were removed.

    Image choice: BOTH nodes use vulnerables/web-dvwa (the "DVWA lab"). The
    image is pulled once via the shared singleton and reused for the 2nd node,
    so there is no slow second pull; both containers run apache and stay up. We
    keep DVWA (not a lighter alpine) because it is the only generic small image
    guaranteed to be in list_inventory on a fresh DB. First-run pulls may take
    several minutes.
    """
    import docker
    from api import nodes as nodes_mod
    from api.agent import SqliteRepo
    from services.docker_provisioner import DockerProvisioner

    # Use the REAL shared provisioner singleton (no mock).
    nodes_mod._reset_provisioner_for_tests(DockerProvisioner())
    raw = docker.from_env()
    repo = SqliteRepo()

    lab_id = tools.create_lab(repo, "DVWA Lifecycle", "two dvwa nodes")["data"]["lab_id"]
    n1 = tools.create_node(repo, lab_id, "dvwa-1", "vulnerables/web-dvwa")["data"]["node_id"]
    n2 = tools.create_node(repo, lab_id, "dvwa-2", "vulnerables/web-dvwa")["data"]["node_id"]
    tools.link_nodes(repo, lab_id, {"node_id": n1}, {"node_id": n2})

    net_name = f"omnilab-lab-{lab_id}"
    try:
        assert tools.start_node(repo, n1)["data"]["state"] == "running"
        assert tools.start_node(repo, n2)["data"]["state"] == "running"

        # Containers actually exist and the lab network is up.
        assert raw.containers.get(f"omnilab-{n1}")
        assert raw.containers.get(f"omnilab-{n2}")
        assert raw.networks.list(names=[net_name])

        state = tools.get_lab_state(repo, lab_id)["data"]
        assert all(node["state"] == "running" for node in state["nodes"])

        assert tools.stop_node(repo, n1)["data"]["state"] == "stopped"
        assert tools.stop_node(repo, n2)["data"]["state"] == "stopped"

        deleted = tools.delete_lab(repo, lab_id)["data"]
        assert deleted["deleted"] is True
        assert deleted["nodes_removed"] == 2
        assert deleted["links_removed"] == 1

        # Containers + network gone; rows removed.
        for nid in (n1, n2):
            with pytest.raises(docker.errors.NotFound):
                raw.containers.get(f"omnilab-{nid}")
        assert raw.networks.list(names=[net_name]) == []
        assert repo.get_lab(lab_id) is None
        assert repo.node_row(n1) is None and repo.node_row(n2) is None
    finally:
        # Self-cleaning: sweep anything left behind on failure.
        for nid in (n1, n2):
            try:
                raw.containers.get(f"omnilab-{nid}").remove(force=True)
            except Exception:
                pass
        for net in raw.networks.list(names=[net_name]):
            try:
                net.remove()
            except Exception:
                pass
        nodes_mod._reset_provisioner_for_tests(None)
