"""Tests for the web-UI reverse proxy (CRE-39 phase 3).

The DockerProvisioner is mocked via ``_reset_provisioner_for_tests`` in
``api.web_proxy`` and the actual backend container is replaced by a tiny
in-process aiohttp-free stand-in: we monkeypatch httpx.AsyncClient with a
mock transport so requests "to the container" come back from a fixture.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from api import web_proxy as web_proxy_mod

# --------------------------------------------------------------- fixtures


@pytest.fixture()
def mock_provisioner():
    p = MagicMock()
    p.get_node_address = AsyncMock(return_value="172.20.0.5")
    web_proxy_mod._reset_provisioner_for_tests(p)
    yield p
    web_proxy_mod._reset_provisioner_for_tests(None)


@pytest.fixture()
def mock_httpx(monkeypatch):
    """Replace httpx.AsyncClient with one driven by a MockTransport.

    Tests set ``mock_httpx.responder = callable(request) -> httpx.Response``
    to define the backend's behavior.
    """
    handler = MagicMock()

    def _responder(request: httpx.Request) -> httpx.Response:
        return handler(request)

    transport = httpx.MockTransport(_responder)

    original = httpx.AsyncClient

    class _PatchedClient(original):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            kwargs.pop("verify", None)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _PatchedClient)
    handler.last_request = None

    def default(req):
        handler.last_request = req
        return httpx.Response(200, content=b"hello from container")

    handler.side_effect = default
    return handler


def _create_lab(client) -> str:
    r = client.post("/api/labs/", json={"name": "p3", "description": "", "category": "security"})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _create_running_docker_node(
    client, lab_id: str, *, web_port: int | None = 8080, scheme: str = "http"
) -> str:
    cfg: dict = {}
    if web_port is not None:
        cfg["web_port"] = web_port
        cfg["web_scheme"] = scheme
    body = {
        "lab_id": lab_id,
        "name": "wazuh",
        "type": "docker",
        "image": "wazuh/wazuh-manager:4.7.0",
        "config": cfg,
    }
    r = client.post("/api/nodes/", json=body)
    assert r.status_code in (200, 201), r.text
    node_id = r.json()["id"]
    # Skip the start endpoint (it would call the real provisioner) — just
    # flip the status directly so the proxy treats the node as running.
    import asyncio

    import aiosqlite
    from core.config import settings

    async def _flip():
        async with aiosqlite.connect(str(settings.DB_PATH)) as db:
            await db.execute(
                "UPDATE nodes SET status = 'running' WHERE id = ?", (node_id,)
            )
            await db.commit()

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_flip())
    return node_id


# ---------------------------------------------------- web-info endpoint


def test_web_info_for_node_with_web_port(client, fresh_db):
    lab_id = _create_lab(client)
    node_id = _create_running_docker_node(client, lab_id, web_port=8080)

    r = client.get(f"/api/labs/{lab_id}/nodes/{node_id}/web-info")
    assert r.status_code == 200
    body = r.json()
    assert body["has_web_ui"] is True
    assert body["web_port"] == 8080
    assert body["web_scheme"] == "http"
    assert body["proxy_url"] == f"/labs/{lab_id}/nodes/{node_id}/web/"
    assert body["ws_proxy_url_prefix"] == f"/labs/{lab_id}/nodes/{node_id}/web-ws/"


def test_web_info_for_node_without_web_port(client, fresh_db):
    lab_id = _create_lab(client)
    node_id = _create_running_docker_node(client, lab_id, web_port=None)

    r = client.get(f"/api/labs/{lab_id}/nodes/{node_id}/web-info")
    assert r.status_code == 200
    body = r.json()
    assert body["has_web_ui"] is False
    assert body["web_port"] is None
    assert body["proxy_url"] is None


def test_web_info_404_for_missing_node(client, fresh_db):
    lab_id = _create_lab(client)
    r = client.get(f"/api/labs/{lab_id}/nodes/does-not-exist/web-info")
    assert r.status_code == 404


# --------------------------------------------------------- HTTP proxy


def test_http_proxy_forwards_get_and_returns_body(
    client, fresh_db, mock_provisioner, mock_httpx
):
    lab_id = _create_lab(client)
    node_id = _create_running_docker_node(client, lab_id, web_port=8080)

    r = client.get(f"/labs/{lab_id}/nodes/{node_id}/web/api/v1/dashboard")
    assert r.status_code == 200
    assert r.content == b"hello from container"

    # Provisioner consulted for the IP.
    mock_provisioner.get_node_address.assert_awaited_once_with(node_id, lab_id)
    # Assert on the URL the mock saw.
    last = mock_httpx.call_args.args[0]
    assert str(last.url) == "http://172.20.0.5:8080/api/v1/dashboard"
    assert last.method == "GET"


def test_http_proxy_forwards_post_body_and_query(
    client, fresh_db, mock_provisioner, mock_httpx
):
    lab_id = _create_lab(client)
    node_id = _create_running_docker_node(client, lab_id, web_port=3000)

    captured = {}

    def responder(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["method"] = req.method
        captured["body"] = req.content
        captured["x_custom"] = req.headers.get("x-custom")
        return httpx.Response(201, content=b"created", headers={"x-trace": "abc"})

    mock_httpx.side_effect = responder

    payload = json.dumps({"key": "val"})
    r = client.post(
        f"/labs/{lab_id}/nodes/{node_id}/web/api/items?foo=bar",
        content=payload,
        headers={"content-type": "application/json", "x-custom": "yes"},
    )
    assert r.status_code == 201
    assert r.content == b"created"
    assert r.headers["x-trace"] == "abc"
    assert captured["url"] == "http://172.20.0.5:3000/api/items?foo=bar"
    assert captured["method"] == "POST"
    assert captured["body"] == payload.encode()
    assert captured["x_custom"] == "yes"


def test_http_proxy_strips_hop_by_hop_headers(
    client, fresh_db, mock_provisioner, mock_httpx
):
    """Connection / transfer-encoding must NOT round-trip in either direction."""
    seen_headers = {}

    def responder(req: httpx.Request) -> httpx.Response:
        seen_headers.update({k.lower(): v for k, v in req.headers.items()})
        return httpx.Response(
            200,
            content=b"ok",
            headers={
                "connection": "keep-alive",  # must be stripped from response
                "x-app": "wazuh",  # must round-trip
            },
        )

    mock_httpx.side_effect = responder

    lab_id = _create_lab(client)
    node_id = _create_running_docker_node(client, lab_id, web_port=8080)

    r = client.get(
        f"/labs/{lab_id}/nodes/{node_id}/web/",
        headers={
            "connection": "Keep-Alive-Browser-Marker",
            "proxy-authorization": "should-not-leak",
        },
    )
    assert r.status_code == 200
    # Outbound (browser -> proxy -> container) — browser's hop-by-hop values
    # must not leak through. httpx may set its own Connection header on the
    # outbound side, so we assert on VALUE rather than presence.
    assert seen_headers.get("connection") != "Keep-Alive-Browser-Marker"
    assert "proxy-authorization" not in seen_headers
    # Inbound (container -> proxy -> browser) hop-by-hop strip
    assert "connection" not in {k.lower() for k in r.headers}
    assert r.headers.get("x-app") == "wazuh"


def test_http_proxy_404_for_node_without_web_port(client, fresh_db, mock_provisioner):
    lab_id = _create_lab(client)
    node_id = _create_running_docker_node(client, lab_id, web_port=None)

    r = client.get(f"/labs/{lab_id}/nodes/{node_id}/web/")
    assert r.status_code == 404
    assert "web_port" in r.json()["detail"]


def test_http_proxy_404_for_unknown_node(client, fresh_db, mock_provisioner):
    lab_id = _create_lab(client)
    r = client.get(f"/labs/{lab_id}/nodes/no-such-node/web/")
    assert r.status_code == 404


def test_http_proxy_400_for_non_docker_node(client, fresh_db, mock_provisioner):
    lab_id = _create_lab(client)
    r = client.post(
        "/api/nodes/",
        json={
            "lab_id": lab_id,
            "name": "host",
            "type": "host",
            "config": {"web_port": 8080},
        },
    )
    node_id = r.json()["id"]

    r = client.get(f"/labs/{lab_id}/nodes/{node_id}/web/")
    assert r.status_code == 400
    assert "docker" in r.json()["detail"].lower()


def test_http_proxy_409_for_stopped_node(client, fresh_db, mock_provisioner):
    lab_id = _create_lab(client)
    # Create node but DON'T flip status to running.
    r = client.post(
        "/api/nodes/",
        json={
            "lab_id": lab_id,
            "name": "wazuh",
            "type": "docker",
            "image": "wazuh/wazuh-manager",
            "config": {"web_port": 8080},
        },
    )
    node_id = r.json()["id"]

    r = client.get(f"/labs/{lab_id}/nodes/{node_id}/web/")
    assert r.status_code == 409
    assert "running" in r.json()["detail"].lower()


def test_http_proxy_503_when_provisioner_down(client, fresh_db):
    from services.docker_provisioner import DockerProvisionerError

    lab_id = _create_lab(client)
    node_id = _create_running_docker_node(client, lab_id, web_port=8080)

    original = web_proxy_mod._get_provisioner
    web_proxy_mod._get_provisioner = lambda: (_ for _ in ()).throw(
        DockerProvisionerError("daemon offline")
    )
    try:
        r = client.get(f"/labs/{lab_id}/nodes/{node_id}/web/")
        assert r.status_code == 503
        assert "daemon" in r.json()["detail"].lower()
    finally:
        web_proxy_mod._get_provisioner = original


def test_http_proxy_502_when_container_has_no_ip(client, fresh_db, mock_provisioner):
    """Container exists but not attached to the lab network — return 502, not 500."""
    lab_id = _create_lab(client)
    node_id = _create_running_docker_node(client, lab_id, web_port=8080)

    mock_provisioner.get_node_address.return_value = ""
    r = client.get(f"/labs/{lab_id}/nodes/{node_id}/web/")
    assert r.status_code == 502
    assert "ip" in r.json()["detail"].lower()


def test_http_proxy_supports_https_backend_scheme(
    client, fresh_db, mock_provisioner, mock_httpx
):
    seen = {}

    def responder(req: httpx.Request) -> httpx.Response:
        seen["scheme"] = req.url.scheme
        return httpx.Response(200, content=b"ok")

    mock_httpx.side_effect = responder

    lab_id = _create_lab(client)
    node_id = _create_running_docker_node(client, lab_id, web_port=443, scheme="https")

    r = client.get(f"/labs/{lab_id}/nodes/{node_id}/web/dashboard")
    assert r.status_code == 200
    assert seen["scheme"] == "https"
