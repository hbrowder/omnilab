"""Unit tests for DockerProvisioner.

The docker SDK is fully mocked here — these tests must pass in CI without a
live docker daemon. Integration tests that exercise a real daemon will live in
a separate ``@pytest.mark.integration`` tier (out of scope for phase 1).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

# conftest already puts backend/ on sys.path, but be defensive in case this file
# is run directly via `pytest tests/test_docker_provisioner.py`.
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from docker.errors import APIError, ImageNotFound, NotFound  # noqa: E402
from services.docker_provisioner import (  # noqa: E402
    CONTAINER_PREFIX,
    NETWORK_PREFIX,
    SHELL_FALLBACKS,
    DockerProvisioner,
    DockerProvisionerError,
)

# --------------------------------------------------------------------- helpers


def make_client() -> MagicMock:
    """Mock docker client with the four sub-collections the provisioner uses."""
    client = MagicMock()
    client.images = MagicMock()
    client.containers = MagicMock()
    client.networks = MagicMock()
    client.api = MagicMock()
    return client


def make_provisioner() -> tuple[DockerProvisioner, MagicMock]:
    client = make_client()
    return DockerProvisioner(client=client), client


# -------------------------------------------------------------------- __init__


def test_init_without_client_or_sdk_raises(monkeypatch):
    """If the docker module is unavailable, init must fail fast with a clear message."""
    import services.docker_provisioner as mod

    monkeypatch.setattr(mod, "docker", None)
    with pytest.raises(DockerProvisionerError, match="docker SDK not installed"):
        DockerProvisioner()


def test_init_with_unreachable_daemon_raises(monkeypatch):
    """If from_env returns a client whose ping() fails, surface the docker-group hint."""
    import services.docker_provisioner as mod

    fake_client = MagicMock()
    fake_client.ping.side_effect = OSError("Cannot connect to docker socket")

    fake_docker_mod = MagicMock()
    fake_docker_mod.from_env.return_value = fake_client
    monkeypatch.setattr(mod, "docker", fake_docker_mod)

    with pytest.raises(DockerProvisionerError, match="Cannot reach Docker daemon"):
        DockerProvisioner()


def test_init_with_injected_client_does_not_call_from_env():
    """Passing an explicit client (the test path) must bypass autodetect entirely."""
    client = make_client()
    p = DockerProvisioner(client=client)
    assert p.client is client
    client.ping.assert_not_called()  # no autoconnect when client is injected


# ----------------------------------------------------------------- ensure_image


@pytest.mark.asyncio
async def test_ensure_image_fast_path_when_present():
    """If the image is already local, do not call pull at all."""
    p, client = make_provisioner()
    client.images.get.return_value = MagicMock()  # image exists

    await p.ensure_image("kalilinux/kali-rolling")

    client.images.get.assert_called_once_with("kalilinux/kali-rolling")
    client.api.pull.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_image_pulls_when_missing_and_streams_progress():
    """When the image is missing, pull is called and each event reaches the callback."""
    p, client = make_provisioner()
    client.images.get.side_effect = ImageNotFound("not local")
    events = [
        {"status": "Pulling fs layer", "id": "abc"},
        {"status": "Downloading", "progressDetail": {"current": 10, "total": 100}, "id": "abc"},
        {"status": "Pull complete", "id": "abc"},
    ]
    client.api.pull.return_value = iter(events)

    captured: list[dict] = []
    await p.ensure_image("wazuh/wazuh-manager:4.7.0", progress_cb=captured.append)

    client.api.pull.assert_called_once_with(
        "wazuh/wazuh-manager:4.7.0", stream=True, decode=True
    )
    assert captured == events


@pytest.mark.asyncio
async def test_ensure_image_raises_on_error_event():
    """Docker streams an error event when the pull fails — surface it as our error type."""
    p, client = make_provisioner()
    client.images.get.side_effect = ImageNotFound("not local")
    client.api.pull.return_value = iter(
        [{"status": "Pulling"}, {"error": "manifest unknown"}]
    )

    with pytest.raises(DockerProvisionerError, match="manifest unknown"):
        await p.ensure_image("bogus/image:latest")


@pytest.mark.asyncio
async def test_ensure_image_progress_callback_exceptions_are_swallowed():
    """A buggy UI callback must never abort an in-flight pull."""
    p, client = make_provisioner()
    client.images.get.side_effect = ImageNotFound("not local")
    client.api.pull.return_value = iter([{"status": "Pulling"}, {"status": "Done"}])

    def bad_cb(_event):
        raise RuntimeError("UI bug")

    await p.ensure_image("kalilinux/kali-rolling", progress_cb=bad_cb)
    # Reaching this line means we did not propagate the callback's exception.


# --------------------------------------------------------------- lab networks


@pytest.mark.asyncio
async def test_create_lab_network_creates_when_missing():
    p, client = make_provisioner()
    client.networks.get.side_effect = NotFound("missing")
    new_net = MagicMock(id="net123")
    client.networks.create.return_value = new_net

    net_id = await p.create_lab_network("lab-abc")

    assert net_id == "net123"
    client.networks.create.assert_called_once_with(
        f"{NETWORK_PREFIX}lab-abc",
        driver="bridge",
        labels={"omnilab.lab_id": "lab-abc"},
    )


@pytest.mark.asyncio
async def test_create_lab_network_is_idempotent():
    """Second call must reuse the existing network (no second create)."""
    p, client = make_provisioner()
    existing = MagicMock(id="existing-id")
    client.networks.get.return_value = existing

    net_id = await p.create_lab_network("lab-abc")

    assert net_id == "existing-id"
    client.networks.create.assert_not_called()


@pytest.mark.asyncio
async def test_destroy_lab_network_removes_when_present():
    p, client = make_provisioner()
    network = MagicMock()
    client.networks.get.return_value = network

    await p.destroy_lab_network("lab-abc")

    network.remove.assert_called_once_with()


@pytest.mark.asyncio
async def test_destroy_lab_network_silent_when_missing():
    """Destroying an already-gone network is a no-op (idempotent cleanup)."""
    p, client = make_provisioner()
    client.networks.get.side_effect = NotFound("missing")

    await p.destroy_lab_network("lab-abc")
    # No raise == pass.


@pytest.mark.asyncio
async def test_destroy_lab_network_wraps_api_errors():
    p, client = make_provisioner()
    network = MagicMock()
    network.remove.side_effect = APIError("network in use")
    client.networks.get.return_value = network

    with pytest.raises(DockerProvisionerError, match="network in use"):
        await p.destroy_lab_network("lab-abc")


# ---------------------------------------------------------------- start_node


@pytest.mark.asyncio
async def test_start_node_runs_container_with_expected_args():
    p, client = make_provisioner()
    container = MagicMock(id="cid-1")
    container.attrs = {
        "NetworkSettings": {
            "Networks": {f"{NETWORK_PREFIX}lab-1": {"IPAddress": "172.20.0.5"}},
            "Ports": {"22/tcp": [{"HostPort": "20022"}]},
        }
    }
    client.containers.run.return_value = container

    result = await p.start_node(
        node_id="node-1",
        lab_id="lab-1",
        image="kalilinux/kali-rolling",
        name="kali",
        ports={"22/tcp": 20022},
    )

    assert result == {
        "container_id": "cid-1",
        "ip_address": "172.20.0.5",
        "ports": {"22/tcp": [{"HostPort": "20022"}]},
    }
    client.containers.run.assert_called_once()
    args, kwargs = client.containers.run.call_args
    assert args == ("kalilinux/kali-rolling",)
    assert kwargs["name"] == f"{CONTAINER_PREFIX}node-1"
    assert kwargs["network"] == f"{NETWORK_PREFIX}lab-1"
    assert kwargs["hostname"] == "kali"
    assert kwargs["detach"] is True
    assert kwargs["labels"] == {"omnilab.node_id": "node-1", "omnilab.lab_id": "lab-1"}
    assert kwargs["ports"] == {"22/tcp": 20022}
    container.reload.assert_called_once()


@pytest.mark.asyncio
async def test_start_node_merges_docker_options():
    """Per-template options like cap_add / privileged / volumes must be merged into run()."""
    p, client = make_provisioner()
    container = MagicMock(id="cid-2", attrs={"NetworkSettings": {"Networks": {}}})
    client.containers.run.return_value = container

    docker_options = {
        "cap_add": ["NET_ADMIN"],
        "privileged": False,
        "environment": {"FOO": "bar"},
        "volumes": {"/data": {"bind": "/data", "mode": "rw"}},
    }
    await p.start_node(
        node_id="node-2",
        lab_id="lab-2",
        image="kalilinux/kali-rolling",
        name="kali",
        docker_options=docker_options,
    )

    _, kwargs = client.containers.run.call_args
    assert kwargs["cap_add"] == ["NET_ADMIN"]
    assert kwargs["environment"] == {"FOO": "bar"}
    assert kwargs["volumes"] == {"/data": {"bind": "/data", "mode": "rw"}}


@pytest.mark.asyncio
async def test_start_node_handles_missing_network_attrs():
    """Some images come up without an attached network record; return empty IP, not raise."""
    p, client = make_provisioner()
    container = MagicMock(id="cid-3", attrs={"NetworkSettings": {}})
    client.containers.run.return_value = container

    result = await p.start_node(
        node_id="node-3", lab_id="lab-3", image="alpine", name="alpine"
    )

    assert result["ip_address"] == ""
    assert result["ports"] == {}


# ----------------------------------------------------------------- stop_node


@pytest.mark.asyncio
async def test_stop_node_force_removes_container():
    p, client = make_provisioner()
    container = MagicMock()
    client.containers.get.return_value = container

    await p.stop_node("node-1")

    client.containers.get.assert_called_once_with(f"{CONTAINER_PREFIX}node-1")
    container.remove.assert_called_once_with(force=True)


@pytest.mark.asyncio
async def test_stop_node_silent_when_missing():
    p, client = make_provisioner()
    client.containers.get.side_effect = NotFound("missing")

    await p.stop_node("node-1")


@pytest.mark.asyncio
async def test_stop_node_wraps_api_errors():
    p, client = make_provisioner()
    container = MagicMock()
    container.remove.side_effect = APIError("device busy")
    client.containers.get.return_value = container

    with pytest.raises(DockerProvisionerError, match="device busy"):
        await p.stop_node("node-1")


# -------------------------------------------------------------- exec_console


@pytest.mark.asyncio
async def test_exec_console_returns_first_available_shell():
    p, client = make_provisioner()
    container = MagicMock()
    # bash present
    container.exec_run.return_value = (0, b"")
    client.containers.get.return_value = container

    name, shell = await p.exec_console("node-1")

    assert name == f"{CONTAINER_PREFIX}node-1"
    assert shell == "/bin/bash"
    container.exec_run.assert_called_once_with(["test", "-x", "/bin/bash"])


@pytest.mark.asyncio
async def test_exec_console_falls_back_through_shell_list():
    p, client = make_provisioner()
    container = MagicMock()
    # bash & sh missing, ash present (Alpine)
    container.exec_run.side_effect = [(1, b""), (1, b""), (0, b"")]
    client.containers.get.return_value = container

    name, shell = await p.exec_console("node-1")

    assert shell == "/bin/ash"
    container.exec_run.assert_has_calls(
        [call(["test", "-x", s]) for s in SHELL_FALLBACKS]
    )


@pytest.mark.asyncio
async def test_exec_console_raises_when_no_shell_found():
    p, client = make_provisioner()
    container = MagicMock()
    container.exec_run.return_value = (1, b"")
    client.containers.get.return_value = container

    with pytest.raises(DockerProvisionerError, match="no usable shell"):
        await p.exec_console("node-1")


@pytest.mark.asyncio
async def test_exec_console_raises_when_container_missing():
    p, client = make_provisioner()
    client.containers.get.side_effect = NotFound("nope")

    with pytest.raises(DockerProvisionerError, match="not found"):
        await p.exec_console("node-1")
