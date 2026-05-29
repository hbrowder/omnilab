"""AI Lab Builder demo-scenario tests (CRE-48 / AILB-8).

Two layers, mirroring the rest of the agent test suite:

  1. Always-on dataset validation (NO docker, NO LLM, runs in the default
     suite). Loads ``agent_scenarios.json`` and asserts its shape AND — the
     important part — that every image each scenario expects is actually present
     in ``list_inventory`` on a clean install. This is the regression guard for
     the FRR/k3s inventory gap fixed in CRE-48: if someone removes
     ``_AGENT_CATALOG`` from api/agent.py, ``test_dataset_images_are_in_inventory``
     goes red instead of the failure surfacing only at demo time.

  2. An opt-in end-to-end test (``@pytest.mark.integration``) that runs each
     scenario through the REAL LLM loop against the REAL sqlite Repo, and for the
     lightweight scenarios actually boots the containers against real docker and
     asserts a node reaches ``running``. It is triple-gated — a real
     ``OPENROUTER_API_KEY``, a reachable docker daemon, AND ``AILB_RUN_SCENARIOS=1``
     — because a full run pulls images on demand (kali, dvwa, k3s, wazuh …) and
     makes real paid LLM calls. FRR is pre-pulled in the dev environment.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_SCENARIOS_PATH = Path(__file__).resolve().parent / "agent_scenarios.json"

_REQUIRED_KEYS = {
    "id", "title", "prompt", "images",
    "min_nodes", "max_nodes", "expect_links", "verify_start",
}


def _load() -> list[dict]:
    data = json.loads(_SCENARIOS_PATH.read_text(encoding="utf-8"))
    return data["scenarios"]


SCENARIOS = _load()


# ============================================================================
# Layer 1 — always-on dataset validation (default suite, no docker, no LLM)
# ============================================================================

def test_dataset_loads_six_scenarios():
    assert len(SCENARIOS) == 6, "CRE-48 specifies exactly 6 demo scenarios"
    ids = [s["id"] for s in SCENARIOS]
    assert len(ids) == len(set(ids)), f"scenario ids must be unique: {ids}"


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["id"])
def test_scenario_schema_is_valid(scenario):
    missing = _REQUIRED_KEYS - scenario.keys()
    assert not missing, f"{scenario.get('id')} missing keys: {missing}"
    assert scenario["prompt"].strip(), "prompt must be non-empty"
    assert scenario["title"].strip(), "title must be non-empty"
    assert isinstance(scenario["images"], list) and scenario["images"], \
        "images must be a non-empty list"
    assert isinstance(scenario["expect_links"], bool)
    assert isinstance(scenario["verify_start"], bool)
    assert 1 <= scenario["min_nodes"] <= scenario["max_nodes"], \
        "min_nodes must be >=1 and <= max_nodes"


def test_dataset_images_are_in_inventory():
    """Every image every scenario expects MUST be buildable on a clean install.

    This is the guard that keeps the OSPF/BGP (FRR) and Kubernetes (k3s)
    scenarios honest — create_node rejects any image not in list_inventory, so a
    scenario referencing an absent image could never pass acceptance.
    """
    from api.agent import SqliteRepo

    available = {i["image"] for i in SqliteRepo().inventory()["images"]}
    for scenario in SCENARIOS:
        for image in scenario["images"]:
            assert image in available, (
                f"scenario {scenario['id']!r} expects image {image!r} which is "
                f"not in list_inventory; add it to _AGENT_CATALOG (api/agent.py) "
                f"or a template. Available: {sorted(available)}"
            )


# ============================================================================
# Layer 2 — opt-in real end-to-end build (LLM + docker)
# ============================================================================

_RUN_E2E = os.environ.get("AILB_RUN_SCENARIOS") == "1"
_HAVE_KEY = bool(os.environ.get("OPENROUTER_API_KEY"))


def _docker_available() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


_E2E_REASON = (
    "scenario e2e is opt-in: set AILB_RUN_SCENARIOS=1, OPENROUTER_API_KEY, and "
    "ensure a docker daemon is reachable (pulls images + makes paid LLM calls)"
)


@pytest.mark.integration
@pytest.mark.skipif(
    not (_RUN_E2E and _HAVE_KEY and _docker_available()), reason=_E2E_REASON
)
@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["id"])
def test_scenario_builds_end_to_end(scenario):
    """Drive the real agent loop for one scenario; assert the topology it builds
    matches the scenario's expected shape, and (for verify_start scenarios) that
    at least one node actually boots. Always tears the lab down afterwards."""
    from api.agent import SqliteRepo
    from services import agent_runner
    from services import agent_tools as tools

    repo = SqliteRepo()
    created_lab_id = None
    try:
        events = list(agent_runner.run_build(
            repo, scenario["prompt"],
            model="anthropic/claude-3.5-haiku",
            max_iterations=30,
        ))
        assert events, "the runner yielded no events"
        terminal = events[-1]
        assert terminal["type"] == "done", (
            f"{scenario['id']} did not complete cleanly: {terminal}"
        )

        created_lab_id = terminal.get("lab_id")
        assert created_lab_id, f"{scenario['id']} produced no lab_id"

        state = repo.lab_state(created_lab_id)
        n = state["node_count"]
        assert scenario["min_nodes"] <= n <= scenario["max_nodes"], (
            f"{scenario['id']} built {n} nodes, expected "
            f"{scenario['min_nodes']}..{scenario['max_nodes']}"
        )
        if scenario["expect_links"]:
            assert state["link_count"] >= 1, f"{scenario['id']} created no links"

        if scenario["verify_start"]:
            running = [node for node in state["nodes"]
                       if node.get("state") == "running"]
            assert running, (
                f"{scenario['id']} started no nodes (states: "
                f"{[node.get('state') for node in state['nodes']]})"
            )
    finally:
        if created_lab_id:
            try:
                tools.delete_lab(repo, created_lab_id)
            except Exception:
                pass
