"""Tests for the CRE-39 phase-4 template config + deploy wiring.

Covers:
- Every docker node across all templates has either a default entrypoint or
  an explicit ``command`` so it doesn't exit immediately on start.
- ``docker_options`` are sane: no implicit ``privileged=True``, all
  capability adds are reviewable.
- ``web_port`` values are valid integers when present.
- The deploy endpoint serializes ``docker_options``/``web_port``/``web_scheme``
  into ``nodes.config`` JSON so api/nodes.py and api/web_proxy.py find them.
- ``coming_soon`` templates are listed but cannot be deployed.
"""

from __future__ import annotations

import json

import aiosqlite
import pytest
from api.templates import TEMPLATES, _node_config_payload
from core.config import settings

# --------------------------------------------------------- static catalog


# Images that are safe to NOT need an explicit command — they run a service
# on their default entrypoint (the container won't immediately exit).
_LONG_RUNNING_IMAGES = {
    "wazuh/wazuh-manager:4.7.0",
    "vulnerables/web-dvwa",
    "jasonish/suricata:latest",
    "zeekurity/zeek:latest",
    "strangebee/thehive:5",
    "mitre/caldera:latest",
    "gitea/gitea:latest",
    "jenkins/jenkins:lts",
    "goharbor/harbor-core",
    "registry:2",
    "ollama/ollama:latest",
    "ghcr.io/open-webui/open-webui:main",
    "jupyter/datascience-notebook",
    "ghcr.io/mlflow/mlflow",
    "minio/minio",
}


def test_every_docker_node_either_has_command_or_is_long_running():
    """Avoid the 'container exits on start because the image's default cmd
    is /bin/bash' footgun. Either the image runs a service on its own or we
    explicitly override the command to sleep infinity."""
    offenders = []
    for tmpl_id, tmpl in TEMPLATES.items():
        if tmpl.get("coming_soon"):
            continue
        for node in tmpl["nodes"]:
            if node["type"] != "docker":
                continue
            image = node.get("image")
            opts = node.get("docker_options") or {}
            if image in _LONG_RUNNING_IMAGES:
                continue
            if "command" in opts and opts["command"]:
                continue
            offenders.append(f"{tmpl_id}.{node['name']} (image={image})")
    assert not offenders, (
        "These docker nodes have no command override but their image isn't in "
        "the long-running set — they'll exit on start:\n  " + "\n  ".join(offenders)
    )


def test_no_template_uses_privileged_true():
    """Privileged containers are the docker equivalent of running as root —
    every template must justify capability needs via cap_add, not privileged."""
    offenders = []
    for tmpl_id, tmpl in TEMPLATES.items():
        for node in tmpl["nodes"]:
            opts = node.get("docker_options") or {}
            if opts.get("privileged"):
                offenders.append(f"{tmpl_id}.{node['name']}")
    assert not offenders, f"Privileged containers must be justified: {offenders}"


def test_capability_additions_are_in_the_allowed_set():
    """Audit gate — every cap_add across all templates must be in the
    reviewed allow-list. Adding a new cap requires editing this set."""
    ALLOWED = {"NET_ADMIN", "NET_RAW", "SYS_NICE"}
    for tmpl_id, tmpl in TEMPLATES.items():
        for node in tmpl["nodes"]:
            caps = (node.get("docker_options") or {}).get("cap_add") or []
            for cap in caps:
                assert cap in ALLOWED, (
                    f"{tmpl_id}.{node['name']} requests capability {cap!r} "
                    f"not in audited allow-list {ALLOWED}"
                )


def test_web_port_values_are_valid_when_present():
    for tmpl_id, tmpl in TEMPLATES.items():
        for node in tmpl["nodes"]:
            if "web_port" in node:
                port = node["web_port"]
                assert isinstance(port, int), f"{tmpl_id}.{node['name']} web_port not int"
                assert 1 <= port <= 65535, (
                    f"{tmpl_id}.{node['name']} web_port {port} out of range"
                )
                scheme = node.get("web_scheme", "http")
                assert scheme in ("http", "https"), (
                    f"{tmpl_id}.{node['name']} web_scheme={scheme!r} not http/https"
                )


def test_coming_soon_templates_are_flagged_and_no_other_template_is():
    """The two QEMU-based templates are flagged; everything else must NOT
    be flagged or beta users will see incorrect Pro labels."""
    flagged = {tid for tid, t in TEMPLATES.items() if t.get("coming_soon")}
    assert flagged == {"kubernetes-cluster", "vyos-routing"}, (
        f"coming_soon set drift: {flagged}"
    )


# --------------------------------------------- _node_config_payload helper


def test_node_config_payload_includes_relevant_keys():
    node = {
        "name": "x",
        "type": "docker",
        "image": "alpine",
        "x": 0,
        "y": 0,
        "docker_options": {"cap_add": ["NET_ADMIN"]},
        "web_port": 8080,
        "web_scheme": "http",
    }
    payload = _node_config_payload(node)
    assert payload == {
        "docker_options": {"cap_add": ["NET_ADMIN"]},
        "web_port": 8080,
        "web_scheme": "http",
    }


def test_node_config_payload_skips_missing_and_none():
    node = {
        "name": "x",
        "type": "docker",
        "image": "alpine",
        "x": 0,
        "y": 0,
        "docker_options": None,
    }
    assert _node_config_payload(node) == {}


# --------------------------------------------- /deploy persists config JSON


def _read_node_config(node_id: str) -> dict:
    """Pull the nodes.config JSON column for a node, parsed."""
    import asyncio

    async def _q():
        async with aiosqlite.connect(str(settings.DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT config FROM nodes WHERE id = ?", (node_id,)
            ) as cur:
                row = await cur.fetchone()
            return json.loads(row["config"] or "{}")

    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_q())


def test_deploy_persists_docker_options_into_nodes_config(client, fresh_db):
    """End-to-end: deploy pentest-lab → kali node has cap_add in config JSON."""
    r = client.post("/api/templates/pentest-lab/deploy")
    assert r.status_code == 200, r.text
    lab_id = r.json()["lab_id"]

    # Find the kali node row via direct DB query.
    import asyncio

    async def _find_kali():
        async with aiosqlite.connect(str(settings.DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id FROM nodes WHERE lab_id = ? AND name = 'kali'",
                (lab_id,),
            ) as cur:
                row = await cur.fetchone()
            return row["id"] if row else None

    kali_id = (
        asyncio.get_event_loop_policy()
        .new_event_loop()
        .run_until_complete(_find_kali())
    )
    assert kali_id is not None
    cfg = _read_node_config(kali_id)
    assert cfg["docker_options"]["cap_add"] == ["NET_ADMIN", "NET_RAW"]
    # kali-rolling is the slim variant — pentest-lab installs nmap + friends
    # via an apt-get one-liner on first boot. Assert the shape, not the
    # exact apt args (they'll churn).
    cmd = cfg["docker_options"]["command"]
    assert cmd[0] == "bash" and cmd[1] == "-c"
    assert "apt-get install" in cmd[2]
    assert "nmap" in cmd[2]
    assert "sleep infinity" in cmd[2]


def test_deploy_persists_web_port_into_nodes_config(client, fresh_db):
    """End-to-end: deploy cicd-pipeline → jenkins node has web_port=8080 in config."""
    r = client.post("/api/templates/cicd-pipeline/deploy")
    assert r.status_code == 200
    lab_id = r.json()["lab_id"]

    import asyncio

    async def _find_jenkins():
        async with aiosqlite.connect(str(settings.DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id FROM nodes WHERE lab_id = ? AND name = 'jenkins'",
                (lab_id,),
            ) as cur:
                row = await cur.fetchone()
            return row["id"]

    jenkins_id = (
        asyncio.get_event_loop_policy()
        .new_event_loop()
        .run_until_complete(_find_jenkins())
    )
    cfg = _read_node_config(jenkins_id)
    assert cfg["web_port"] == 8080
    # web_scheme omitted at template-definition time = default 'http' at read time
    assert cfg.get("web_scheme", "http") == "http"


def test_deploy_persists_https_scheme_for_wazuh(client, fresh_db):
    r = client.post("/api/templates/wazuh-soc/deploy")
    assert r.status_code == 200
    lab_id = r.json()["lab_id"]

    import asyncio

    async def _find():
        async with aiosqlite.connect(str(settings.DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id FROM nodes WHERE lab_id = ? AND name = 'wazuh-manager'",
                (lab_id,),
            ) as cur:
                row = await cur.fetchone()
            return row["id"]

    wazuh_id = (
        asyncio.get_event_loop_policy()
        .new_event_loop()
        .run_until_complete(_find())
    )
    cfg = _read_node_config(wazuh_id)
    assert cfg["web_port"] == 443
    assert cfg["web_scheme"] == "https"


def test_deploy_rejects_coming_soon_template(client, fresh_db):
    r = client.post("/api/templates/kubernetes-cluster/deploy")
    assert r.status_code == 400
    assert "coming soon" in r.json()["detail"].lower()


def test_deploy_rejects_unknown_template(client, fresh_db):
    r = client.post("/api/templates/does-not-exist/deploy")
    assert r.status_code == 404


def test_list_templates_still_includes_coming_soon():
    """The UI surfaces them as Pro/Coming Soon, so they must be listed —
    just not deployable."""
    # Direct dict access since this is a static catalog test.
    assert "kubernetes-cluster" in TEMPLATES
    assert "vyos-routing" in TEMPLATES
    assert TEMPLATES["kubernetes-cluster"]["coming_soon"] is True
    assert TEMPLATES["vyos-routing"]["coming_soon"] is True


def test_list_templates_endpoint_includes_all_categories(client, fresh_db):
    r = client.get("/api/templates/")
    assert r.status_code == 200
    items = r.json()
    ids = {t["id"] for t in items}
    # 10 templates total (8 deployable + 2 coming-soon)
    assert len(ids) == 10
    assert "kubernetes-cluster" in ids
    assert "pentest-lab" in ids
