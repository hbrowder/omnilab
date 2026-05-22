"""DockerProvisioner — single owner of all docker side-effects for OmniLab labs.

Wraps the `docker` SDK so the rest of the backend never imports it directly. All
methods are async (sync SDK calls offloaded via `asyncio.to_thread`) and
idempotent where the ticket calls for it.

Naming conventions (must match across the codebase):
- Containers: ``omnilab-<node_id>``
- Networks:   ``omnilab-lab-<lab_id>``

Phase 1 (CRE-39) lands this module + unit tests. Wiring into ``api/nodes.py``
and ``api/console.py`` is phase 2.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

try:
    import docker
    from docker.errors import APIError, ImageNotFound, NotFound
except ImportError:  # pragma: no cover - docker is a hard dependency in prod
    docker = None  # type: ignore[assignment]
    APIError = NotFound = ImageNotFound = Exception  # type: ignore[misc,assignment]


CONTAINER_PREFIX = "omnilab-"
NETWORK_PREFIX = "omnilab-lab-"

# Shells tried in order for ``exec_console``. Bash covers Kali/Ubuntu/Jenkins;
# sh is the POSIX fallback; ash is Alpine (Suricata, Zeek minimal images).
SHELL_FALLBACKS = ("/bin/bash", "/bin/sh", "/bin/ash")


class DockerProvisionerError(RuntimeError):
    """Raised when docker is unreachable or an operation fails unrecoverably."""


def _container_name(node_id: str) -> str:
    return f"{CONTAINER_PREFIX}{node_id}"


def _network_name(lab_id: str) -> str:
    return f"{NETWORK_PREFIX}{lab_id}"


class DockerProvisioner:
    """Service object — owns the docker client and exposes lab/node lifecycle ops."""

    def __init__(self, client: Any | None = None) -> None:
        """Build with an explicit client (tests inject a mock) or autodetect.

        Autodetect path raises DockerProvisionerError if the daemon is
        unreachable — surfaces a clear message at app startup rather than a
        500 on the first node start.
        """
        if client is not None:
            self.client = client
            return

        if docker is None:
            raise DockerProvisionerError(
                "docker SDK not installed — pip install docker>=7.0.0"
            )
        try:
            self.client = docker.from_env()
            # ``ping()`` forces an actual connection attempt; ``from_env`` is lazy.
            self.client.ping()
        except Exception as exc:  # noqa: BLE001 — wrap any SDK/transport error
            raise DockerProvisionerError(
                "Cannot reach Docker daemon. If running as a non-root user, "
                "ensure your user is in the 'docker' group "
                "(sudo usermod -aG docker $USER && newgrp docker)."
            ) from exc

    # ------------------------------------------------------------------ images

    async def ensure_image(
        self,
        image: str,
        progress_cb: Callable[[dict], None] | None = None,
    ) -> None:
        """Pull ``image`` if not already present locally. Idempotent.

        If ``progress_cb`` is provided, each docker pull progress event dict
        (status/progressDetail/id) is forwarded to it. Pull is performed in a
        thread so the event loop stays responsive on multi-GB images.
        """

        def _pull() -> None:
            # Fast path: already pulled.
            try:
                self.client.images.get(image)
                return
            except ImageNotFound:
                pass

            api = self.client.api
            for event in api.pull(image, stream=True, decode=True):
                if progress_cb is not None:
                    try:
                        progress_cb(event)
                    except Exception:  # noqa: BLE001 — never let a UI cb kill a pull
                        pass
                if isinstance(event, dict) and event.get("error"):
                    raise DockerProvisionerError(
                        f"docker pull {image} failed: {event['error']}"
                    )

        await asyncio.to_thread(_pull)

    # ---------------------------------------------------------------- networks

    async def create_lab_network(self, lab_id: str) -> str:
        """Create (or reuse) ``omnilab-lab-<lab_id>`` bridge network. Returns network ID."""
        name = _network_name(lab_id)

        def _create() -> str:
            try:
                existing = self.client.networks.get(name)
                return str(existing.id or "")
            except NotFound:
                pass
            network = self.client.networks.create(
                name,
                driver="bridge",
                labels={"omnilab.lab_id": lab_id},
            )
            return str(network.id or "")

        return await asyncio.to_thread(_create)

    async def destroy_lab_network(self, lab_id: str) -> None:
        """Remove the lab network. No-op if it doesn't exist."""
        name = _network_name(lab_id)

        def _destroy() -> None:
            try:
                network = self.client.networks.get(name)
            except NotFound:
                return
            try:
                network.remove()
            except APIError as exc:
                raise DockerProvisionerError(
                    f"docker network rm {name} failed: {exc}"
                ) from exc

        await asyncio.to_thread(_destroy)

    # ------------------------------------------------------------------- nodes

    async def start_node(
        self,
        node_id: str,
        lab_id: str,
        image: str,
        name: str,
        ports: dict | None = None,
        docker_options: dict | None = None,
    ) -> dict:
        """Start a container for one node.

        Equivalent to:
            docker run -d --name omnilab-<node_id>
                          --network omnilab-lab-<lab_id>
                          --hostname <name>
                          [-p host:cont]...
                          [extra docker_options...]
                          <image>

        Returns ``{container_id, ip_address, ports}``. ``docker_options`` is
        merged into the run kwargs and is the channel for per-template quirks
        (``cap_add``, ``privileged``, ``volumes``, ``environment``).
        """
        container_name = _container_name(node_id)
        network_name = _network_name(lab_id)

        run_kwargs: dict[str, Any] = {
            "name": container_name,
            "hostname": name,
            "network": network_name,
            "detach": True,
            "labels": {
                "omnilab.node_id": node_id,
                "omnilab.lab_id": lab_id,
            },
        }
        if ports:
            run_kwargs["ports"] = ports
        if docker_options:
            # Caller-supplied options win — they're per-template intentional.
            run_kwargs.update(docker_options)

        def _run() -> dict:
            container = self.client.containers.run(image, **run_kwargs)
            container.reload()
            networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
            ip_address = ""
            if network_name in networks:
                ip_address = networks[network_name].get("IPAddress", "") or ""
            return {
                "container_id": container.id,
                "ip_address": ip_address,
                "ports": container.attrs.get("NetworkSettings", {}).get("Ports", {}) or {},
            }

        return await asyncio.to_thread(_run)

    async def stop_node(self, node_id: str) -> None:
        """Force-remove the container. Idempotent — missing container is fine."""
        container_name = _container_name(node_id)

        def _stop() -> None:
            try:
                container = self.client.containers.get(container_name)
            except NotFound:
                return
            try:
                container.remove(force=True)
            except APIError as exc:
                raise DockerProvisionerError(
                    f"docker rm -f {container_name} failed: {exc}"
                ) from exc

        await asyncio.to_thread(_stop)

    # ----------------------------------------------------------------- console

    async def exec_console(self, node_id: str) -> tuple[str, str]:
        """Return ``(container_name, shell_path)`` for the xterm.js console.

        Probes the container for a usable shell, trying bash → sh → ash.
        Phase 2 (api/console.py) is responsible for piping
        ``docker exec -it <name> <shell>`` into the WebSocket.
        """
        container_name = _container_name(node_id)

        def _detect() -> tuple[str, str]:
            try:
                container = self.client.containers.get(container_name)
            except NotFound as exc:
                raise DockerProvisionerError(
                    f"container {container_name} not found"
                ) from exc

            for shell in SHELL_FALLBACKS:
                # ``exec_run`` returns (exit_code, output). `test -x` is the
                # cheapest portable probe — works in bash, sh, and ash.
                result = container.exec_run(["test", "-x", shell])
                exit_code = result[0] if isinstance(result, tuple) else result.exit_code
                if exit_code == 0:
                    return container_name, shell

            raise DockerProvisionerError(
                f"no usable shell found in {container_name} "
                f"(tried {', '.join(SHELL_FALLBACKS)})"
            )

        return await asyncio.to_thread(_detect)
