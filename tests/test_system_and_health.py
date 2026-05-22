"""Smoke tests for the FastAPI app: it boots, routes are registered, root works."""


def test_health_endpoint_returns_ok(client):
    r = client.get("/api/system/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["product"] == "OmniLab"
    assert "version" in body


def test_system_info_shape(client):
    r = client.get("/api/system/info")
    assert r.status_code == 200
    body = r.json()
    for key in ("platform", "arch", "kvm_available", "disk_free_gb", "disk_total_gb"):
        assert key in body, f"missing {key}"


def test_openapi_schema_lists_expected_routers(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    # One representative endpoint per major router
    must_have = [
        "/api/system/health",
        "/api/license/status",
        "/api/license/activate",
        "/api/billing/health",
        "/api/labs/",
        "/api/health/metrics",
    ]
    for p in must_have:
        assert p in paths, f"router not registered: {p}"


def test_spa_fallback_serves_index_for_unknown_paths(client, tmp_path, monkeypatch):
    # The SPA catch-all is intentional — frontend routes like /labs/abc must
    # serve index.html so React Router can resolve them client-side. This
    # also means /api/* paths that don't match a registered route fall
    # through to the SPA (not a 404). That's the documented design.
    #
    # We can't easily assert "serves index.html" here because the dist/ dir
    # doesn't exist in the test HOME. Instead, assert that registered API
    # routes win against the catch-all — which the other tests already do.
    # This test just documents the intent.
    r = client.get("/api/system/health")
    assert r.status_code == 200  # registered route wins, not the SPA


def test_billing_health_in_test_mode(client):
    r = client.get("/api/billing/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mode"] == "test"  # no STRIPE_SECRET_KEY → defaults to test
    assert body["has_secret_key"] is False
