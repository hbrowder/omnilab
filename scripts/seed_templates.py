#!/usr/bin/env python3
"""
CRE-55: Seed built-in templates from templates.py to templates table.

Run once to populate the database with OmniLab's built-in Docker templates.
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add backend dir to path so we can import
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from core.database import get_db

# Built-in template definitions (extracted from api/templates.py)
BUILTIN_TEMPLATES = [
    {
        "id": "pentest-lab",
        "name": "Pentest Lab",
        "vendor": "OmniLab",
        "category": "security",
        "description": "Kali Linux attacker against DVWA vulnerable web app. Classic intro pentest lab.",
        "type": "docker",
        "image": "kalilinux/kali-rolling",
        "cpu": 2,
        "ram": 2048,
        "console_type": "telnet",
        "icon": "🔒",
        "config": {"tags": ["pentest", "kali", "red-team"], "difficulty": "beginner"},
    },
    {
        "id": "wazuh-soc",
        "name": "Wazuh SOC Lab",
        "vendor": "Wazuh",
        "category": "security",
        "description": "Wazuh SIEM + Linux endpoint + Kali attacker. SOC analyst workflows.",
        "type": "docker",
        "image": "wazuh/wazuh-manager:4.7.0",
        "cpu": 4,
        "ram": 4096,
        "console_type": "telnet",
        "icon": "🛡️",
        "config": {"tags": ["siem", "wazuh", "blue-team"], "difficulty": "intermediate"},
    },
    {
        "id": "threat-hunting",
        "name": "Threat Hunting Lab",
        "vendor": "OmniLab",
        "category": "security",
        "description": "Windows + Sysmon + ELK stack. Hunt for IOCs and lateral movement.",
        "type": "docker",
        "image": "ubuntu:22.04",
        "cpu": 4,
        "ram": 8192,
        "console_type": "rdp",
        "icon": "🔍",
        "config": {"tags": ["threat-hunting", "elk", "windows"], "difficulty": "advanced"},
    },
    {
        "id": "devsecops-pipeline",
        "name": "DevSecOps CI/CD Pipeline",
        "vendor": "OmniLab",
        "category": "devops",
        "description": "Jenkins + Trivy + SonarQube. Security gates in CI/CD.",
        "type": "docker",
        "image": "jenkins/jenkins:lts",
        "cpu": 2,
        "ram": 4096,
        "console_type": "telnet",
        "icon": "⚙️",
        "config": {"tags": ["cicd", "jenkins", "security"], "difficulty": "intermediate"},
    },
    {
        "id": "kubernetes-cluster",
        "name": "Kubernetes 3-Node Cluster",
        "vendor": "K8s",
        "category": "cloud",
        "description": "k3s control-plane + 2 workers. Learn pods, deployments, services.",
        "type": "docker",
        "image": "rancher/k3s:latest",
        "cpu": 2,
        "ram": 2048,
        "console_type": "telnet",
        "icon": "☸️",
        "config": {"tags": ["kubernetes", "k3s", "containers"], "difficulty": "intermediate"},
    },
    {
        "id": "malware-analysis",
        "name": "Malware Analysis Lab",
        "vendor": "REMnux",
        "category": "security",
        "description": "REMnux + FLARE VM. Reverse engineer malware safely.",
        "type": "docker",
        "image": "remnux/remnux-distro:focal",
        "cpu": 4,
        "ram": 8192,
        "console_type": "vnc",
        "icon": "🦠",
        "config": {"tags": ["malware", "reverse-engineering", "forensics"], "difficulty": "advanced"},
    },
    {
        "id": "red-team-c2",
        "name": "Red Team C2 Infrastructure",
        "vendor": "OmniLab",
        "category": "security",
        "description": "Havoc C2 + phishing server + domain fronting redirector.",
        "type": "docker",
        "image": "ubuntu:22.04",
        "cpu": 2,
        "ram": 4096,
        "console_type": "telnet",
        "icon": "🎯",
        "config": {"tags": ["red-team", "c2", "havoc"], "difficulty": "advanced"},
    },
    {
        "id": "cisco-ccna-lab",
        "name": "Cisco CCNA Lab (Coming Soon)",
        "vendor": "Cisco",
        "category": "networking",
        "description": "2x routers + 2x switches. CCNA practice (VLANs, OSPF, trunking).",
        "type": "qemu",
        "image": "/opt/unetlab/addons/qemu/vios-adventerprisek9-m/virtioa.qcow2",
        "cpu": 1,
        "ram": 512,
        "console_type": "telnet",
        "icon": "🌐",
        "config": {"tags": ["cisco", "ccna", "routing"], "difficulty": "beginner", "coming_soon": True},
    },
    {
        "id": "juniper-jncia-lab",
        "name": "Juniper JNCIA Lab (Coming Soon)",
        "vendor": "Juniper",
        "category": "networking",
        "description": "vMX routers + vSRX firewall. Junos CLI practice.",
        "type": "qemu",
        "image": "/opt/unetlab/addons/qemu/vmx-20.2R1/virtioa.qcow2",
        "cpu": 2,
        "ram": 4096,
        "console_type": "telnet",
        "icon": "🌲",
        "config": {"tags": ["juniper", "jncia", "junos"], "difficulty": "intermediate", "coming_soon": True},
    },
    {
        "id": "arista-veos-lab",
        "name": "Arista vEOS Lab (Coming Soon)",
        "vendor": "Arista",
        "category": "networking",
        "description": "vEOS switches for data-center networking (VXLAN, EVPN, BGP).",
        "type": "qemu",
        "image": "/opt/unetlab/addons/qemu/veos-4.25.0F/hda.qcow2",
        "cpu": 2,
        "ram": 2048,
        "console_type": "telnet",
        "icon": "🔌",
        "config": {"tags": ["arista", "veos", "datacenter"], "difficulty": "advanced", "coming_soon": True},
    },
]


async def seed_templates():
    """Seed built-in templates into the database."""
    async for db in get_db():
        now = datetime.utcnow().isoformat()
        
        for tmpl in BUILTIN_TEMPLATES:
            # Check if template already exists
            async with db.execute(
                "SELECT id FROM templates WHERE id = ?", (tmpl["id"],)
            ) as cur:
                if await cur.fetchone():
                    print(f"⏭️  Skip: {tmpl['name']} (already exists)")
                    continue
            
            try:
                await db.execute(
                    """INSERT INTO templates (
                        id, name, vendor, category, description, type, image,
                        cpu, ram, disk, console_type, icon, visible, is_builtin,
                        config, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 10, ?, ?, 1, 1, ?, ?, ?)""",
                    (
                        tmpl["id"],
                        tmpl["name"],
                        tmpl["vendor"],
                        tmpl["category"],
                        tmpl["description"],
                        tmpl["type"],
                        tmpl["image"],
                        tmpl["cpu"],
                        tmpl["ram"],
                        tmpl["console_type"],
                        tmpl.get("icon"),
                        json.dumps(tmpl["config"]),
                        now,
                        now,
                    ),
                )
                print(f"✅ Added: {tmpl['name']}")
            except Exception as e:
                print(f"❌ Error: {tmpl['name']} - {str(e)}")
        
        await db.commit()
        print(f"\n🎉 Seeded {len(BUILTIN_TEMPLATES)} built-in templates!")


if __name__ == "__main__":
    asyncio.run(seed_templates())
