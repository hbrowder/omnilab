"""Lab template catalog + deploy endpoint (CRE-39 phase 4).

Each template lists its nodes with everything needed to actually provision
them at deploy time:

- ``type``: ``"docker"`` or ``"qemu"``
- ``image``: docker image ref or qemu disk image path
- ``x`` / ``y``: canvas position
- ``docker_options`` (optional): per-image quirks merged into the docker run
  kwargs at start time. Examples: ``cap_add=NET_ADMIN`` for Kali, volume mounts
  for Wazuh, environment vars for Caldera/Jenkins. Audited at template-
  definition time so privilege escalations are loud and reviewable.
- ``web_port`` (optional): container-internal port the web-UI reverse proxy
  forwards to. Set only on nodes that actually expose a browser-facing UI.
- ``web_scheme`` (optional): ``"http"`` (default) or ``"https"``.

Templates flagged ``"coming_soon": True`` are returned in the list (so the UI
can show them as "Pro / Coming Soon") but ``deploy`` refuses to provision
them — these are the two QEMU-based templates that need cloud-init + OVS
bridging work (CRE-40, v1.1 scope).

On deploy, ``docker_options``/``web_port``/``web_scheme`` are persisted into
the ``nodes.config`` JSON column where ``api/nodes.py`` and ``api/web_proxy.py``
already read them from.
"""

import json
import uuid

from core.database import get_db
from fastapi import APIRouter, HTTPException

router = APIRouter()


TEMPLATES = {
    # ============================================================ security ===
    "wazuh-soc": {
        "id": "wazuh-soc",
        "name": "Wazuh SOC Lab",
        "category": "security",
        "description": "Wazuh SIEM + Linux endpoint + Kali attacker. Practice"
        " SOC analyst workflows: tail alerts, investigate, write detection rules.",
        "difficulty": "intermediate",
        "tags": ["siem", "wazuh", "blue-team"],
        "nodes": [
            {
                "name": "wazuh-manager",
                "type": "docker",
                "image": "wazuh/wazuh-manager:4.7.0",
                "x": 300,
                "y": 100,
                "web_port": 443,
                "web_scheme": "https",
                "docker_options": {
                    # Wazuh manager listens on tcp/1514 (agents) and 55000 (API);
                    # the dashboard reverse-proxies through 443.
                    "environment": {
                        "INDEXER_URL": "https://wazuh-indexer:9200",
                        "INDEXER_USERNAME": "admin",
                        "INDEXER_PASSWORD": "SecretPassword",
                    },
                },
            },
            {
                "name": "linux-agent",
                "type": "docker",
                "image": "ubuntu:22.04",
                "x": 150,
                "y": 300,
                "docker_options": {
                    # Keep the container alive — ubuntu's default cmd exits.
                    "command": ["sleep", "infinity"],
                    "tty": True,
                },
            },
            {
                "name": "kali-attacker",
                "type": "docker",
                "image": "kalilinux/kali-rolling",
                "x": 450,
                "y": 300,
                "docker_options": {
                    "cap_add": ["NET_ADMIN", "NET_RAW"],
                    "command": ["sleep", "infinity"],
                    "tty": True,
                },
            },
        ],
        "links": [
            {"src": "linux-agent", "dst": "wazuh-manager"},
            {"src": "kali-attacker", "dst": "linux-agent"},
        ],
    },
    "pentest-lab": {
        "id": "pentest-lab",
        "name": "Pentest Lab",
        "category": "security",
        "description": "Kali Linux attacker (with nmap, nc, hydra pre-installed) "
        "against a vulnerable target. The classic intro pentest lab: scan, exploit, root.",
        "difficulty": "beginner",
        "tags": ["pentest", "kali", "metasploit", "red-team"],
        "nodes": [
            {
                "name": "kali",
                "type": "docker",
                "image": "kalilinux/kali-rolling",
                "x": 150,
                "y": 200,
                "docker_options": {
                    # NET_ADMIN + NET_RAW required for nmap SYN scans and
                    # raw-socket exploits. NOT privileged=True — we don't
                    # need full host access.
                    "cap_add": ["NET_ADMIN", "NET_RAW"],
                    # kali-rolling is the slim variant — base image has no
                    # security tools. Install the essentials on first boot
                    # then sleep. The install is cached as a docker layer
                    # after first deploy if we ever build a derived image;
                    # for v1.0 we accept the ~45s install on first start.
                    "command": [
                        "bash", "-c",
                        "DEBIAN_FRONTEND=noninteractive apt-get update -qq && "
                        "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "
                        "nmap netcat-traditional iputils-ping hydra curl wget "
                        "dnsutils python3 git vim less >/dev/null 2>&1 || true && "
                        "echo 'kali ready' && sleep infinity",
                    ],
                    "tty": True,
                },
            },
            {
                "name": "target",
                "type": "docker",
                # vulhub-style intentionally-vulnerable web app — actually stays
                # running (unlike tleemcjr/metasploitable2 which exits after boot).
                # DVWA is a Damn Vulnerable Web App — has SQL injection, XSS,
                # command injection, file upload, etc. Perfect demo target:
                # instructor can show nmap finds open port 80, curl returns
                # vulnerable HTTP, then walk through an actual exploit.
                "image": "vulnerables/web-dvwa",
                "x": 400,
                "y": 200,
                "web_port": 80,
                # No command override — DVWA's default entrypoint (apache +
                # mysql) keeps the container alive.
            },
        ],
        "links": [{"src": "kali", "dst": "target"}],
    },
    "threat-hunting": {
        "id": "threat-hunting",
        "name": "Threat Hunting Lab",
        "category": "security",
        "description": "Suricata + Zeek IDS feeding TheHive case management."
        " Detect, triage, and document.",
        "difficulty": "advanced",
        "tags": ["ids", "zeek", "suricata", "thehive", "blue-team"],
        "nodes": [
            {
                "name": "suricata",
                "type": "docker",
                "image": "jasonish/suricata:latest",
                "x": 200,
                "y": 150,
                "docker_options": {
                    "cap_add": ["NET_ADMIN", "SYS_NICE"],
                },
            },
            {
                "name": "zeek",
                "type": "docker",
                "image": "zeekurity/zeek:latest",
                "x": 400,
                "y": 150,
                "docker_options": {
                    "cap_add": ["NET_ADMIN", "NET_RAW"],
                },
            },
            {
                "name": "thehive",
                "type": "docker",
                "image": "strangebee/thehive:5",
                "x": 300,
                "y": 350,
                "web_port": 9000,
            },
        ],
        "links": [
            {"src": "suricata", "dst": "thehive"},
            {"src": "zeek", "dst": "thehive"},
        ],
    },
    "caldera": {
        "id": "caldera",
        "name": "MITRE Caldera",
        "category": "security",
        "description": "Adversary emulation against two Ubuntu targets."
        " Walk through MITRE ATT&CK techniques end-to-end.",
        "difficulty": "advanced",
        "tags": ["caldera", "mitre", "att&ck", "red-team"],
        "nodes": [
            {
                "name": "caldera",
                "type": "docker",
                "image": "mitre/caldera:latest",
                "x": 300,
                "y": 100,
                "web_port": 8888,
                "docker_options": {
                    "environment": {
                        # Caldera pulls technique manifests from GitHub at
                        # boot — needs outbound internet.
                        "CALDERA_HOST": "0.0.0.0",
                    },
                },
            },
            {
                "name": "agent-1",
                "type": "docker",
                "image": "ubuntu:22.04",
                "x": 150,
                "y": 300,
                "docker_options": {
                    "command": ["sleep", "infinity"],
                    "tty": True,
                },
            },
            {
                "name": "agent-2",
                "type": "docker",
                "image": "ubuntu:22.04",
                "x": 450,
                "y": 300,
                "docker_options": {
                    "command": ["sleep", "infinity"],
                    "tty": True,
                },
            },
        ],
        "links": [
            {"src": "caldera", "dst": "agent-1"},
            {"src": "caldera", "dst": "agent-2"},
        ],
    },
    # ============================================================== devops ===
    "ansible-lab": {
        "id": "ansible-lab",
        "name": "Ansible Lab",
        "category": "devops",
        "description": "Ansible controller pushing playbooks to two Ubuntu"
        " managed nodes. Practice idempotent provisioning.",
        "difficulty": "beginner",
        "tags": ["ansible", "automation"],
        "nodes": [
            {
                "name": "controller",
                "type": "docker",
                "image": "cytopia/ansible:latest",
                "x": 300,
                "y": 100,
                "docker_options": {
                    "command": ["sleep", "infinity"],
                    "tty": True,
                },
            },
            {
                "name": "node-1",
                "type": "docker",
                "image": "ubuntu:22.04",
                "x": 200,
                "y": 300,
                "docker_options": {
                    "command": ["sleep", "infinity"],
                    "tty": True,
                },
            },
            {
                "name": "node-2",
                "type": "docker",
                "image": "ubuntu:22.04",
                "x": 400,
                "y": 300,
                "docker_options": {
                    "command": ["sleep", "infinity"],
                    "tty": True,
                },
            },
        ],
        "links": [
            {"src": "controller", "dst": "node-1"},
            {"src": "controller", "dst": "node-2"},
        ],
    },
    "cicd-pipeline": {
        "id": "cicd-pipeline",
        "name": "CI/CD Pipeline",
        "category": "devops",
        "description": "Gitea source hosting → Jenkins build server → Harbor"
        " container registry. Full pipeline in one lab.",
        "difficulty": "intermediate",
        "tags": ["cicd", "jenkins", "gitea", "harbor"],
        "nodes": [
            {
                "name": "gitea",
                "type": "docker",
                "image": "gitea/gitea:latest",
                "x": 150,
                "y": 200,
                "web_port": 3000,
            },
            {
                "name": "jenkins",
                "type": "docker",
                "image": "jenkins/jenkins:lts",
                "x": 350,
                "y": 200,
                "web_port": 8080,
            },
            {
                "name": "harbor",
                "type": "docker",
                "image": "goharbor/harbor-core",
                "x": 550,
                "y": 200,
                "web_port": 80,
            },
        ],
        "links": [
            {"src": "gitea", "dst": "jenkins"},
            {"src": "jenkins", "dst": "harbor"},
        ],
    },
    # ============================================================== ai-ml ===
    "llm-sandbox": {
        "id": "llm-sandbox",
        "name": "LLM Security Lab",
        "category": "ai-ml",
        "description": "Ollama local model server + Open-WebUI chat frontend"
        " + Python attacker. Practice prompt-injection and jailbreak hardening.",
        "difficulty": "intermediate",
        "tags": ["llm", "ollama", "open-webui", "ai-security"],
        "nodes": [
            {
                "name": "ollama",
                "type": "docker",
                "image": "ollama/ollama:latest",
                "x": 300,
                "y": 100,
                "web_port": 11434,
            },
            {
                "name": "webui",
                "type": "docker",
                "image": "ghcr.io/open-webui/open-webui:main",
                "x": 150,
                "y": 300,
                "web_port": 8080,
                "docker_options": {
                    "environment": {
                        "OLLAMA_BASE_URL": "http://ollama:11434",
                    },
                },
            },
            {
                "name": "attacker",
                "type": "docker",
                "image": "python:3.11-slim",
                "x": 450,
                "y": 300,
                "docker_options": {
                    "command": ["sleep", "infinity"],
                    "tty": True,
                },
            },
        ],
        "links": [
            {"src": "webui", "dst": "ollama"},
            {"src": "attacker", "dst": "ollama"},
        ],
    },
    "mlops-lab": {
        "id": "mlops-lab",
        "name": "MLOps Lab",
        "category": "ai-ml",
        "description": "Jupyter notebooks + MLflow experiment tracker + MinIO"
        " artifact store. End-to-end model lifecycle.",
        "difficulty": "intermediate",
        "tags": ["mlops", "mlflow", "jupyter", "minio"],
        "nodes": [
            {
                "name": "jupyter",
                "type": "docker",
                "image": "jupyter/datascience-notebook",
                "x": 200,
                "y": 150,
                "web_port": 8888,
                "docker_options": {
                    "environment": {
                        # Disable token auth so the proxy can hit it directly.
                        # Lab-only; not for production exposure.
                        "JUPYTER_TOKEN": "",
                        "JUPYTER_ENABLE_LAB": "yes",
                    },
                },
            },
            {
                "name": "mlflow",
                "type": "docker",
                "image": "ghcr.io/mlflow/mlflow",
                "x": 400,
                "y": 150,
                "web_port": 5000,
                "docker_options": {
                    "command": [
                        "mlflow", "server",
                        "--host", "0.0.0.0",
                        "--backend-store-uri", "sqlite:///mlflow.db",
                    ],
                },
            },
            {
                "name": "minio",
                "type": "docker",
                "image": "minio/minio",
                "x": 300,
                "y": 350,
                "web_port": 9001,
                "docker_options": {
                    "command": [
                        "server", "/data",
                        "--console-address", ":9001",
                    ],
                    "environment": {
                        "MINIO_ROOT_USER": "minioadmin",
                        "MINIO_ROOT_PASSWORD": "minioadmin",
                    },
                },
            },
        ],
        "links": [
            {"src": "jupyter", "dst": "mlflow"},
            {"src": "mlflow", "dst": "minio"},
        ],
    },
    # ============================================ coming soon (v1.1, CRE-40) ===
    "kubernetes-cluster": {
        "id": "kubernetes-cluster",
        "name": "Kubernetes Lab",
        "category": "devops",
        "description": "Multi-node Kubernetes cluster (control + 2 workers)."
        " Requires QEMU + cloud-init — coming in v1.1.",
        "difficulty": "intermediate",
        "tags": ["k8s", "kubernetes", "devops"],
        "coming_soon": True,
        "nodes": [
            {"name": "control", "type": "qemu", "image": None, "x": 300, "y": 100},
            {"name": "worker-1", "type": "qemu", "image": None, "x": 150, "y": 300},
            {"name": "worker-2", "type": "qemu", "image": None, "x": 450, "y": 300},
        ],
        "links": [
            {"src": "control", "dst": "worker-1"},
            {"src": "control", "dst": "worker-2"},
        ],
    },
    "vyos-routing": {
        "id": "vyos-routing",
        "name": "VyOS Routing Lab",
        "category": "networking",
        "description": "BGP/OSPF routing with two VyOS routers and two Linux"
        " hosts. Requires QEMU + OVS bridging — coming in v1.1.",
        "difficulty": "intermediate",
        "tags": ["vyos", "routing", "bgp", "ospf", "networking"],
        "coming_soon": True,
        "nodes": [
            {"name": "r1", "type": "qemu", "image": None, "x": 150, "y": 200},
            {"name": "r2", "type": "qemu", "image": None, "x": 400, "y": 200},
            {"name": "pc1", "type": "docker", "image": "ubuntu:22.04", "x": 100, "y": 400},
            {"name": "pc2", "type": "docker", "image": "ubuntu:22.04", "x": 450, "y": 400},
        ],
        "links": [
            {"src": "r1", "dst": "r2"},
            {"src": "pc1", "dst": "r1"},
            {"src": "pc2", "dst": "r2"},
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_NODE_CONFIG_KEYS = ("docker_options", "web_port", "web_scheme")


def _node_config_payload(node: dict) -> dict:
    """Extract the per-node config that gets serialized into nodes.config JSON.

    Pulled out so it's testable in isolation and so future config fields
    (e.g. ``host_port``) can be added in one place.
    """
    cfg: dict = {}
    for key in _NODE_CONFIG_KEYS:
        if key in node and node[key] is not None:
            cfg[key] = node[key]
    return cfg


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/")
async def list_templates(category: str | None = None):
    t = list(TEMPLATES.values())
    if category:
        t = [x for x in t if x["category"] == category]
    return t


@router.get("/categories")
async def list_categories():
    cats: dict[str, int] = {}
    for t in TEMPLATES.values():
        cats[t["category"]] = cats.get(t["category"], 0) + 1
    return [{"name": k, "count": v} for k, v in cats.items()]


@router.get("/{template_id}")
async def get_template(template_id: str):
    t = TEMPLATES.get(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.post("/{template_id}/deploy")
async def deploy_template(template_id: str, lab_name: str | None = None):
    template = TEMPLATES.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Refuse to deploy "Pro / Coming Soon" templates — UI should also gate this
    # but the backend is the source of truth.
    if template.get("coming_soon"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Template '{template_id}' is not yet available (Pro / Coming"
                " Soon — see CRE-40 / v1.1)."
            ),
        )

    lab_id = str(uuid.uuid4())
    async for db in get_db():
        await db.execute(
            "INSERT INTO labs (id,name,description,category) VALUES (?,?,?,?)",
            (
                lab_id,
                lab_name or template["name"],
                template["description"],
                template["category"],
            ),
        )
        nm: dict[str, str] = {}
        for n in template["nodes"]:
            nid = str(uuid.uuid4())
            nm[n["name"]] = nid
            cfg_payload = _node_config_payload(n)
            await db.execute(
                "INSERT INTO nodes (id,lab_id,name,type,image,config,x,y)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (
                    nid,
                    lab_id,
                    n["name"],
                    n["type"],
                    n.get("image"),
                    json.dumps(cfg_payload),
                    n["x"],
                    n["y"],
                ),
            )
        for lnk in template.get("links", []):
            s, d = nm.get(lnk["src"]), nm.get(lnk["dst"])
            if s and d:
                await db.execute(
                    "INSERT INTO links (id,lab_id,src_node_id,dst_node_id)"
                    " VALUES (?,?,?,?)",
                    (str(uuid.uuid4()), lab_id, s, d),
                )
        await db.commit()
    return {
        "lab_id": lab_id,
        "name": lab_name or template["name"],
        "nodes_created": len(template["nodes"]),
        "status": "created",
    }
