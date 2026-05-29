"""
Tests for the AI Lab Builder LLM loop (CRE-44).

Every unit test MOCKS the OpenRouter HTTP call (monkeypatching the runner's
``_chat_completion`` seam) so NO real paid request is ever made. The scripted
sequence reproduces the CRE-41 §7 OSPF worked trace.

Layers:
  1. A scripted full OSPF build: assert tool dispatch order, a lab was built,
     the ``done`` event carries the lab_id.
  2. Cost rails: max_iterations exceeded -> error event (no infinite loop);
     the outgoing request carries max_tokens (default 4096); delete_lab is
     invoked on unrecoverable mid-build error; the API key is REDACTED.
  3. The SSE endpoint via the client fixture + dependency_overrides[get_repo].
  4. An integration test gated on a real OPENROUTER_API_KEY (SKIPs here).
"""
from __future__ import annotations

import json
import os

import pytest
from services import agent_runner

# Reuse the in-memory fake Repo from the tool-layer tests.
from tests.test_agent_tools import FakeRepo


@pytest.fixture()
def no_docker(monkeypatch):
    """Replace the docker-touching lifecycle tools with pure fakes so unit
    tests NEVER start a real container, even when a docker daemon is present.

    The runner dispatches via ``agent_tools.TOOLS[name]``, so patching that
    dict is enough. We keep the same envelope shapes the real tools return."""
    from services import agent_tools as t

    def fake_start(repo, node_id):
        repo.set_node_status(node_id, "running")
        return t.ok({"node_id": node_id, "state": "running"})

    def fake_stop(repo, node_id):
        repo.set_node_status(node_id, "stopped")
        return t.ok({"node_id": node_id, "state": "stopped"})

    patched = dict(t.TOOLS)
    patched["start_node"] = fake_start
    patched["stop_node"] = fake_stop
    monkeypatch.setattr(t, "TOOLS", patched)
    return patched


# ============================================================================
# Scripted-completion helpers — emulate OpenRouter /chat/completions responses.
# ============================================================================

def _assistant_tool_calls(*calls: tuple[str, dict]) -> dict:
    """Build an OpenRouter response whose assistant message requests tools."""
    tool_calls = []
    for i, (name, args) in enumerate(calls):
        tool_calls.append({
            "id": f"call_{name}_{i}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)},
        })
    return {"choices": [{"message": {"role": "assistant", "content": None,
                                     "tool_calls": tool_calls}}]}


def _assistant_text(text: str) -> dict:
    """A final, tool-call-free assistant message (the model is done)."""
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


class ScriptedLLM:
    """Replays a fixed list of completions; records every outgoing request.

    Because args (esp. lab_id / node_id) are only known at runtime, the script
    is a list of callables that receive the recorded messages-so-far OR a plain
    dict completion. Simpler: each entry is a callable(repo_state) -> completion.
    Here we build the script lazily inside each test using closures.
    """

    def __init__(self, script):
        self._script = list(script)
        self.calls = []  # recorded kwargs passed to _chat_completion

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        step = self._script.pop(0)
        return step(kwargs) if callable(step) else step


# ============================================================================
# 1. Full OSPF build (CRE-41 §7 trace), scripted.
# ============================================================================

def test_full_ospf_build_dispatch_order(monkeypatch, no_docker):
    repo = FakeRepo()
    img = "frrouting/frr:latest"

    # The model can't know ids up front, so each scripted turn reads the live
    # repo state (created lab + node ids) to construct the next tool args.
    def turn_inventory(_):
        return _assistant_tool_calls(("list_inventory", {}))

    def turn_create_lab(_):
        return _assistant_tool_calls(("create_lab", {"name": "OSPF Areas 0/1",
                                                      "description": "area 0 + area 1"}))

    def turn_create_nodes(_):
        lab_id = next(iter(repo.labs))
        return _assistant_tool_calls(
            ("create_node", {"lab_id": lab_id, "name": "r1", "image": img}),
            ("create_node", {"lab_id": lab_id, "name": "r2", "image": img}),
            ("create_node", {"lab_id": lab_id, "name": "r3", "image": img}),
            ("create_node", {"lab_id": lab_id, "name": "r4", "image": img}),
        )

    def turn_links(_):
        lab_id = next(iter(repo.labs))
        ids = {n["name"]: nid for nid, n in repo.nodes.items()}
        return _assistant_tool_calls(
            ("link_nodes", {"lab_id": lab_id, "a": {"node_id": ids["r1"]},
                            "b": {"node_id": ids["r2"]}}),
            ("link_nodes", {"lab_id": lab_id, "a": {"node_id": ids["r2"]},
                            "b": {"node_id": ids["r3"]}}),
            ("link_nodes", {"lab_id": lab_id, "a": {"node_id": ids["r3"]},
                            "b": {"node_id": ids["r4"]}}),
        )

    def turn_push_config(_):
        ids = {n["name"]: nid for nid, n in repo.nodes.items()}
        return _assistant_tool_calls(
            *[("push_config", {"node_id": ids[r], "config_text": f"<frr {r}>",
                               "mode": "startup"}) for r in ("r1", "r2", "r3", "r4")]
        )

    def turn_start(_):
        ids = {n["name"]: nid for nid, n in repo.nodes.items()}
        return _assistant_tool_calls(
            *[("start_node", {"node_id": ids[r]}) for r in ("r1", "r2", "r3", "r4")]
        )

    def turn_poll(_):
        ids = {n["name"]: nid for nid, n in repo.nodes.items()}
        return _assistant_tool_calls(
            *[("get_node_state", {"node_id": ids[r]}) for r in ("r1", "r2", "r3", "r4")]
        )

    def turn_lab_state(_):
        lab_id = next(iter(repo.labs))
        return _assistant_tool_calls(("get_lab_state", {"lab_id": lab_id}))

    def turn_final(_):
        return _assistant_text("Built OSPF Areas 0/1: 4 routers, 3 links, all running.")

    llm = ScriptedLLM([turn_inventory, turn_create_lab, turn_create_nodes,
                       turn_links, turn_push_config, turn_start, turn_poll,
                       turn_lab_state, turn_final])
    monkeypatch.setattr(agent_runner, "_chat_completion", llm)

    events = list(agent_runner.run_build(repo, "build me an OSPF area 0/1 lab "
                                         "with 4 routers", api_key="sk-fake"))

    types = [e["type"] for e in events]
    assert types[-1] == "done"

    dispatched = [e["name"] for e in events if e["type"] == "tool_call"]
    assert dispatched == [
        "list_inventory", "create_lab",
        "create_node", "create_node", "create_node", "create_node",
        "link_nodes", "link_nodes", "link_nodes",
        "push_config", "push_config", "push_config", "push_config",
        "start_node", "start_node", "start_node", "start_node",
        "get_node_state", "get_node_state", "get_node_state", "get_node_state",
        "get_lab_state",
    ]

    # A lab was actually built through the repo.
    assert len(repo.labs) == 1
    assert len(repo.nodes) == 4
    assert len(repo.links) == 3
    assert all(n["state"] == "running" for n in repo.nodes.values())

    # The done event carries the created lab_id.
    done = events[-1]
    assert done["lab_id"] == next(iter(repo.labs))
    assert "OSPF" in done["summary"]


# ============================================================================
# 2. Cost rails
# ============================================================================

def test_max_iterations_exceeded_emits_error_no_infinite_loop(monkeypatch):
    repo = FakeRepo()

    # The model NEVER finishes — it keeps asking for list_inventory forever.
    def always_tool(_):
        return _assistant_tool_calls(("list_inventory", {}))

    monkeypatch.setattr(agent_runner, "_chat_completion",
                        ScriptedLLM([always_tool] * 1000))

    events = list(agent_runner.run_build(repo, "loop forever",
                                         max_iterations=3, api_key="sk-fake"))
    # Stops (no infinite loop) and the terminal event is an error.
    assert events[-1]["type"] == "error"
    assert "max_iterations" in events[-1]["message"]
    # Exactly the capped number of LLM calls were made.
    n_calls = sum(1 for e in events if e["type"] == "tool_call")
    assert n_calls == 3


def test_request_carries_default_max_tokens(monkeypatch):
    repo = FakeRepo()
    llm = ScriptedLLM([lambda _: _assistant_text("done, no tools needed")])
    monkeypatch.setattr(agent_runner, "_chat_completion", llm)

    list(agent_runner.run_build(repo, "noop", api_key="sk-fake"))

    assert llm.calls, "expected at least one LLM request"
    assert llm.calls[0]["max_tokens"] == 4096
    assert llm.calls[0]["max_tokens"] != 32000


def test_request_max_tokens_passes_through_to_payload(monkeypatch):
    """The real _chat_completion must put max_tokens into the POST body."""
    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return _assistant_text("ok")

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: A002
        captured["json"] = json
        captured["headers"] = headers
        return _Resp()

    monkeypatch.setattr(agent_runner.httpx, "post", fake_post)
    out = agent_runner._chat_completion(
        api_key="sk-secret", model="m", messages=[], tools_schema=[],
        max_tokens=4096)
    assert out  # parsed
    assert captured["json"]["max_tokens"] == 4096
    assert captured["headers"]["Authorization"] == "Bearer sk-secret"


def test_delete_lab_invoked_on_unrecoverable_error(monkeypatch):
    repo = FakeRepo()

    # Turn 1: create the lab. Turn 2: the LLM HTTP call blows up unrecoverably.
    def turn_create_lab(_):
        return _assistant_tool_calls(("create_lab", {"name": "Doomed"}))

    def turn_explode(_):
        raise agent_runner.httpx.ConnectError("boom")

    monkeypatch.setattr(agent_runner, "_chat_completion",
                        ScriptedLLM([turn_create_lab, turn_explode]))

    delete_calls = []
    real_delete = agent_runner.tools.delete_lab

    def spy_delete(r, lab_id):
        delete_calls.append(lab_id)
        return real_delete(r, lab_id)

    monkeypatch.setattr(agent_runner.tools, "delete_lab", spy_delete)

    events = list(agent_runner.run_build(repo, "build then fail", api_key="sk-fake"))

    assert events[-1]["type"] == "error"
    # The lab the agent created was torn down.
    assert len(delete_calls) == 1
    assert repo.labs == {}  # delete_lab removed it


def test_api_key_is_redacted_in_error_output(monkeypatch):
    repo = FakeRepo()
    secret = "sk-or-SUPERSECRETKEY-123456"

    # The HTTP layer raises an error that embeds the key (worst case).
    def turn_leaky(_):
        raise agent_runner.httpx.HTTPError(f"401 unauthorized for Bearer {secret}")

    monkeypatch.setattr(agent_runner, "_chat_completion",
                        ScriptedLLM([turn_leaky]))

    events = list(agent_runner.run_build(repo, "x", api_key=secret))
    err_event = events[-1]
    assert err_event["type"] == "error"
    # The key string must NEVER appear in client-facing output.
    assert secret not in err_event["message"]
    assert "REDACTED" in err_event["message"]


def test_total_tool_call_cap(monkeypatch):
    repo = FakeRepo()

    def many_calls(_):
        # One turn asking for many tool calls at once.
        return _assistant_tool_calls(*[("list_inventory", {})] * 10)

    monkeypatch.setattr(agent_runner, "_chat_completion",
                        ScriptedLLM([many_calls] * 100))

    events = list(agent_runner.run_build(
        repo, "spam tools", max_tool_calls=5, max_iterations=50,
        api_key="sk-fake"))
    assert events[-1]["type"] == "error"
    dispatched = sum(1 for e in events if e["type"] == "tool_call")
    assert dispatched <= 5


def test_missing_api_key_yields_error(monkeypatch):
    repo = FakeRepo()
    monkeypatch.setattr(agent_runner, "_load_api_key", lambda: None)
    events = list(agent_runner.run_build(repo, "x"))
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "OPENROUTER_API_KEY" in events[0]["message"]


# ============================================================================
# 3. tools schema sanity
# ============================================================================

def test_tools_schema_covers_every_registered_tool():
    from services import agent_tools as tools

    schema = agent_runner.build_tools_schema()
    names = {s["function"]["name"] for s in schema}
    assert names == set(tools.TOOLS)
    for s in schema:
        assert s["type"] == "function"
        assert "parameters" in s["function"]
        assert s["function"]["parameters"]["type"] == "object"


# ============================================================================
# 4. SSE endpoint
# ============================================================================

@pytest.fixture()
def build_repo(client):
    from api.agent import get_repo
    from main import app

    fake = FakeRepo()
    app.dependency_overrides[get_repo] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_repo, None)


def _parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.strip().split("\n\n"):
        block = block.strip()
        if block.startswith("data: "):
            events.append(json.loads(block[len("data: "):]))
    return events


def test_sse_endpoint_streams_events(monkeypatch, client, build_repo):
    img = "frrouting/frr:latest"

    def turn_inventory(_):
        return _assistant_tool_calls(("list_inventory", {}))

    def turn_create_lab(_):
        return _assistant_tool_calls(("create_lab", {"name": "SSE Lab"}))

    def turn_node(_):
        lab_id = next(iter(build_repo.labs))
        return _assistant_tool_calls(
            ("create_node", {"lab_id": lab_id, "name": "r1", "image": img}))

    def turn_final(_):
        return _assistant_text("Done: SSE Lab with 1 node.")

    monkeypatch.setattr(agent_runner, "_chat_completion",
                        ScriptedLLM([turn_inventory, turn_create_lab,
                                     turn_node, turn_final]))
    # Make sure a key is "present" so the loop runs.
    monkeypatch.setattr(agent_runner, "_load_api_key", lambda: "sk-fake")

    r = client.post("/api/agent/build", json={"prompt": "make me a tiny lab"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "tool_result" in types
    assert types[-1] == "done"

    tool_call_event = next(e for e in events if e["type"] == "tool_call")
    assert {"name", "args"} <= tool_call_event.keys()
    done = events[-1]
    assert done["lab_id"] == next(iter(build_repo.labs))


def test_sse_endpoint_missing_key_streams_error(monkeypatch, client, build_repo):
    monkeypatch.setattr(agent_runner, "_load_api_key", lambda: None)
    r = client.post("/api/agent/build", json={"prompt": "x"})
    assert r.status_code == 200
    events = _parse_sse(r.text)
    assert events[-1]["type"] == "error"


# ============================================================================
# 5. Integration — a real cheap OpenRouter call. SKIPs without a key.
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="requires a real OPENROUTER_API_KEY (no paid call in CI)",
)
def test_integration_real_build_creates_lab():
    repo = FakeRepo()
    events = list(agent_runner.run_build(
        repo, "Build a simple lab with two hosts connected to each other.",
        model="anthropic/claude-3.5-haiku", max_iterations=20))
    assert events[-1]["type"] in ("done", "error")
    # A real model on this prompt should at least create the lab.
    assert len(repo.labs) >= 1
