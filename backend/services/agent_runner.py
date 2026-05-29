"""
backend/services/agent_runner.py  —  AI Lab Builder, Phase 3 (CRE-44)

The LLM tool-calling loop — "the actual AI". It drives the pure-Python tools in
``services/agent_tools.py`` from a natural-language prompt, using OpenRouter
(OpenAI-compatible /chat/completions + tool-calling) over plain ``httpx``. No
``openai``/``anthropic`` SDK is used or required, which also makes the LLM call
trivially mockable (monkeypatch ``_chat_completion``).

Design:
- ``build_tools_schema()`` returns the OpenAI ``tools=[...]`` array, ONE entry
  per ``agent_tools.TOOLS`` key, with JSON-schemas that mirror
  docs/ailb-tool-api.md. The agent can ONLY call these registered tools.
- ``run_build(repo, prompt, ...)`` is a generator yielding structured events:
  ``thinking`` / ``tool_call`` / ``tool_result`` / ``done`` / ``error``.
- Hermes (CRE-40) cost rails are enforced here: a hard per-call ``max_tokens``
  (default 4096), a hard ``max_iterations`` cap (default 20), a total tool-call
  cap, and a bounded message history. On unrecoverable error the lab the agent
  created is torn down via ``delete_lab`` so nothing is orphaned.
- The OpenRouter API key is NEVER logged; it is redacted from every error or
  exception surfaced to the client (``_redact``).
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path

import httpx

from services import agent_tools as tools
from services.agent_tools import AILBError

# ============================================================================
# Configuration / constants
# ============================================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "anthropic/claude-sonnet-4.5"

# Cost rails (CRE-40 / Hermes). NEVER inherit a 32k default.
DEFAULT_MAX_TOKENS = 4096
DEFAULT_MAX_ITERATIONS = 20
DEFAULT_MAX_TOOL_CALLS = 60
# Bound the message history so it can't grow without limit across iterations.
# We always keep the system prompt (index 0) + the original user prompt
# (index 1) and trim the oldest middle messages beyond this many.
MAX_HISTORY_MESSAGES = 60

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "lab_builder.md"


# ============================================================================
# API key handling — env first, then ~/.omnilab/.env (read-only here).
# AILB-5/CRE-45 owns WRITING that file; we only READ it if present.
# ============================================================================

def _load_api_key() -> str | None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip() or None
    env_path = Path.home() / ".omnilab" / ".env"
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == "OPENROUTER_API_KEY":
                return value.strip().strip('"').strip("'") or None
    except (OSError, UnicodeDecodeError):
        pass
    return None


def _redact(text: str, api_key: str | None) -> str:
    """Strip the API key from any text before it reaches a client or log."""
    if not text:
        return text
    if api_key:
        text = text.replace(api_key, "***REDACTED***")
        # Also redact a "Bearer <key>" form in case it was serialized.
        text = text.replace(f"Bearer {api_key}", "Bearer ***REDACTED***")
    return text


def _load_system_prompt() -> str:
    try:
        return _PROMPT_PATH.read_text(encoding="utf-8")
    except OSError:
        # Defensive fallback so the loop never hard-fails on a missing file.
        return (
            "You are OmniLab's Lab Builder agent. Call list_inventory first, "
            "then create_lab, create_node, link_nodes, push_config, start_node, "
            "poll get_node_state, and finish with get_lab_state plus a short "
            "text summary. You may only call the registered tools."
        )


# ============================================================================
# Tool schemas (OpenAI function format) — mirror docs/ailb-tool-api.md.
# One entry per agent_tools.TOOLS key. Hand-written table keyed by tool name.
# ============================================================================

def _endpoint_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "node_id": {"type": "string", "description": "node id of this endpoint"},
            "iface": {"type": "string", "description": "interface name; omit to auto-assign next free"},
        },
        "required": ["node_id"],
    }


_TOOL_PARAMS: dict[str, dict] = {
    "list_inventory": {
        "type": "object", "properties": {}, "required": [],
    },
    "get_lab_state": {
        "type": "object",
        "properties": {"lab_id": {"type": "string"}},
        "required": ["lab_id"],
    },
    "get_node_state": {
        "type": "object",
        "properties": {"node_id": {"type": "string"}},
        "required": ["node_id"],
    },
    "create_lab": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "lab name (required)"},
            "description": {"type": "string"},
        },
        "required": ["name"],
    },
    "create_node": {
        "type": "object",
        "properties": {
            "lab_id": {"type": "string"},
            "name": {"type": "string"},
            "image": {"type": "string", "description": "must be an image from list_inventory"},
            "type": {"type": "string", "description": "node type; defaults to the image's first type"},
            "options": {"type": "object", "description": "optional, e.g. {x, y, ram_mb}"},
        },
        "required": ["lab_id", "name", "image"],
    },
    "link_nodes": {
        "type": "object",
        "properties": {
            "lab_id": {"type": "string"},
            "a": _endpoint_schema(),
            "b": _endpoint_schema(),
            "options": {"type": "object"},
        },
        "required": ["lab_id", "a", "b"],
    },
    "push_config": {
        "type": "object",
        "properties": {
            "node_id": {"type": "string"},
            "config_text": {"type": "string"},
            "mode": {"type": "string", "enum": ["startup", "live"], "description": "default startup"},
        },
        "required": ["node_id", "config_text"],
    },
    "start_node": {
        "type": "object",
        "properties": {"node_id": {"type": "string"}},
        "required": ["node_id"],
    },
    "stop_node": {
        "type": "object",
        "properties": {"node_id": {"type": "string"}},
        "required": ["node_id"],
    },
    "delete_lab": {
        "type": "object",
        "properties": {"lab_id": {"type": "string"}},
        "required": ["lab_id"],
    },
}

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "list_inventory": "List available node images/types and host capacity. Call this first.",
    "get_lab_state": "Return the full topology (nodes + links) for a lab. The source of truth.",
    "get_node_state": "Return fine-grained state for one node. Poll this after start_node.",
    "create_lab": "Create a new (empty) lab and return its lab_id.",
    "create_node": "Add a node to a lab. Returns node_id and available interfaces. Does NOT start it.",
    "link_nodes": "Connect two node interfaces (omit iface to auto-assign). Creates the L2 segment.",
    "push_config": "Apply configuration to a node (mode=startup at boot, or live to a running node).",
    "start_node": "Boot a node. Idempotent. Poll get_node_state for readiness.",
    "stop_node": "Stop a node. Idempotent.",
    "delete_lab": "Destroy a lab: stop all nodes and remove links/nodes/lab rows.",
}


def build_tools_schema() -> list[dict]:
    """OpenAI ``tools=[...]`` array — one function per registered tool."""
    schema: list[dict] = []
    for name in tools.TOOLS:
        schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": _TOOL_DESCRIPTIONS.get(name, name),
                "parameters": _TOOL_PARAMS.get(
                    name, {"type": "object", "properties": {}, "required": []}
                ),
            },
        })
    return schema


# ============================================================================
# OpenRouter HTTP call — the single seam tests monkeypatch.
# ============================================================================

def _chat_completion(*, api_key: str, model: str, messages: list[dict],
                     tools_schema: list[dict], max_tokens: int,
                     timeout: float = 60.0) -> dict:
    """POST one chat/completions request and return the parsed JSON.

    This is the ONLY place a real network call happens, so unit tests
    monkeypatch this function (or httpx) to return a scripted sequence. The
    request ALWAYS carries a hard ``max_tokens`` (cost rail)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://omnilab.local",
        "X-Title": "OmniLab Lab Builder",
    }
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools_schema,
        "tool_choice": "auto",
        "max_tokens": max_tokens,
    }
    resp = httpx.post(OPENROUTER_URL, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


# ============================================================================
# Argument normalization — the contract uses "type" but the tool param is
# "type_" (type is a builtin). Mirror api/agent._normalize_args.
# ============================================================================

def _normalize_args(name: str, args: dict) -> dict:
    if name == "create_node" and "type" in args:
        args = dict(args)
        args["type_"] = args.pop("type")
    return args


def _trim_history(messages: list[dict]) -> list[dict]:
    """Bound the message history. Keep system (0) + first user (1) and the most
    recent tail; drop the oldest middle messages if we exceed the cap."""
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    head = messages[:2]
    tail = messages[-(MAX_HISTORY_MESSAGES - 2):]
    return head + tail


# ============================================================================
# The loop
# ============================================================================

def run_build(repo: tools.Repo, prompt: str, *, model: str | None = None,
              max_iterations: int = DEFAULT_MAX_ITERATIONS,
              max_tokens: int = DEFAULT_MAX_TOKENS,
              max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS,
              api_key: str | None = None) -> Iterator[dict]:
    """Drive the LLM tool-calling loop, yielding structured events.

    Events: ``thinking`` {text}, ``tool_call`` {name, args},
    ``tool_result`` {name, ok, data?/error?}, ``done`` {lab_id, summary},
    ``error`` {message}.

    Cost rails: ``max_tokens`` per call (default 4096), ``max_iterations``
    (default 20) and ``max_tool_calls`` caps, bounded history. On unrecoverable
    error the created lab is delete_lab'd. The API key is never leaked.
    """
    key = api_key or _load_api_key()
    if not key:
        yield {"type": "error", "message": "OPENROUTER_API_KEY is not configured"}
        return

    model = model or DEFAULT_MODEL
    # Clamp the iteration cap to something sane (never inherit a huge default).
    if not isinstance(max_iterations, int) or max_iterations <= 0:
        max_iterations = DEFAULT_MAX_ITERATIONS
    max_iterations = min(max_iterations, 100)

    tools_schema = build_tools_schema()
    messages: list[dict] = [
        {"role": "system", "content": _load_system_prompt()},
        {"role": "user", "content": prompt},
    ]

    created_lab_id: str | None = None
    tool_calls_made = 0
    finished = False

    try:
        for _ in range(max_iterations):
            messages = _trim_history(messages)
            try:
                completion = _chat_completion(
                    api_key=key, model=model, messages=messages,
                    tools_schema=tools_schema, max_tokens=max_tokens,
                )
            except httpx.HTTPError as exc:
                raise _Unrecoverable(_redact(f"LLM request failed: {exc}", key)) from exc

            choice = (completion.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            content = msg.get("content")
            tool_calls = msg.get("tool_calls") or []

            if content:
                yield {"type": "thinking", "text": content}

            # No tool calls -> the model produced a final answer. Done.
            if not tool_calls:
                summary = content or ""
                finished = True
                yield {"type": "done", "lab_id": created_lab_id, "summary": summary}
                return

            # Append the assistant turn (with its tool_calls) before results.
            messages.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls,
            })

            for tc in tool_calls:
                if tool_calls_made >= max_tool_calls:
                    raise _Unrecoverable(
                        f"tool-call cap reached ({max_tool_calls}); stopping"
                    )
                tool_calls_made += 1

                fn = (tc.get("function") or {})
                name = fn.get("name") or ""
                raw_args = fn.get("arguments")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                    if not isinstance(args, dict):
                        args = {}
                except (TypeError, ValueError):
                    args = {}

                yield {"type": "tool_call", "name": name, "args": args}

                result = _dispatch(repo, name, args)
                if result["ok"] and name == "create_lab":
                    created_lab_id = (result.get("data") or {}).get("lab_id") or created_lab_id

                # Surface the tool result event.
                if result["ok"]:
                    yield {"type": "tool_result", "name": name, "ok": True,
                           "data": result.get("data")}
                else:
                    yield {"type": "tool_result", "name": name, "ok": False,
                           "error": result.get("error")}

                # Feed the result back to the model.
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id") or name,
                    "name": name,
                    "content": json.dumps(result),
                })

        # Fell out of the loop without finishing -> iteration cap exceeded.
        raise _Unrecoverable(
            f"max_iterations ({max_iterations}) exceeded without completing the build"
        )

    except _Unrecoverable as exc:
        _safe_cleanup(repo, created_lab_id)
        yield {"type": "error", "message": _redact(str(exc), key)}
    except Exception as exc:  # noqa: BLE001 — last-resort guard; never leak the key
        _safe_cleanup(repo, created_lab_id)
        yield {"type": "error", "message": _redact(f"unexpected error: {exc}", key)}
    finally:
        if not finished:
            # Loop ended via error path; nothing else to emit here.
            pass


class _Unrecoverable(Exception):
    """Internal signal: stop the loop, clean up, emit an error event."""


def _dispatch(repo: tools.Repo, name: str, args: dict) -> dict:
    """Invoke a registered tool, always returning the standard envelope.

    Unknown tools and bad arguments become error envelopes (never exceptions),
    so the model can read them and self-correct — that is NOT an unrecoverable
    error on its own."""
    fn = tools.TOOLS.get(name)
    if fn is None:
        return tools.err("VALIDATION", f"unknown tool {name!r}",
                         {"available": sorted(tools.TOOLS)})
    try:
        return fn(repo, **_normalize_args(name, args))
    except AILBError as e:
        return tools.err(e.code, e.message, e.details)
    except TypeError as e:
        return tools.err("VALIDATION", f"bad arguments for {name}: {e}")


def _safe_cleanup(repo: tools.Repo, lab_id: str | None) -> None:
    """Best-effort delete_lab so a half-built lab isn't orphaned on error."""
    if not lab_id:
        return
    try:
        tools.delete_lab(repo, lab_id)
    except Exception:  # noqa: BLE001 — cleanup must never raise
        pass
