"""Build site/docs/api/index.html from the live FastAPI OpenAPI spec.

Run with the backend venv:
    ~/omnilab-env/bin/python scripts/build_api_docs.py

Output: site/docs/api/index.html (plus the raw spec at site/docs/api/openapi.json).

Design goals (per CRE-23):
- Left sidebar with searchable endpoint navigation
- Color-coded HTTP methods
- All public endpoints documented with paths, descriptions, params, examples
- Mobile responsive
- ZERO third-party scripts (matches the privacy claim on the landing page)
"""
from __future__ import annotations

import json
import os
import sys
from html import escape
from pathlib import Path

# -- bootstrap: same isolation trick as the test suite --------------------
REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("OMNILAB_LICENSE_DIR", "/tmp/cre23-build-lic")
os.makedirs(os.environ["OMNILAB_LICENSE_DIR"], exist_ok=True)

from main import app  # noqa: E402

# -- pull the spec --------------------------------------------------------
spec = app.openapi()

# Strip routes that aren't part of the public REST API surface
def _is_public(path: str) -> bool:
    if path.startswith("/guacamole"):
        return False  # reverse proxy, not an API
    if path == "/" or path == "/checkout":
        return False  # SPA + Stripe redirect
    if "{full_path}" in path:
        return False  # SPA fallback catch-all
    return True

spec["paths"] = {p: v for p, v in spec["paths"].items() if _is_public(p)}

# -- group endpoints by tag ----------------------------------------------
HTTP_METHODS = ("get", "post", "put", "patch", "delete", "options", "head")

groups: dict[str, list[dict]] = {}
for path in sorted(spec["paths"]):
    methods = spec["paths"][path]
    for method in HTTP_METHODS:
        if method not in methods:
            continue
        op = methods[method]
        tags = op.get("tags") or [_guess_tag(path)] if (
            _guess_tag := (lambda p: (p.split("/")[2] if p.startswith("/api/") and len(p.split("/")) > 2 else "misc"))
        ) else ["misc"]
        for tag in tags:
            groups.setdefault(tag, []).append({
                "path": path,
                "method": method.upper(),
                "op": op,
            })

# Sort groups in a sensible order: license, billing, labs, nodes, networks,
# templates, system, health, backup, updates, console, then anything else.
PREFERRED_ORDER = [
    "license", "billing", "labs", "nodes", "networks", "templates",
    "system", "health", "backup", "updates", "console",
]
def _group_key(t):
    try:
        return (PREFERRED_ORDER.index(t), t)
    except ValueError:
        return (999, t)

sorted_groups = sorted(groups.items(), key=lambda kv: _group_key(kv[0]))

# -- helpers --------------------------------------------------------------
METHOD_COLORS = {
    "GET":     ("#3b82f6", "GET"),   # blue
    "POST":    ("#10b981", "POST"),  # green
    "PUT":     ("#8b5cf6", "PUT"),   # purple
    "PATCH":   ("#f59e0b", "PATCH"), # amber
    "DELETE":  ("#ef4444", "DEL"),   # red
    "OPTIONS": ("#6b7280", "OPT"),
    "HEAD":    ("#6b7280", "HEAD"),
}

def slug(method: str, path: str) -> str:
    safe = path.strip("/").replace("/", "-").replace("{", "").replace("}", "")
    return f"{method.lower()}-{safe}" if safe else f"{method.lower()}-root"

def resolve_ref(ref: str) -> dict:
    """Resolve a JSON pointer like '#/components/schemas/Foo' against the spec."""
    if not ref.startswith("#/"):
        return {}
    node = spec
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            return {}
        node = node[part]
    return node if isinstance(node, dict) else {}

def render_schema_example(schema: dict, depth: int = 0) -> str:
    """Generate a small JSON example for a schema (best-effort)."""
    if not isinstance(schema, dict):
        return "null"
    if "$ref" in schema:
        schema = resolve_ref(schema["$ref"])
    if depth > 4:
        return "..."
    if schema.get("example") is not None:
        return json.dumps(schema["example"])
    t = schema.get("type")
    if "enum" in schema:
        return json.dumps(schema["enum"][0])
    if t == "object" or "properties" in schema:
        props = schema.get("properties") or {}
        if not props:
            return "{}"
        inner = ", ".join(
            f'"{k}": {render_schema_example(v, depth+1)}' for k, v in list(props.items())[:8]
        )
        return "{ " + inner + " }"
    if t == "array":
        item = schema.get("items") or {}
        return f"[ {render_schema_example(item, depth+1)} ]"
    defaults = {
        "string":  '"string"',
        "integer": "0",
        "number":  "0.0",
        "boolean": "true",
        "null":    "null",
    }
    return defaults.get(t, "null")

def html_param_table(params: list[dict]) -> str:
    if not params:
        return ""
    rows = []
    for p in params:
        name = escape(p.get("name", ""))
        loc = escape(p.get("in", ""))
        req = " <span class=\"req\">required</span>" if p.get("required") else ""
        s = p.get("schema", {}) or {}
        ptype = escape(s.get("type", "—"))
        desc = escape(p.get("description") or s.get("description") or "")
        default = ""
        if "default" in s:
            default = f" <span class=\"hint\">default: <code>{escape(json.dumps(s['default']))}</code></span>"
        rows.append(
            f"<tr><td><code>{name}</code>{req}</td><td>{loc}</td><td>{ptype}</td>"
            f"<td>{desc}{default}</td></tr>"
        )
    return (
        '<table class="params"><thead><tr><th>Name</th><th>In</th>'
        '<th>Type</th><th>Description</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table>"
    )

def html_request_body(rb: dict) -> str:
    if not rb:
        return ""
    content = rb.get("content") or {}
    if "application/json" not in content:
        return ""
    schema = content["application/json"].get("schema") or {}
    example = render_schema_example(schema)
    try:
        pretty = json.dumps(json.loads(example), indent=2)
    except (json.JSONDecodeError, ValueError):
        pretty = example
    required = ' <span class="req">required</span>' if rb.get("required") else ""
    return (
        f'<h4>Request body{required}</h4>'
        f'<pre class="example"><code>{escape(pretty)}</code></pre>'
    )

def html_responses(responses: dict) -> str:
    if not responses:
        return ""
    rows = []
    for code, resp in sorted(responses.items()):
        desc = escape(resp.get("description") or "")
        color = "#10b981" if code.startswith("2") else \
                "#f59e0b" if code.startswith("3") else \
                "#ef4444" if code.startswith(("4", "5")) else "#6b7280"
        rows.append(
            f'<tr><td><span class="status-code" style="color:{color}">{escape(code)}</span></td>'
            f'<td>{desc}</td></tr>'
        )
    return (
        '<h4>Responses</h4><table class="params"><tbody>'
        + "".join(rows) + "</tbody></table>"
    )

# -- render the body ------------------------------------------------------
body_blocks = []
nav_blocks = []
for tag, ops in sorted_groups:
    nav_items = []
    for op in ops:
        sid = slug(op["method"], op["path"])
        color, label = METHOD_COLORS.get(op["method"], ("#6b7280", op["method"]))
        nav_items.append(
            f'<a class="nav-op" href="#{sid}" data-q="{escape(op["method"].lower())} {escape(op["path"])}">'
            f'<span class="badge" style="background:{color}">{label}</span>'
            f'<span class="nav-path">{escape(op["path"])}</span></a>'
        )
    nav_blocks.append(
        f'<div class="nav-group" data-tag="{escape(tag)}">'
        f'<h3>{escape(tag)}</h3>{"".join(nav_items)}</div>'
    )

    op_blocks = []
    for op in ops:
        sid = slug(op["method"], op["path"])
        color, label = METHOD_COLORS.get(op["method"], ("#6b7280", op["method"]))
        meta = op["op"]
        summary = escape(meta.get("summary") or meta.get("operationId") or op["path"])
        description = escape(meta.get("description") or "")
        params_html = html_param_table(meta.get("parameters") or [])
        body_html = html_request_body(meta.get("requestBody") or {})
        resp_html = html_responses(meta.get("responses") or {})
        op_blocks.append(f"""
<article class="endpoint" id="{sid}">
  <header>
    <span class="badge" style="background:{color}">{label}</span>
    <code class="path">{escape(op["path"])}</code>
  </header>
  <h2>{summary}</h2>
  {f'<p class="desc">{description}</p>' if description else ''}
  {params_html}
  {body_html}
  {resp_html}
</article>""")

    body_blocks.append(f'<section class="tag-group"><h1 id="tag-{escape(tag)}">{escape(tag)}</h1>{"".join(op_blocks)}</section>')

# -- assemble final HTML --------------------------------------------------
HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0b0d12">
<meta name="color-scheme" content="dark">
<title>OmniLab REST API — Reference</title>
<meta name="description" content="OmniLab REST API reference. {count} endpoints covering labs, nodes, networks, license, billing, health, and more.">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="canonical" href="https://omnilab.io/docs/api/">
<style>
  :root {{
    --bg: #0b0d12; --bg-alt: #11141c; --bg-elev: #161a24;
    --border: #232735; --text: #e6e8ee; --text-muted: #9aa3b6;
    --accent: #7c5cff; --accent-2: #2cd4d9;
    --good: #10b981; --warn: #f59e0b; --bad: #ef4444;
    --mono: "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace;
  }}
  *, *::before, *::after {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  a {{ color: inherit; text-decoration: none; }}
  code, pre {{ font-family: var(--mono); }}
  h1, h2, h3, h4 {{ margin: 0 0 .5em; line-height: 1.25; }}

  /* ============ layout ============ */
  .shell {{ display: grid; grid-template-columns: 320px 1fr; min-height: 100vh; }}
  @media (max-width: 880px) {{
    .shell {{ grid-template-columns: 1fr; }}
    .sidebar {{ position: static !important; height: auto !important; border-right: none !important; border-bottom: 1px solid var(--border); }}
  }}

  /* ============ sidebar ============ */
  .sidebar {{
    position: sticky; top: 0; height: 100vh; overflow-y: auto;
    background: var(--bg-alt); border-right: 1px solid var(--border);
    padding: 20px;
  }}
  .sb-brand {{
    display: flex; align-items: center; gap: 10px;
    font-weight: 700; font-size: 1.05rem; margin-bottom: 8px;
  }}
  .sb-brand .mark {{
    width: 26px; height: 26px; border-radius: 8px;
    background: linear-gradient(135deg, #7c5cff, #2cd4d9);
  }}
  .sb-version {{ color: var(--text-muted); font-size: .8rem; margin-bottom: 18px; }}
  .sb-search {{
    width: 100%; padding: 9px 12px; border-radius: 9px;
    background: var(--bg-elev); border: 1px solid var(--border);
    color: var(--text); font: inherit;
    margin-bottom: 16px;
  }}
  .sb-search::placeholder {{ color: var(--text-muted); }}
  .sb-search:focus {{ outline: 2px solid var(--accent-2); outline-offset: 1px; }}
  .nav-group {{ margin-bottom: 22px; }}
  .nav-group h3 {{
    font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
    color: var(--text-muted); margin-bottom: 8px;
  }}
  .nav-op {{
    display: flex; align-items: center; gap: 10px;
    padding: 5px 8px; margin: 0 -8px;
    border-radius: 7px; color: var(--text-muted);
    font-size: .88rem; line-height: 1.3;
    border: 1px solid transparent;
  }}
  .nav-op:hover {{ color: var(--text); background: var(--bg-elev); }}
  .nav-op.active {{ color: var(--text); background: var(--bg-elev); border-color: var(--border); }}
  .nav-path {{
    font-family: var(--mono); font-size: .82rem;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }}

  /* ============ method badge ============ */
  .badge {{
    display: inline-block; flex-shrink: 0;
    color: #0b0d12; font-weight: 800;
    font-size: .65rem; letter-spacing: .04em;
    padding: 2px 6px; border-radius: 5px; min-width: 38px;
    text-align: center; font-family: var(--mono);
  }}

  /* ============ main content ============ */
  main {{ padding: 32px 40px; max-width: 920px; }}
  @media (max-width: 880px) {{ main {{ padding: 24px; }} }}

  .preamble {{
    background: var(--bg-elev); border: 1px solid var(--border);
    border-radius: 14px; padding: 22px 24px; margin-bottom: 32px;
  }}
  .preamble h1 {{ font-size: 1.7rem; margin-bottom: 6px; }}
  .preamble p {{ color: var(--text-muted); margin: 6px 0; }}
  .preamble code {{ background: var(--bg-alt); padding: 2px 6px; border-radius: 4px; font-size: .9em; }}

  .tag-group {{ margin-bottom: 56px; }}
  .tag-group > h1 {{
    font-size: 1.5rem; padding-bottom: 12px; margin-bottom: 18px;
    border-bottom: 1px solid var(--border); text-transform: capitalize;
  }}

  .endpoint {{
    background: var(--bg-elev); border: 1px solid var(--border);
    border-radius: 12px; padding: 22px 24px; margin-bottom: 18px;
    scroll-margin-top: 24px;
  }}
  .endpoint header {{
    display: flex; align-items: center; gap: 12px; margin-bottom: 14px;
    flex-wrap: wrap;
  }}
  .endpoint h2 {{ font-size: 1.1rem; margin: 0 0 4px; }}
  .endpoint .path {{
    color: var(--text); background: var(--bg-alt);
    padding: 4px 10px; border-radius: 6px; font-size: .92rem;
    word-break: break-all;
  }}
  .endpoint .desc {{ color: var(--text-muted); margin: 6px 0 16px; }}
  .endpoint h4 {{
    font-size: .78rem; text-transform: uppercase; letter-spacing: .08em;
    color: var(--text-muted); margin-top: 22px; margin-bottom: 8px;
  }}

  /* ============ tables ============ */
  table.params {{
    width: 100%; border-collapse: collapse;
    background: var(--bg-alt); border-radius: 8px; overflow: hidden;
    border: 1px solid var(--border); margin-top: 4px;
  }}
  table.params th, table.params td {{
    padding: 9px 12px; text-align: left; vertical-align: top;
    border-bottom: 1px solid var(--border); font-size: .9rem;
  }}
  table.params th {{
    background: var(--bg); color: var(--text);
    font-weight: 600; font-size: .82rem;
    text-transform: uppercase; letter-spacing: .04em;
  }}
  table.params tr:last-child td {{ border-bottom: none; }}
  table.params code {{ color: var(--accent-2); }}
  .req {{ color: var(--bad); font-size: .7rem; text-transform: uppercase; margin-left: 4px; }}
  .hint {{ color: var(--text-muted); font-size: .82rem; }}
  .status-code {{ font-family: var(--mono); font-weight: 700; }}

  /* ============ code blocks ============ */
  pre.example {{
    background: var(--bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 14px 16px;
    font-size: .86rem; line-height: 1.55;
    overflow-x: auto; margin: 4px 0 0;
  }}

  /* ============ focus ============ */
  :focus-visible {{ outline: 2px solid var(--accent-2); outline-offset: 2px; border-radius: 4px; }}
</style>
</head>
<body>
<div class="shell">
  <aside class="sidebar">
    <a class="sb-brand" href="/">
      <span class="mark" aria-hidden="true"></span> OmniLab API
    </a>
    <div class="sb-version">v{api_version}</div>
    <input class="sb-search" type="search" placeholder="Search endpoints…" autocomplete="off" id="q" aria-label="Search endpoints">
    <nav>{nav}</nav>
  </aside>
  <main>
    <div class="preamble">
      <h1>OmniLab REST API</h1>
      <p>
        Base URL: <code>http://your-server:5000</code> &nbsp;·&nbsp;
        Content-Type: <code>application/json</code> &nbsp;·&nbsp;
        Spec: <a href="openapi.json">openapi.json</a>
      </p>
      <p>
        {count} public endpoints across {tag_count} resource groups. Generated from the live FastAPI schema — this page never drifts from the running server.
      </p>
      <p>
        Local interactive docs (with Try-it-now): visit <code>/docs</code> (Swagger UI) or <code>/redoc</code> on your running OmniLab instance.
      </p>
    </div>
    {body}
  </main>
</div>
<script>
  // Live search — filters sidebar items by method + path substring
  (function() {{
    var q = document.getElementById('q');
    var items = document.querySelectorAll('.nav-op');
    var groups = document.querySelectorAll('.nav-group');
    q.addEventListener('input', function() {{
      var v = q.value.trim().toLowerCase();
      items.forEach(function(el) {{
        var hit = !v || el.dataset.q.indexOf(v) >= 0;
        el.style.display = hit ? '' : 'none';
      }});
      groups.forEach(function(g) {{
        var visible = g.querySelectorAll('.nav-op:not([style*="display: none"])').length;
        g.style.display = visible ? '' : 'none';
      }});
    }});

    // Scroll-spy — highlight sidebar entry for the endpoint in view
    var endpoints = document.querySelectorAll('.endpoint');
    var byId = {{}};
    items.forEach(function(el) {{
      var href = el.getAttribute('href');
      if (href && href.charAt(0) === '#') byId[href.slice(1)] = el;
    }});
    var io = new IntersectionObserver(function(entries) {{
      entries.forEach(function(e) {{
        var link = byId[e.target.id];
        if (!link) return;
        if (e.isIntersecting) {{
          items.forEach(function(el) {{ el.classList.remove('active'); }});
          link.classList.add('active');
        }}
      }});
    }}, {{ rootMargin: '-30% 0px -60% 0px' }});
    endpoints.forEach(function(el) {{ io.observe(el); }});
  }})();
</script>
</body>
</html>
"""

total_ops = sum(len(ops) for _, ops in sorted_groups)
out = HTML_TEMPLATE.format(
    api_version=escape(spec.get("info", {}).get("version", "1.0.0")),
    nav="".join(nav_blocks),
    body="".join(body_blocks),
    count=total_ops,
    tag_count=len(sorted_groups),
)

OUT_HTML = REPO / "site/docs/api/index.html"
OUT_JSON = REPO / "site/docs/api/openapi.json"
OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
OUT_HTML.write_text(out)
OUT_JSON.write_text(json.dumps(spec, indent=2))

print(f"wrote {OUT_HTML} ({OUT_HTML.stat().st_size} bytes)")
print(f"wrote {OUT_JSON} ({OUT_JSON.stat().st_size} bytes)")
print(f"endpoints: {total_ops}, groups: {len(sorted_groups)}")
