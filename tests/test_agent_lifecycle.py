"""Tests for the AI Lab Builder lifecycle/mutation tools (CRE-43).

start_node, stop_node, delete_lab, push_config — exercised against the
in-memory FakeRepo from test_agent_tools, with the DockerProvisioner mocked via
the SHARED ``_reset_provisioner_for_tests`` hook in api.nodes (the same hook the
HTTP endpoints use — proving there's exactly one docker client seam).

Three layers, mirroring CRE-42:
  1. Unit tests against FakeRepo + a mock provisioner (success + failure).
  2. HTTP-level tests via app.dependency_overrides[get_repo].
  3. (Integration lab build lives in test_agent_tools.py / extended below.)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from api import nodes as nodes_mod
from services import agent_tools as tools
from services.agent_tools import AILBError
from test_agent_tools import FakeRepo

# ---------------------------------------------------------------- fixtures


@pytest.fixture()
def mock_provisioner():
    """Inject a mock DockerProvisioner into the SHARED singleton used by both
    the HTTP endpoints and the agent tools."""
    p = MagicMock()
    p.ensure_image = AsyncMock(return_value=None)
    p.create_lab_network = AsyncMock(return_value="net-id")
    p.start_node = AsyncMock(return_value={
        "container_id": "cid-1", "ip_address": "172.20.0.5", "ports": {}})
    p.stop_node = AsyncMock(return_value=None)
    p.destroy_lab_network = AsyncMock(return_value=None)
    nodes_mod._reset_provisioner_for_tests(p)
    yield p
    nodes_mod._reset_provisioner_for_tests(None)


@pytest.fixture()
def repo():
    return FakeRepo()


def _docker_lab(repo: FakeRepo, n: int = 2):
    lab_id = tools.create_lab(repo, "L")["data"]["lab_id"]
    ids = []
    for i in range(n):
        nid = tools.create_node(
            repo, lab_id, f"d{i}", "vulnerables/web-dvwa")["data"]["node_id"]
        ids.append(nid)
    return lab_id, ids


# ---------------------------------------------------------------- start_node


def test_start_node_docker_ok(repo, mock_provisioner):
    lab_id, [n1, n2] = _docker_lab(repo)
    res = tools.start_node(repo, n1)
    assert res["ok"] is True
    assert res["data"] == {"node_id": n1, "state": "running"}
    assert repo.nodes[n1]["state"] == "running"
    # Shared sequence ran in order.
    mock_provisioner.ensure_image.assert_awaited_once()
    mock_provisioner.create_lab_network.assert_awaited_once_with(lab_id)
    mock_provisioner.start_node.assert_awaited_once()


def test_start_node_idempotent_no_side_effect(repo, mock_provisioner):
    lab_id, [n1, _] = _docker_lab(repo)
    tools.start_node(repo, n1)
    mock_provisioner.start_node.reset_mock()
    res = tools.start_node(repo, n1)
    assert res["data"]["state"] == "running"
    mock_provisioner.start_node.assert_not_awaited()  # no second start


def test_start_node_not_found(repo, mock_provisioner):
    with pytest.raises(AILBError) as ei:
        tools.start_node(repo, "ghost")
    assert ei.value.code == "NOT_FOUND"


def test_start_node_capacity_exceeded_on_disk_full(repo, mock_provisioner):
    from services.docker_provisioner import DiskFullError
    lab_id, [n1, _] = _docker_lab(repo)
    mock_provisioner.ensure_image = AsyncMock(side_effect=DiskFullError("no space"))
    with pytest.raises(AILBError) as ei:
        tools.start_node(repo, n1)
    assert ei.value.code == "CAPACITY_EXCEEDED"


def test_start_node_timeout_on_provisioner_error(repo, mock_provisioner):
    from services.docker_provisioner import DockerProvisionerError
    lab_id, [n1, _] = _docker_lab(repo)
    mock_provisioner.start_node = AsyncMock(side_effect=DockerProvisionerError("boom"))
    with pytest.raises(AILBError) as ei:
        tools.start_node(repo, n1)
    assert ei.value.code == "TIMEOUT"


def test_start_node_non_docker_flips_status(repo, mock_provisioner):
    lab_id = tools.create_lab(repo, "L")["data"]["lab_id"]
    nid = tools.create_node(repo, lab_id, "h", "vulnerables/web-dvwa")["data"]["node_id"]
    repo.nodes[nid]["type"] = "pty"
    res = tools.start_node(repo, nid)
    assert res["data"]["state"] == "running"
    mock_provisioner.start_node.assert_not_awaited()


# ---------------------------------------------------------------- stop_node


def test_stop_node_docker_tears_down_network_when_last(repo, mock_provisioner):
    lab_id, [n1, n2] = _docker_lab(repo)
    tools.start_node(repo, n1)
    res = tools.stop_node(repo, n1)
    assert res["data"] == {"node_id": n1, "state": "stopped"}
    assert repo.nodes[n1]["state"] == "stopped"
    mock_provisioner.stop_node.assert_awaited_with(n1)
    # No other docker node running -> network destroyed.
    mock_provisioner.destroy_lab_network.assert_awaited_with(lab_id)


def test_stop_node_keeps_network_when_others_running(repo, mock_provisioner):
    lab_id, [n1, n2] = _docker_lab(repo)
    tools.start_node(repo, n1)
    tools.start_node(repo, n2)
    mock_provisioner.destroy_lab_network.reset_mock()
    tools.stop_node(repo, n1)
    mock_provisioner.stop_node.assert_awaited_with(n1)
    mock_provisioner.destroy_lab_network.assert_not_awaited()


def test_stop_node_idempotent(repo, mock_provisioner):
    lab_id, [n1, _] = _docker_lab(repo)
    res = tools.stop_node(repo, n1)  # already stopped
    assert res["data"]["state"] == "stopped"


def test_stop_node_not_found(repo, mock_provisioner):
    with pytest.raises(AILBError) as ei:
        tools.stop_node(repo, "ghost")
    assert ei.value.code == "NOT_FOUND"


# ---------------------------------------------------------------- delete_lab


def test_delete_lab_stops_nodes_and_removes_rows(repo, mock_provisioner):
    lab_id, [n1, n2] = _docker_lab(repo)
    tools.link_nodes(repo, lab_id, {"node_id": n1}, {"node_id": n2})
    tools.start_node(repo, n1)
    tools.start_node(repo, n2)

    res = tools.delete_lab(repo, lab_id)
    assert res["data"]["deleted"] is True
    assert res["data"]["nodes_removed"] == 2
    assert res["data"]["links_removed"] == 1
    assert lab_id not in repo.labs
    assert n1 not in repo.nodes and n2 not in repo.nodes
    # Every node was stopped before deletion (no orphaned containers).
    assert mock_provisioner.stop_node.await_count >= 2


def test_delete_lab_not_found(repo, mock_provisioner):
    with pytest.raises(AILBError) as ei:
        tools.delete_lab(repo, "ghost")
    assert ei.value.code == "NOT_FOUND"


# ---------------------------------------------------------------- push_config


def test_push_config_startup_persists(repo, mock_provisioner):
    lab_id, [n1, _] = _docker_lab(repo)
    res = tools.push_config(repo, n1, "interface eth0\n ip address 10.0.0.1/24",
                            mode="startup")
    assert res["data"] == {"applied": True, "mode": "startup", "warnings": []}
    assert repo.nodes[n1]["config"]["startup_config"].startswith("interface eth0")


def test_push_config_startup_preserves_existing_config(repo, mock_provisioner):
    lab_id, [n1, _] = _docker_lab(repo)
    repo.nodes[n1]["config"] = {"docker_options": {"privileged": True}}
    tools.push_config(repo, n1, "hostname r1", mode="startup")
    assert repo.nodes[n1]["config"]["docker_options"] == {"privileged": True}
    assert repo.nodes[n1]["config"]["startup_config"] == "hostname r1"


def test_push_config_live_requires_running(repo, mock_provisioner):
    lab_id, [n1, _] = _docker_lab(repo)  # stopped
    with pytest.raises(AILBError) as ei:
        tools.push_config(repo, n1, "x", mode="live")
    assert ei.value.code == "NODE_NOT_RUNNING"


def test_push_config_live_docker_generic_ok(repo, mock_provisioner):
    lab_id, [n1, _] = _docker_lab(repo)
    repo.nodes[n1]["state"] = "running"
    container = MagicMock()
    container.exec_run.return_value = (0, b"")
    mock_provisioner.client = MagicMock()
    mock_provisioner.client.containers.get.return_value = container
    res = tools.push_config(repo, n1, "key=value", mode="live")
    assert res["data"]["applied"] is True
    assert res["data"]["mode"] == "live"
    container.exec_run.assert_called()


def test_push_config_live_frr_rejected(repo, mock_provisioner):
    lab_id = tools.create_lab(repo, "L")["data"]["lab_id"]
    n1 = tools.create_node(repo, lab_id, "r1", "frrouting/frr:latest")["data"]["node_id"]
    repo.nodes[n1]["state"] = "running"
    container = MagicMock()
    # vtysh rejects the line: non-zero exit + '% ...' error marker.
    container.exec_run.return_value = (1, b"% Unknown command: bogus line")
    mock_provisioner.client = MagicMock()
    mock_provisioner.client.containers.get.return_value = container
    with pytest.raises(AILBError) as ei:
        tools.push_config(repo, n1, "bogus line", mode="live")
    assert ei.value.code == "CONFIG_REJECTED"
    assert "bogus line" in ei.value.details["lines"]


def test_push_config_invalid_mode(repo, mock_provisioner):
    lab_id, [n1, _] = _docker_lab(repo)
    with pytest.raises(AILBError) as ei:
        tools.push_config(repo, n1, "x", mode="bananas")
    assert ei.value.code == "VALIDATION"


def test_push_config_not_found(repo, mock_provisioner):
    with pytest.raises(AILBError) as ei:
        tools.push_config(repo, "ghost", "x")
    assert ei.value.code == "NOT_FOUND"


def test_push_config_live_qemu_not_implemented(repo, mock_provisioner):
    lab_id = tools.create_lab(repo, "L")["data"]["lab_id"]
    n1 = tools.create_node(repo, lab_id, "v", "vulnerables/web-dvwa")["data"]["node_id"]
    repo.nodes[n1]["type"] = "qemu"
    repo.nodes[n1]["state"] = "running"
    with pytest.raises(AILBError) as ei:
        tools.push_config(repo, n1, "x", mode="live")
    assert ei.value.code == "VALIDATION"


# ---------------------------------------------------------------- HTTP layer


@pytest.fixture()
def http_repo(client):
    from api.agent import get_repo
    from main import app

    fake = FakeRepo()
    app.dependency_overrides[get_repo] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_repo, None)


def test_http_lifecycle_tools_registered(client):
    body = client.get("/api/agent/tools").json()
    for name in ("start_node", "stop_node", "delete_lab", "push_config"):
        assert name in body["data"]["tools"]


def test_http_start_then_stop(client, http_repo, mock_provisioner):
    lab_id, [n1, _] = _docker_lab(http_repo)
    r = client.post("/api/agent/tools/start_node", json={"args": {"node_id": n1}})
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["state"] == "running"

    r = client.post("/api/agent/tools/stop_node", json={"args": {"node_id": n1}})
    assert r.json()["data"]["state"] == "stopped"


def test_http_push_config_node_not_running_envelope(client, http_repo, mock_provisioner):
    lab_id, [n1, _] = _docker_lab(http_repo)
    r = client.post("/api/agent/tools/push_config",
                    json={"args": {"node_id": n1, "config_text": "x", "mode": "live"}})
    body = r.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "NODE_NOT_RUNNING"
