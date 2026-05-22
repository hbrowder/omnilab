"""Labs router: CRUD, export, import roundtrip.

Uses the `fresh_db` fixture to make assertions about counts deterministic.
"""


def test_list_labs_initially_empty_after_wipe(client, fresh_db):
    r = client.get("/api/labs/")
    assert r.status_code == 200
    assert r.json() == []


def test_create_then_get_lab(client, fresh_db):
    r = client.post("/api/labs/", json={"name": "demo", "description": "x", "category": "security"})
    assert r.status_code in (200, 201)
    lab = r.json()
    lab_id = lab["id"]
    assert lab["name"] == "demo"

    g = client.get(f"/api/labs/{lab_id}")
    assert g.status_code == 200
    assert g.json()["name"] == "demo"


def test_get_lab_404_for_unknown_id(client):
    r = client.get("/api/labs/does-not-exist-uuid")
    assert r.status_code == 404


def test_delete_lab(client, fresh_db):
    lab_id = client.post("/api/labs/", json={"name": "del", "category": "general"}).json()["id"]
    r = client.delete(f"/api/labs/{lab_id}")
    assert r.status_code in (200, 204)
    assert client.get(f"/api/labs/{lab_id}").status_code == 404


def test_import_roundtrip_security_stack_seed(client, fresh_db):
    """The seed JSON we shipped with CRE-26 must import cleanly against the
    real schema. This test is the smoke check the demo-prep README promises."""
    import json
    from pathlib import Path

    seed_path = Path(__file__).resolve().parent.parent / "docs/demo-assets/seed-labs/security-stack.json"
    payload = json.loads(seed_path.read_text())

    r = client.post("/api/labs/import", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["imported_nodes"] == 3
    assert body["imported_links"] == 3

    lab_id = body["id"]
    topo = client.get(f"/api/labs/{lab_id}/topology").json()
    assert len(topo["nodes"]) == 3
    assert len(topo["links"]) == 3


def test_import_rejects_wrong_schema_version(client, fresh_db):
    r = client.post("/api/labs/import", json={
        "schema_version": 99,
        "product": "OmniLab",
        "lab": {"name": "bad"},
        "nodes": [],
        "links": [],
    })
    assert r.status_code == 400


def test_import_name_collision_appends_suffix(client, fresh_db):
    payload = {
        "schema_version": 1,
        "product": "OmniLab",
        "lab": {"name": "Collision Lab"},
        "nodes": [],
        "links": [],
    }
    a = client.post("/api/labs/import", json=payload).json()
    b = client.post("/api/labs/import", json=payload).json()
    assert a["name"] == "Collision Lab"
    assert b["name"] == "Collision Lab (2)"
