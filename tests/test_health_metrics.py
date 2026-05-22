"""Health/metrics router: smoke + structural assertions.

The CRE-7 regression we fixed (lab-stats 500 schema mismatch) gets a guard
test so the schema can't silently drift again.
"""


def test_metrics_returns_either_stats_or_degraded(client):
    r = client.get("/api/health/metrics")
    assert r.status_code == 200
    body = r.json()
    # Either psutil is present (full payload) or it returned the degraded
    # fallback. Both must answer the "is the API up?" question.
    assert "version" in body
    assert body.get("api_healthy") is True


def test_lab_stats_schema_does_not_500(client):
    """Regression guard for CRE-7."""
    r = client.get("/api/health/lab-stats")
    assert r.status_code == 200, r.text
    body = r.json()
    for k in ("total_labs", "active_labs", "total_nodes", "running_nodes",
              "stopped_nodes", "by_category"):
        assert k in body, f"missing key: {k}"
    assert isinstance(body["by_category"], dict)


def test_network_info_shape(client):
    r = client.get("/api/health/network")
    assert r.status_code == 200
    body = r.json()
    assert "bridges" in body
    assert isinstance(body["bridges"], list)


def test_docker_endpoint_degrades_gracefully(client):
    r = client.get("/api/health/docker")
    assert r.status_code == 200
    body = r.json()
    # Either docker is reachable or we get a clean error stub.
    assert "containers_running" in body
    assert "images_count" in body
