"""Wiring tests: nodes.py and console.py docker branches (CRE-39 phase 2).

The DockerProvisioner is mocked via the ``_reset_provisioner_for_tests`` hook
in each router module — no docker daemon required. Tests exercise the HTTP /
WebSocket layer and verify the right provisioner calls happen in the right
order with the right arguments.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from api import console as console_mod
from api import nodes as nodes_mod

# --------------------------------------------------------------- fixtures


@pytest.fixture()
def mock_provisioner_nodes():
    """Inject a mock DockerProvisioner into api.nodes for the duration of the test."""
    p = MagicMock()
    p.ensure_image = AsyncMock(return_value=None)
    p.create_lab_network = AsyncMock(return_value="net-id")
    p.start_node = AsyncMock(
        return_value={
            "container_id": "cid-1",
            "ip_address": "172.20.0.5",
            "ports": {"22/tcp": [{"HostPort": "20022"}]},
        }
    )
    p.stop_node = AsyncMock(return_value=None)
    p.destroy_lab_network = AsyncMock(return_value=None)
    nodes_mod._reset_provisioner_for_tests(p)
    yield p
    nodes_mod._reset_provisioner_for_tests(None)


@pytest.fixture()
def mock_provisioner_console():
    """Inject a mock DockerProvisioner into api.console."""
    p = MagicMock()
    p.exec_console = AsyncMock(return_value=("omnilab-n1", "/bin/bash"))
    # Build a fake API surface for the console exec path.
    fake_api = MagicMock()
    fake_api.exec_create.return_value = {"Id": "exec-1"}
    fake_sock = MagicMock()
    fake_sock._sock = MagicMock()
    fake_sock._sock.recv.return_value = b""  # immediate EOF closes the reader
    fake_api.exec_start.return_value = fake_sock
    fake_container = MagicMock(id="cid-abc")
    p.client = MagicMock()
    p.client.api = fake_api
    p.client.containers.get.return_value = fake_container
    console_mod._reset_provisioner_for_tests(p)
    yield p
    console_mod._reset_provisioner_for_tests(None)


def _create_lab(client) -> str:
    r = client.post("/api/labs/", json={"name": "cre39", "description": "", "category": "security"})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _create_docker_node(client, lab_id: str, *, image="alpine", config=None) -> str:
    body = {
        "lab_id": lab_id,
        "name": "kali",
        "type": "docker",
        "image": image,
        "console_type": "pty",
    }
    if config is not None:
        body["config"] = config
    r = client.post("/api/nodes/", json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


# --------------------------------------------------------- nodes start_node


def test_start_docker_node_pulls_image_creates_network_then_runs(
    client, fresh_db, mock_provisioner_nodes
):
    lab_id = _create_lab(client)
    node_id = _create_docker_node(client, lab_id)

    r = client.post(f"/api/nodes/{node_id}/start")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "running"
    assert body["container_id"] == "cid-1"
    assert body["ip_address"] == "172.20.0.5"

    # Right calls happened, in the right order.
    p = mock_provisioner_nodes
    p.ensure_image.assert_awaited_once()
    assert p.ensure_image.await_args.args[0] == "alpine"
    p.create_lab_network.assert_awaited_once_with(lab_id)
    p.start_node.assert_awaited_once()
    kwargs = p.start_node.await_args.kwargs
    assert kwargs["node_id"] == node_id
    assert kwargs["lab_id"] == lab_id
    assert kwargs["image"] == "alpine"
    assert kwargs["name"] == "kali"
    assert kwargs["docker_options"] == {}
    assert kwargs["ports"] is None


def test_start_docker_node_passes_docker_options_from_config(
    client, fresh_db, mock_provisioner_nodes
):
    lab_id = _create_lab(client)
    node_id = _create_docker_node(
        client,
        lab_id,
        config={
            "docker_options": {"cap_add": ["NET_ADMIN"], "privileged": False},
            "ports": {"22/tcp": 20022},
        },
    )

    r = client.post(f"/api/nodes/{node_id}/start")
    assert r.status_code == 200

    p = mock_provisioner_nodes
    kwargs = p.start_node.await_args.kwargs
    assert kwargs["docker_options"] == {"cap_add": ["NET_ADMIN"], "privileged": False}
    assert kwargs["ports"] == {"22/tcp": 20022}


def test_start_docker_node_rejects_missing_image(client, fresh_db, mock_provisioner_nodes):
    lab_id = _create_lab(client)
    # NodeCreate allows image=None — exercise that path.
    r = client.post(
        "/api/nodes/",
        json={"lab_id": lab_id, "name": "x", "type": "docker", "image": None},
    )
    node_id = r.json()["id"]

    r = client.post(f"/api/nodes/{node_id}/start")
    assert r.status_code == 400
    assert "no image" in r.json()["detail"].lower()
    mock_provisioner_nodes.ensure_image.assert_not_awaited()


def test_start_docker_node_503_when_daemon_unreachable(client, fresh_db):
    """If the provisioner can't be constructed, the start endpoint returns 503."""
    from services.docker_provisioner import DockerProvisionerError

    lab_id = _create_lab(client)
    node_id = _create_docker_node(client, lab_id)

    # Patch the module-level factory to raise.
    original = nodes_mod._get_provisioner
    nodes_mod._get_provisioner = lambda: (_ for _ in ()).throw(
        DockerProvisionerError("Cannot reach Docker daemon. test")
    )
    try:
        r = client.post(f"/api/nodes/{node_id}/start")
        assert r.status_code == 503
        assert "docker" in r.json()["detail"].lower()
    finally:
        nodes_mod._get_provisioner = original


def test_start_non_docker_node_does_not_touch_provisioner(
    client, fresh_db, mock_provisioner_nodes
):
    """PTY/qemu nodes must still work without provisioner calls."""
    lab_id = _create_lab(client)
    r = client.post(
        "/api/nodes/",
        json={"lab_id": lab_id, "name": "host-shell", "type": "host", "console_type": "pty"},
    )
    node_id = r.json()["id"]

    r = client.post(f"/api/nodes/{node_id}/start")
    assert r.status_code == 200
    assert r.json()["status"] == "running"
    mock_provisioner_nodes.ensure_image.assert_not_awaited()
    mock_provisioner_nodes.start_node.assert_not_awaited()


# --------------------------------------------------------- nodes stop_node


def test_stop_docker_node_removes_container_and_tears_down_network(
    client, fresh_db, mock_provisioner_nodes
):
    """Single docker node — stop should remove container AND destroy the lab network."""
    lab_id = _create_lab(client)
    node_id = _create_docker_node(client, lab_id)
    client.post(f"/api/nodes/{node_id}/start")

    r = client.post(f"/api/nodes/{node_id}/stop")
    assert r.status_code == 200
    assert r.json()["status"] == "stopped"

    p = mock_provisioner_nodes
    p.stop_node.assert_awaited_with(node_id)
    p.destroy_lab_network.assert_awaited_with(lab_id)


def test_stop_docker_node_keeps_network_when_others_still_running(
    client, fresh_db, mock_provisioner_nodes
):
    """Two docker nodes in same lab — stopping one must NOT tear down the network."""
    lab_id = _create_lab(client)
    n1 = _create_docker_node(client, lab_id, image="alpine")
    n2 = _create_docker_node(client, lab_id, image="alpine")
    client.post(f"/api/nodes/{n1}/start")
    client.post(f"/api/nodes/{n2}/start")

    p = mock_provisioner_nodes
    p.destroy_lab_network.reset_mock()

    r = client.post(f"/api/nodes/{n1}/stop")
    assert r.status_code == 200

    p.stop_node.assert_awaited_with(n1)
    p.destroy_lab_network.assert_not_awaited()


# ------------------------------------------------------------- console docker


def test_console_info_reports_docker_node_type(client, fresh_db):
    lab_id = _create_lab(client)
    node_id = _create_docker_node(client, lab_id)
    r = client.get(f"/api/console/{node_id}/info")
    assert r.status_code == 200
    body = r.json()
    assert body["node_type"] == "docker"
    assert body["websocket_url"].endswith(f"/api/console/{node_id}/ws")


def test_console_ws_dispatches_to_docker_branch(
    client, fresh_db, mock_provisioner_console
):
    """Opening the console WS on a docker node must call exec_console + exec_create+exec_start."""
    import time

    lab_id = _create_lab(client)
    node_id = _create_docker_node(client, lab_id)

    with client.websocket_connect(f"/api/console/{node_id}/ws") as ws:
        # Wait up to 2s for the server-side handler to reach exec_console.
        # The mock recv() returns b'' immediately (EOF), so once exec_start has
        # been called the reader exits and the handler unwinds.
        deadline = time.monotonic() + 2.0
        p = mock_provisioner_console
        while time.monotonic() < deadline:
            if p.client.api.exec_start.called:
                break
            try:
                ws.receive(timeout=0.05)
            except Exception:
                pass

    p = mock_provisioner_console
    p.exec_console.assert_awaited_with(node_id)
    p.client.api.exec_create.assert_called_once()
    create_kwargs = p.client.api.exec_create.call_args.kwargs
    assert create_kwargs["tty"] is True
    assert create_kwargs["stdin"] is True
    assert create_kwargs["cmd"] == ["/bin/bash"]
    p.client.api.exec_start.assert_called_once()
    start_kwargs = p.client.api.exec_start.call_args.kwargs
    assert start_kwargs["socket"] is True
    assert start_kwargs["tty"] is True


def test_console_ws_sends_error_when_provisioner_unreachable(client, fresh_db):
    """If provisioner construction fails, the WS sends a clean ERROR text frame."""
    from services.docker_provisioner import DockerProvisionerError

    lab_id = _create_lab(client)
    node_id = _create_docker_node(client, lab_id)

    original = console_mod._get_provisioner
    console_mod._get_provisioner = lambda: (_ for _ in ()).throw(
        DockerProvisionerError("Cannot reach Docker daemon. test")
    )
    try:
        with client.websocket_connect(f"/api/console/{node_id}/ws") as ws:
            msg = ws.receive_text()
            assert msg.startswith("ERROR:")
            assert "docker" in msg.lower()
    finally:
        console_mod._get_provisioner = original


# ---------------------------------------------------- provision-ws fan-out


def test_provision_ws_accepts_connection_and_registers_listener(client, fresh_db):
    """The provision WS must register itself in the fan-out registry on connect."""
    lab_id = _create_lab(client)
    node_id = _create_docker_node(client, lab_id)

    with client.websocket_connect(f"/api/nodes/{node_id}/provision-ws"):
        # Inside the with-block the listener should be registered.
        assert node_id in nodes_mod._provision_listeners
        assert len(nodes_mod._provision_listeners[node_id]) == 1

    # After exit, the cleanup branch should have pruned the bucket.
    assert node_id not in nodes_mod._provision_listeners


@pytest.mark.asyncio
async def test_broadcast_provision_sends_to_each_listener():
    """Verify the fan-out helper hits every registered WebSocket exactly once."""
    ws_a = MagicMock()
    ws_a.send_json = AsyncMock()
    ws_b = MagicMock()
    ws_b.send_json = AsyncMock()
    nodes_mod._provision_listeners["test-node"] = {ws_a, ws_b}
    try:
        await nodes_mod._broadcast_provision(
            "test-node", {"type": "pull", "status": "Downloading"}
        )
        ws_a.send_json.assert_awaited_once()
        ws_b.send_json.assert_awaited_once()
    finally:
        nodes_mod._provision_listeners.pop("test-node", None)
