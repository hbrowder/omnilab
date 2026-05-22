# API documentation site (omnilab.io/docs/api)

Tracked under **CRE-23**. Single-page static doc rendered from the **live FastAPI OpenAPI spec** — never drifts from what the running server actually exposes.

## Files

```
site/docs/api/
├── index.html      # Auto-generated reference page (CRE-23 deliverable)
└── openapi.json    # Auto-generated raw spec (linked from the doc page)
```

Both files are committed for static hosting, but they are **build artifacts**. Source of truth is `backend/api/*.py` + `scripts/build_api_docs.py`.

## Regenerating

After any backend route change:

```bash
cd ~/netlab
~/netlab-env/bin/python scripts/build_api_docs.py
git add site/docs/api/
git commit -m "docs(api): regenerate (route X added/removed)"
```

The CI workflow (`.github/workflows/ci.yml`) runs this build on every PR and fails if the committed artifacts are stale relative to the current spec. So you can't accidentally land a backend change that leaves the docs lying about the API surface.

## Why hand-roll instead of using Redoc / Swagger UI?

1. **No third-party scripts.** The marketing site at the same domain promises "no tracking, no cookies, no third-party scripts." A CDN-hosted Redoc bundle would break that claim. Vendoring it (~900 KB of JS) is the alternative; the hand-rolled page is 50 KB total including the spec.
2. **Local interactive docs still exist.** Anyone running OmniLab gets Swagger UI at `/docs` and Redoc at `/redoc` on their own instance — that's where Try-it-now actually belongs (you need a real backend to send requests to).
3. **Build-time render means perfect search-engine indexing.** A SPA doc tool's content is invisible to crawlers without JS execution.

## Deploy

This folder ships with the rest of `site/` to Cloudflare Pages. The same `site/` build output dir handles both:

- `omnilab.io/`           → `site/index.html` (landing — CRE-20)
- `omnilab.io/docs/api/`  → `site/docs/api/index.html` (this — CRE-23)

No additional Cloudflare config is needed. The build setting "build output directory = `site`" covers both pages.

## What the page contains

- Sticky left sidebar with searchable endpoint list, grouped by router tag
- Method-coloured badges (GET=blue, POST=green, PUT=purple, PATCH=amber, DELETE=red)
- Live filter as you type in the search box (no debounce, instant on every keystroke)
- Scroll-spy: sidebar entry highlights as you scroll through endpoint cards
- For each endpoint: HTTP method + path, summary, description, parameter table (path/query/header with type and required marker), request-body example (auto-generated from the schema), response code table colour-coded by status class
- Footer of the preamble points readers at the live Swagger UI / Redoc on their own running instance for Try-it-now flows

## Limits / known cosmetics

- Request-body examples are best-effort schema renderings (`render_schema_example` in the build script). They cover scalars, objects, arrays, enums, and `example`/`default` overrides. Recursive schemas are capped at depth 4 with `...`. If a route grows a complex polymorphic body and the example looks off, add an explicit `example=` to the pydantic model — the build picks it up automatically.
- The build emits a FastAPI duplicate-operation-ID warning for the Guacamole reverse proxy. The script filters `/guacamole/*` out of the public surface, so the warning is cosmetic. (Tracked already in the test suite warnings — separate cleanup ticket-worthy.)
