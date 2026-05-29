"""
Tests for the AI Lab Builder run-history + cancel features (CRE-47 / AILB-7).

Everything that touches the LLM MOCKS the OpenRouter HTTP seam exactly as
test_agent_runner.py does (monkeypatch ``agent_runner._chat_completion``) — NO
real paid request is ever made.

Coverage:
  1. agent_runs row is created at start (running) and updated to completed
     across a full run, carrying lab_id / tool_call_count / total_tokens.
  2. Cancel: request_cancel sets the flag, the sync loop stops mid-build with a
     terminal ``cancelled`` event, and the partially-built lab is cleaned up.
  3. The cancel registry doesn't leak between runs (unregistered when run ends).
  4. GET /api/agent/runs returns <=10 most-recent rows (newest first).
  5. The run_started event is emitted early carrying the run_id.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile

import pytest
from services import agent_runner

from tests.test_agent_runner import (
    ScriptedLLM,
    _assistant_text,
    _assistant_tool_calls,
    no_docker,  # noqa: F401 — re-exported fixture used by tests below
)
from tests.test_agent_tools import FakeRepo

# ============================================================================
# A temp-file AgentRunStore so run-history tests are fully isolated from the
# session DB.
# ============================================================================

@pytest.fixture()
def run_store():
    from api.agent import AgentRunStore

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("""CREATE TABLE agent_runs (
        id TEXT PRIMARY KEY, prompt TEXT, status TEXT, lab_id TEXT,
        started_at TEXT, completed_at TEXT,
        tool_call_count INTEGER DEFAULT 0, total_tokens INTEGER DEFAULT 0)""")
    conn.commit()
    conn.close()
    yield AgentRunStore(db_path=tmp.name)


# ============================================================================
# 1. Run row lifecycle across a full (mocked) build.
# ============================================================================

def test_agent_runs_row_created_and_updated_across_run(monkeypatch, no_docker, run_store):  # noqa: F811
    repo = FakeRepo()

    def turn_create_lab(_):
        return _assistant_tool_calls(("create_lab", {"name": "Run Lab"}))

    def turn_final(_):
        return _assistant_text("done")

    monkeypatch.setattr(agent_runner, "_chat_completion",
                        ScriptedLLM([turn_create_lab, turn_final]))

    run_id = "run-1"
    run_store.start_run(run_id, "build a lab")
    rows = run_store.recent()
    assert rows[0]["status"] == "running"
    assert rows[0]["completed_at"] is None

    events = list(agent_runner.run_build(repo, "build a lab", run_id=run_id,
                                         api_key="sk-fake"))
    done = events[-1]
    assert done["type"] == "done"

    run_store.finish_run(run_id, "completed", lab_id=done["lab_id"],
                         tool_call_count=done["tool_call_count"],
                         total_tokens=done["total_tokens"])
    row = run_store.recent()[0]
    assert row["status"] == "completed"
    assert row["lab_id"] == done["lab_id"]
    assert row["completed_at"] is not None
    assert row["tool_call_count"] == 1  # exactly one create_lab call


def test_run_started_event_emitted_early(monkeypatch, run_store):
    repo = FakeRepo()
    monkeypatch.setattr(agent_runner, "_chat_completion",
                        ScriptedLLM([lambda _: _assistant_text("nothing to do")]))
    events = list(agent_runner.run_build(repo, "noop", run_id="run-early",
                                         api_key="sk-fake"))
    assert events[0]["type"] == "run_started"
    assert events[0]["run_id"] == "run-early"


# ============================================================================
# 2. Cancel — flag set, loop stops mid-build, partial lab cleaned up.
# ============================================================================

def test_cancel_stops_loop_mid_build_and_cleans_up(monkeypatch, no_docker):  # noqa: F811
    repo = FakeRepo()
    run_id = "run-cancel"

    # Turn 1 asks for create_lab THEN a second create_node in the SAME round.
    # A spy on create_lab sets the cancel flag the instant the lab is built, so
    # the between-tool-call poll fires BEFORE the second tool runs: the lab is
    # already created (and must be torn down) but the build stops mid-round.
    def turn_two_calls(_):
        return _assistant_tool_calls(
            ("create_lab", {"name": "Doomed"}),
            ("create_node", {"lab_id": "x", "name": "r1", "image": "frrouting/frr:latest"}),
        )

    def turn_should_not_run(_):
        raise AssertionError("loop continued after cancel was requested")

    real_create = agent_runner.tools.create_lab

    def spy_create_lab(r, **kw):
        out = real_create(r, **kw)
        agent_runner.request_cancel(run_id)  # cancel the instant the lab exists
        return out

    delete_calls = []
    real_delete = agent_runner.tools.delete_lab

    def spy_delete(r, lab_id):
        delete_calls.append(lab_id)
        return real_delete(r, lab_id)

    patched = dict(agent_runner.tools.TOOLS)
    patched["create_lab"] = spy_create_lab
    monkeypatch.setattr(agent_runner.tools, "TOOLS", patched)
    monkeypatch.setattr(agent_runner.tools, "delete_lab", spy_delete)
    monkeypatch.setattr(agent_runner, "_chat_completion",
                        ScriptedLLM([turn_two_calls, turn_should_not_run]))

    events = list(agent_runner.run_build(repo, "build then cancel",
                                         run_id=run_id, api_key="sk-fake"))

    types = [e["type"] for e in events]
    assert types[-1] == "cancelled"
    assert events[-1]["run_id"] == run_id
    # create_lab ran but create_node did NOT (cancel caught between calls).
    dispatched = [e["name"] for e in events if e["type"] == "tool_call"]
    assert dispatched == ["create_lab"]
    # The partially built lab was torn down (no orphaned containers).
    assert len(delete_calls) == 1
    assert repo.labs == {}


def test_cancel_registry_does_not_leak_between_runs(monkeypatch):
    repo = FakeRepo()

    monkeypatch.setattr(agent_runner, "_chat_completion",
                        ScriptedLLM([lambda _: _assistant_text("done")]))
    list(agent_runner.run_build(repo, "x", run_id="run-leak", api_key="sk-fake"))

    # After the run completes the registry entry must be gone.
    assert "run-leak" not in agent_runner._CANCEL_REGISTRY
    # Cancelling an unknown/finished run is a no-op that reports False.
    assert agent_runner.request_cancel("run-leak") is False


def test_request_cancel_unknown_run_returns_false():
    assert agent_runner.request_cancel("nope-not-registered") is False


# ============================================================================
# 3. recent() returns <=10 most-recent, newest first.
# ============================================================================

def test_recent_returns_at_most_ten_newest_first(run_store):
    # Insert 15 runs with monotonically increasing started_at.
    for i in range(15):
        run_store.start_run(f"run-{i:02d}", f"prompt {i}")
        # Force ordered timestamps so DESC ordering is deterministic.
        with sqlite3.connect(run_store._db_path) as conn:
            conn.execute("UPDATE agent_runs SET started_at = ? WHERE id = ?",
                         (f"2026-05-29T00:00:{i:02d}", f"run-{i:02d}"))
            conn.commit()

    rows = run_store.recent()
    assert len(rows) == 10
    # Newest first: run-14 ... run-05
    assert rows[0]["id"] == "run-14"
    assert rows[-1]["id"] == "run-05"


# ============================================================================
# 4. HTTP surface — /runs, /build/{id}/cancel via the client + overrides.
# ============================================================================

@pytest.fixture()
def overridden(client, run_store):
    from api.agent import get_repo, get_run_store
    from main import app

    fake = FakeRepo()
    app.dependency_overrides[get_repo] = lambda: fake
    app.dependency_overrides[get_run_store] = lambda: run_store
    yield fake, run_store
    app.dependency_overrides.pop(get_repo, None)
    app.dependency_overrides.pop(get_run_store, None)


def test_runs_endpoint_returns_recent(client, overridden):
    _, store = overridden
    store.start_run("api-run-1", "a prompt")
    store.finish_run("api-run-1", "completed", lab_id="lab-xyz",
                     tool_call_count=3, total_tokens=42)

    r = client.get("/api/agent/runs")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    runs = body["data"]["runs"]
    assert len(runs) >= 1
    top = runs[0]
    assert top["id"] == "api-run-1"
    assert top["status"] == "completed"
    assert top["lab_id"] == "lab-xyz"
    assert top["total_tokens"] == 42


def test_cancel_endpoint_unknown_run_is_idempotent(client, overridden):
    r = client.post("/api/agent/build/does-not-exist/cancel")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["cancelled"] is False


def test_build_endpoint_persists_run_row(monkeypatch, client, overridden):
    repo, store = overridden

    def turn_create_lab(_):
        return _assistant_tool_calls(("create_lab", {"name": "SSE Run"}))

    def turn_final(_):
        return _assistant_text("Built SSE Run.")

    monkeypatch.setattr(agent_runner, "_chat_completion",
                        ScriptedLLM([turn_create_lab, turn_final]))
    monkeypatch.setattr(agent_runner, "_load_api_key", lambda: "sk-fake")

    r = client.post("/api/agent/build", json={"prompt": "make a lab"})
    assert r.status_code == 200

    # Parse SSE; first event is run_started, last is done.
    events = []
    for block in r.text.strip().split("\n\n"):
        block = block.strip()
        if block.startswith("data: "):
            events.append(json.loads(block[len("data: "):]))
    assert events[0]["type"] == "run_started"
    run_id = events[0]["run_id"]
    assert events[-1]["type"] == "done"

    row = store.recent()[0]
    assert row["id"] == run_id
    assert row["status"] == "completed"
    assert row["lab_id"] == events[-1]["lab_id"]
