"""End-to-end integration tests against a real Docker daemon (CRE-39 phase 4).

Run with: ``pytest -m integration``

These are explicitly NOT in the default test run (see pyproject.toml's
``addopts = -m 'not integration'``). They require:

- A reachable Docker daemon (``docker ps`` works without sudo)
- Internet to pull the ``alpine:latest`` image on first run

What's verified end-to-end:

1. DockerProvisioner can pull a small image, create a lab network, run a
   container on it, query its IP, exec a shell in it, stop it, and tear
   the network down.

2. POST /api/nodes/{id}/start on a docker-typed node actually produces a
   running container; GET on the web-info endpoint returns the expected
   metadata.

The tests are designed to be **idempotent and self-cleaning** — if a prior
run left containers/networks behind, setup removes them by label first.
"""

from __future__ import annotations

import contextlib
import uuid

import pytest

pytestmark = pytest.mark.integration


# --------------------------------------------------------------- preflight


def _docker_available() -> bool:
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


if not _docker_available():
    pytest.skip(
        "docker daemon unreachable — skipping integration tests "
        "(install docker and add user to the docker group)",
        allow_module_level=True,
    )


# ---------------------------------------------------------------- fixtures


@pytest.fixture()
def lab_id():
    """Generate a unique-per-test lab id, then sweep any containers/networks
    bearing it before AND after the test to keep runs hermetic."""
    lid = f"itest-{uuid.uuid4().hex[:8]}"
    _sweep(lid)
    yield lid
    _sweep(lid)


def _sweep(lab_id: str) -> None:
    """Remove any leftover containers + networks for this lab id."""
    import docker

    client = docker.from_env()
    for c in client.containers.list(
        all=True, filters={"label": f"omnilab.lab_id={lab_id}"}
    ):
        with contextlib.suppress(Exception):
            c.remove(force=True)
    for n in client.networks.list(names=[f"omnilab-lab-{lab_id}"]):
        with contextlib.suppress(Exception):
            n.remove()


# ----------------------------------------------------- provisioner end-to-end


@pytest.mark.asyncio
async def test_provisioner_full_lifecycle_against_real_daemon(lab_id):
    """Pull alpine, run it on a lab network, exec a shell, stop, destroy network."""
    from services.docker_provisioner import DockerProvisioner

    p = DockerProvisioner()
    node_id = f"itest-node-{uuid.uuid4().hex[:8]}"

    # 1. Pull image (or no-op if already local).
    events: list[dict] = []
    await p.ensure_image("alpine:latest", progress_cb=events.append)

    # 2. Create lab network.
    net_id = await p.create_lab_network(lab_id)
    assert net_id

    # 3. Start a container with an explicit long-running command.
    result = await p.start_node(
        node_id=node_id,
        lab_id=lab_id,
        image="alpine:latest",
        name="itest",
        docker_options={"command": ["sleep", "60"], "tty": True},
    )
    assert result["container_id"]
    assert result["ip_address"]  # Must be on the lab network.

    # 4. Lookup the IP via the proxy helper.
    ip = await p.get_node_address(node_id, lab_id)
    assert ip == result["ip_address"]

    # 5. Console shell probe — alpine has /bin/sh, not bash.
    container_name, shell = await p.exec_console(node_id)
    assert container_name == f"omnilab-{node_id}"
    assert shell in ("/bin/sh", "/bin/ash")  # alpine has both as busybox symlinks

    # 6. Stop the node.
    await p.stop_node(node_id)

    # 7. Tear down the lab network.
    await p.destroy_lab_network(lab_id)


# ---------------------------------------------------- API end-to-end roundtrip


def test_api_start_stop_roundtrip_against_real_daemon(client, fresh_db, lab_id):
    """POST /api/nodes/{id}/start actually starts a real container that
    /api/console/{id}/info recognizes; POST /stop cleans up."""
    # Create lab + node directly through the API.
    r = client.post(
        "/api/labs/",
        json={"name": f"itest-{lab_id}", "description": "", "category": "security"},
    )
    api_lab_id = r.json()["id"]

    r = client.post(
        "/api/nodes/",
        json={
            "lab_id": api_lab_id,
            "name": "itest",
            "type": "docker",
            "image": "alpine:latest",
            "config": {
                "docker_options": {"command": ["sleep", "60"], "tty": True},
            },
        },
    )
    assert r.status_code in (200, 201), r.text
    node_id = r.json()["id"]

    try:
        r = client.post(f"/api/nodes/{node_id}/start")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "running"
        assert body["container_id"]
        assert body["ip_address"]

        # Console info should report it as a docker node.
        r = client.get(f"/api/console/{node_id}/info")
        assert r.json()["node_type"] == "docker"
    finally:
        client.post(f"/api/nodes/{node_id}/stop")
