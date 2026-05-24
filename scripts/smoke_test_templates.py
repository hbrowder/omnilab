#!/usr/bin/env python3
"""
Smoke-test all docker templates end-to-end against the live daemon.

For each template:
  1. POST /api/templates/{id}/deploy → creates lab + node rows
  2. POST /api/nodes/{node_id}/start for each docker node → docker run
  3. Wait 5s, then `docker inspect` each container to confirm it's still alive
     (catches the "exits-after-init" footgun)
  4. If a node has web_port, hit the reverse proxy: GET /labs/{lab_id}/nodes/{node_id}/web/
     → expect 2xx/3xx
  5. Cleanup: stop all nodes + delete the lab

Run with: ~/omnilab-env/bin/python ~/omnilab/scripts/smoke_test_templates.py [template_id ...]
If no template IDs supplied, runs all docker-typed templates except pentest-lab (already verified).
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://localhost:5000"
TEMPLATES_TO_SKIP = {"pentest-lab", "kubernetes-cluster", "vyos-routing"}


def http(method: str, path: str, body=None, timeout=30):
    url = f"{BASE_URL}{path}"
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, raw[:200].decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, str(e)
    except Exception as e:
        return None, str(e)


def docker_inspect(container_name: str):
    """Return (status, exit_code) or (None, None) if container missing."""
    r = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Status}}|{{.State.ExitCode}}", container_name],
        capture_output=True, text=True, timeout=10,
    )
    if r.returncode != 0:
        return None, None
    parts = r.stdout.strip().split("|")
    return parts[0], int(parts[1]) if len(parts) > 1 else 0


def smoke_test(template_id: str) -> dict:
    """Return result dict with success flag, errors, and per-node status."""
    result = {"template_id": template_id, "ok": False, "errors": [], "nodes": [], "lab_id": None}

    # 1. Deploy
    status, body = http("POST", f"/api/templates/{template_id}/deploy",
                        body={"name": f"smoketest-{template_id}-{int(time.time())}"})
    if status != 200:
        result["errors"].append(f"deploy failed: HTTP {status} {body}")
        return result

    lab_id = body.get("lab_id") or body.get("id")
    if not lab_id:
        result["errors"].append(f"deploy returned no lab_id: {body}")
        return result
    result["lab_id"] = lab_id

    # 2. Fetch nodes for this lab via topology endpoint
    status, body = http("GET", f"/api/labs/{lab_id}/topology")
    if status != 200 or not isinstance(body, dict):
        result["errors"].append(f"topology fetch failed: HTTP {status}")
        return result
    nodes = body.get("nodes", [])
    docker_nodes = [n for n in nodes if (n.get("type") or "").lower() == "docker"]

    # 3. Start each docker node
    for node in docker_nodes:
        node_id = node["id"]
        node_name = node["name"]
        result["nodes"].append({"name": node_name, "id": node_id, "status": "starting"})
        s, b = http("POST", f"/api/nodes/{node_id}/start", timeout=180)
        if s != 200:
            result["nodes"][-1]["status"] = "failed_start"
            result["nodes"][-1]["error"] = f"HTTP {s}: {str(b)[:300]}"
            continue
        result["nodes"][-1]["start_response"] = b if isinstance(b, dict) else {}

    # 4. Wait for containers to settle, then inspect
    time.sleep(8)
    for nrec in result["nodes"]:
        container_name = f"omnilab-{nrec['id']}"
        status, exit_code = docker_inspect(container_name)
        nrec["docker_status"] = status
        nrec["docker_exit_code"] = exit_code
        if status != "running":
            nrec["status"] = f"exited(status={status}, exit_code={exit_code})"
        else:
            nrec["status"] = "running"

    # 5. Web-UI reverse proxy check (only for nodes with web_port)
    for node, nrec in zip(docker_nodes, result["nodes"], strict=True):
        config_str = node.get("config") or "{}"
        try:
            cfg = json.loads(config_str) if isinstance(config_str, str) else config_str
        except json.JSONDecodeError:
            cfg = {}
        if cfg.get("web_port") and nrec.get("status") == "running":
            s, b = http("GET", f"/labs/{lab_id}/nodes/{nrec['id']}/web/", timeout=15)
            nrec["web_status"] = s
            nrec["web_preview"] = (str(b)[:120] if isinstance(b, str) else "OK") if s else "no response"

    # 6. Cleanup
    for nrec in result["nodes"]:
        if nrec.get("status") == "running" or "exited" in str(nrec.get("status", "")):
            http("POST", f"/api/nodes/{nrec['id']}/stop", timeout=30)
    http("DELETE", f"/api/labs/{lab_id}", timeout=30)

    # 7. Summary
    failing = [n for n in result["nodes"] if n.get("status") != "running"]
    result["ok"] = len(failing) == 0 and len(result["nodes"]) > 0
    result["summary"] = f"{len(result['nodes']) - len(failing)}/{len(result['nodes'])} containers running"
    return result


def main():
    # Get list of templates
    status, body = http("GET", "/api/templates/")
    if status != 200:
        print(f"FATAL: couldn't list templates: {status} {body}")
        sys.exit(1)

    all_templates = body if isinstance(body, list) else body.get("templates", [])
    requested = set(sys.argv[1:]) if len(sys.argv) > 1 else None

    targets = []
    for t in all_templates:
        tid = t.get("id")
        if requested:
            if tid in requested:
                targets.append(tid)
        else:
            if tid not in TEMPLATES_TO_SKIP and not t.get("coming_soon"):
                targets.append(tid)

    print(f"=== Smoke testing {len(targets)} templates ===")
    for tid in targets:
        print(f"  {tid}")
    print()

    results = []
    for tid in targets:
        # Disk hygiene — prune BEFORE each template so we always start
        # with room for the next image pull. Template images are 1-6 GB
        # each; sequential pulls can fill 20 GB fast. Without this,
        # SQLite writes start failing mid-test ("database or disk is full")
        # and you get false negatives on whichever template runs last.
        before = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        subprocess.run(["docker", "system", "prune", "-af"], capture_output=True, timeout=120)
        after = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        print(f"--- {tid} (disk: {before.stdout.splitlines()[-1].split()[3]} → {after.stdout.splitlines()[-1].split()[3]} free) ---")

        r = smoke_test(tid)
        results.append(r)
        print(f"  result: ok={r['ok']} — {r.get('summary', 'n/a')}")
        for n in r["nodes"]:
            print(f"    {n['name']}: {n['status']}", end="")
            if n.get("web_status"):
                print(f"   web_status={n['web_status']}", end="")
            print()
        if r["errors"]:
            print(f"  errors: {r['errors']}")
        print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        flag = "✓" if r["ok"] else "✗"
        print(f"  {flag} {r['template_id']}: {r.get('summary', 'failed')}")

    # Write full JSON for the agent to read back
    with open("/tmp/smoke_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nFull results written to /tmp/smoke_test_results.json")

    # 8. Disk hygiene — these images are HUGE (5-10 GB combined) and the
    #    smoke test is expected to be re-runnable. Without this, every run
    #    consumes another ~7 GB and eventually fills the disk.
    print("\n=== Reclaiming disk (prune dangling images + stopped containers) ===")
    subprocess.run(["docker", "system", "prune", "-f"], capture_output=True, timeout=60)
    df = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=10)
    print(df.stdout)


if __name__ == "__main__":
    main()
