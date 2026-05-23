# OmniLab Templates

The "golden lab" templates are pre-configured topologies that one-click deploy
into a working Docker-backed lab. They are defined in
[`backend/api/templates.py`](../backend/api/templates.py) and surfaced through
`GET /api/templates/` + `POST /api/templates/{id}/deploy`.

This document is the source of truth for which templates are smoke-tested and
known-working, and is updated alongside any change that touches a template
image or `docker_options`.

## Templates ledger

| Template ID         | Description                         | Nodes (docker)        | Status | Notes |
| ------------------- | ----------------------------------- | --------------------- | ------ | ----- |
| `pentest-lab`       | Kali + DVWA target                  | kali, target          | ✓      | Reference template; Kali needs `command` override + apt install of nmap/etc on first start |
| `wazuh-soc`         | Wazuh manager + Linux + Kali        | manager, linux, kali  | ✓      | Manager web UI takes ~60s to bind :443 — 502 from smoke test at 8s is benign |
| `threat-hunting`    | Suricata + Zeek + TheHive           | suricata, zeek, thehive | ✓    | Both IDS containers need `command` override. **Zeek image is `zeek/zeek:latest` (official), NOT `zeekurity/zeek` (doesn't exist).** |
| `caldera`           | MITRE Caldera + 2 victim agents     | caldera, agent-1, agent-2 | ✓  | Caldera web UI binds :8888 after ~30s |
| `ansible-lab`       | Controller + 2 managed nodes        | controller, node-1, node-2 | ✓ | All ubuntu-based, need `command` override |
| `cicd-pipeline`     | Gitea + Jenkins + registry          | gitea, jenkins, registry | ✓  | Harbor swapped for `registry:2` (Harbor needs PostgreSQL/Redis/Trivy/nginx sidecar stack — deferred to v1.1) |
| `llm-sandbox`       | Ollama + Open-WebUI + attacker      | ollama, webui, attacker | ✓   | Open-WebUI lives on `ghcr.io/open-webui/open-webui:main` (not Docker Hub) |
| `mlops-lab`         | Jupyter + MLflow + MinIO            | jupyter, mlflow, minio | ✓    | **Jupyter image pinned to `:x86_64-python-3.11` — `:latest` tag does not exist on Docker Hub.** |
| `kubernetes-cluster` | Coming soon                        | —                     | —      | Marked `coming_soon=True`. Needs QEMU cloud-init + bridge-to-docker networking. v1.1+. |
| `vyos-routing`      | Coming soon                         | —                     | —      | Marked `coming_soon=True`. v1.1+. |

## Smoke testing

`scripts/smoke_test_templates.py` exercises each template end-to-end against
the live backend:

1. `POST /api/templates/{id}/deploy` — creates lab + node rows
2. `POST /api/nodes/{id}/start` for each docker node — pulls image + `docker run`
3. Sleeps 8s, then `docker inspect` each container to confirm it's still
   running (catches the "exits-after-init" footgun)
4. If a node has `web_port`, hits the reverse proxy and records the status
5. Cleans up (stop nodes + delete lab)
6. **Runs `docker system prune -af` BEFORE each template** — these
   images are huge (1–6 GB each) and the test runs sequentially.
   Without per-template pruning, the disk fills mid-run, SQLite
   writes start failing (`database or disk is full`), and you get
   false negatives on whichever template ran last. The cost is
   ~30s of re-pulling already-cached layers between templates,
   which is acceptable for a 5-minute test run.

### Running it

```bash
# Default: every template except pentest-lab (already verified) and the
# coming_soon ones
~/netlab-env/bin/python ~/netlab/scripts/smoke_test_templates.py

# Subset — only the templates you want to verify
~/netlab-env/bin/python ~/netlab/scripts/smoke_test_templates.py threat-hunting mlops-lab
```

Results are written to `/tmp/smoke_test_results.json`.

### Interpreting results

- **`status=running`** — container alive after 8s. The verifiable minimum.
- **`status=exited(...)`** — container died. Either the image's entrypoint
  exits after init, OR the image reference is wrong (Docker pull silently
  failed somewhere upstream). Check `docker pull <image>` directly.
- **`web_status=2xx/3xx`** — reverse proxy + service both working.
- **`web_status=502`** — service is still booting (most web UIs need 30-60s).
  Re-run after a delay, OR trust the `running` flag alone.
- **`web_status=403`** — service responded but rejected unauth (Jenkins
  default behavior). Expected.

### Recurring template-config pitfalls

These have all been caught at least once by the smoke test and live in
the omnilab-engineering Hermes skill under "Smoke-testing docker templates":

1. **Image references must be exact and existing.** `docker pull` failures
   surface as `status=None` (no container ever existed). Verify with
   `docker pull` directly when adding any template.
2. **"Slim" base images lack expected tools.** `kalilinux/kali-rolling`
   ships with bash + apt + curl only — no nmap, ping, nc, hydra. Add
   an `apt-get install` in `docker_options.command`.
3. **Images that exit after init.** `tleemcjr/metasploitable2` and similar
   "setup-then-fork-then-exit" images need a `command: ["sleep","infinity"]`
   override OR replacement with a long-running image (e.g.
   `vulnerables/web-dvwa` instead of metasploitable2).
4. **Tagless image references.** `jupyter/datascience-notebook` (no tag)
   defaults to `:latest`, which does not exist for many of the Jupyter
   images. Pin an explicit tag.

When a smoke test catches an issue: fix the template, update this ledger's
**Notes** column, restart the backend, re-run the smoke test for that
template only, then commit.
