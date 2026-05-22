"""License system tests — key gen, verify, activate/deactivate, free-tier limits.

Covers the most security-sensitive module in the backend: anyone who can
forge a valid OMNI-XXXX key gets the Pro feature set. The verifier MUST
reject tampered keys.
"""
import pytest


def test_generate_then_verify_roundtrip():
    from api.license import generate_key, verify_key
    key = generate_key("pro", "user")
    assert key.startswith("OMNI-")
    info = verify_key(key)
    assert info == {"plan": "pro", "customer": "user"}


def test_generate_format_is_dashed_groups():
    from api.license import generate_key
    key = generate_key("free", "user")
    # Format: OMNI-XXXX-XXXX-XXXX-XXXX → 5 dashed segments
    assert key.count("-") == 4
    body = key.split("-", 1)[1]
    parts = body.split("-")
    assert len(parts) == 4
    assert all(len(p) == 4 for p in parts)


@pytest.mark.parametrize("bad", [
    "",
    "NOTAKEY",
    "OMNI-",
    "OMNI-AAAA-BBBB-CCCC-DDDD",  # right shape, wrong signature
    "OMNI-AAAA-BBBB-CCCC",       # too short
    "FAKE-AAAA-BBBB-CCCC-DDDD",  # wrong prefix
])
def test_verify_rejects_garbage(bad):
    from api.license import verify_key
    assert verify_key(bad) is None


def test_verify_rejects_tampered_key():
    """Flip a single character of a valid key — it must fail."""
    from api.license import generate_key, verify_key
    key = generate_key("pro", "user")
    # Swap the 8th char of the signature body
    body = key[5:].replace("-", "")
    swapped = "Z" if body[7] != "Z" else "A"
    tampered_body = body[:7] + swapped + body[8:]
    tampered_key = "OMNI-" + "-".join(tampered_body[i:i+4] for i in range(0, 16, 4))
    assert verify_key(tampered_key) is None


def test_status_endpoint_defaults_to_free(client, clean_license):
    r = client.get("/api/license/status")
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "free"
    assert body["activated"] is False
    assert body["limits"]["max_nodes"] > 0  # free tier has a finite limit
    assert body["features"]["multi_lab"] is False


def test_activate_with_valid_key_flips_to_pro(client, clean_license):
    # Mint a key with the same secret the running app uses
    from api.license import generate_key
    key = generate_key("pro", "user")
    r = client.post("/api/license/activate", json={"key": key})
    assert r.status_code == 200, r.text
    assert r.json()["plan"] == "pro"

    # Status should now reflect activation
    s = client.get("/api/license/status").json()
    assert s["plan"] == "pro"
    assert s["activated"] is True
    assert s["features"]["unlimited_nodes"] is True
    assert s["limits"]["max_nodes"] == -1  # unlimited sentinel


def test_activate_rejects_invalid_key(client, clean_license):
    r = client.post("/api/license/activate", json={"key": "OMNI-FAKE-FAKE-FAKE-FAKE"})
    assert r.status_code == 400


def test_deactivate_reverts_to_free(client, clean_license):
    from api.license import generate_key
    client.post("/api/license/activate", json={"key": generate_key("pro", "user")})
    r = client.post("/api/license/deactivate")
    assert r.status_code == 200
    assert r.json()["plan"] == "free"
    assert client.get("/api/license/status").json()["activated"] is False


def test_check_tier_limit_blocks_at_free_node_cap(clean_license):
    from api.license import FREE_TIER_NODES, check_tier_limit
    assert check_tier_limit(0, "nodes") is True
    assert check_tier_limit(FREE_TIER_NODES - 1, "nodes") is True
    assert check_tier_limit(FREE_TIER_NODES, "nodes") is False
    assert check_tier_limit(FREE_TIER_NODES + 10, "nodes") is False


def test_check_tier_limit_unblocks_on_pro(client, clean_license):
    from api.license import FREE_TIER_NODES, check_tier_limit, generate_key
    client.post("/api/license/activate", json={"key": generate_key("pro", "user")})
    # Pro tier ignores the free cap
    assert check_tier_limit(FREE_TIER_NODES + 100, "nodes") is True
    assert check_tier_limit(FREE_TIER_NODES + 100, "labs") is True


def test_generate_endpoint_rejects_unknown_plan(client):
    r = client.post("/api/license/generate?plan=enterprise-plus")
    assert r.status_code == 400


def test_generate_endpoint_happy_path(client):
    r = client.post("/api/license/generate?plan=pro&customer=user")
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "pro"
    assert body["key"].startswith("OMNI-")
