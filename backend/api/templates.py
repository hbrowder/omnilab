import json, uuid
from fastapi import APIRouter, HTTPException
from core.database import get_db
router = APIRouter()
TEMPLATES = {
    "wazuh-soc": {"id":"wazuh-soc","name":"Wazuh SOC Lab","category":"security","description":"Wazuh SIEM + Kali attacker","difficulty":"intermediate","tags":["siem","wazuh"],"nodes":[{"name":"wazuh-manager","type":"docker","image":"wazuh/wazuh-manager:4.7.0","x":300,"y":100},{"name":"linux-agent","type":"docker","image":"ubuntu:22.04","x":150,"y":300},{"name":"kali-attacker","type":"docker","image":"kalilinux/kali-rolling","x":450,"y":300}],"links":[{"src":"linux-agent","dst":"wazuh-manager"},{"src":"kali-attacker","dst":"linux-agent"}]},
    "pentest-lab": {"id":"pentest-lab","name":"Pentest Lab","category":"security","description":"Kali + Metasploit + targets","difficulty":"intermediate","tags":["pentest","kali"],"nodes":[{"name":"kali","type":"docker","image":"kalilinux/kali-rolling","x":150,"y":200},{"name":"target","type":"docker","image":"tleemcjr/metasploitable2","x":400,"y":200}],"links":[{"src":"kali","dst":"target"}]},
    "kubernetes-cluster": {"id":"kubernetes-cluster","name":"Kubernetes Lab","category":"devops","description":"K8s cluster","difficulty":"intermediate","tags":["k8s"],"nodes":[{"name":"control","type":"qemu","image":None,"x":300,"y":100},{"name":"worker-1","type":"qemu","image":None,"x":150,"y":300},{"name":"worker-2","type":"qemu","image":None,"x":450,"y":300}],"links":[{"src":"control","dst":"worker-1"},{"src":"control","dst":"worker-2"}]},
    "ansible-lab": {"id":"ansible-lab","name":"Ansible Lab","category":"devops","description":"Ansible automation","difficulty":"beginner","tags":["ansible"],"nodes":[{"name":"controller","type":"docker","image":"cytopia/ansible:latest","x":300,"y":100},{"name":"node-1","type":"docker","image":"ubuntu:22.04","x":200,"y":300},{"name":"node-2","type":"docker","image":"ubuntu:22.04","x":400,"y":300}],"links":[{"src":"controller","dst":"node-1"},{"src":"controller","dst":"node-2"}]},
    "llm-sandbox": {"id":"llm-sandbox","name":"LLM Security Lab","category":"ai-ml","description":"Ollama + AI pentesting","difficulty":"intermediate","tags":["llm","ollama"],"nodes":[{"name":"ollama","type":"docker","image":"ollama/ollama:latest","x":300,"y":100},{"name":"webui","type":"docker","image":"ghcr.io/open-webui/open-webui:main","x":150,"y":300},{"name":"attacker","type":"docker","image":"python:3.11-slim","x":450,"y":300}],"links":[{"src":"webui","dst":"ollama"},{"src":"attacker","dst":"ollama"}]},
    "cicd-pipeline": {"id":"cicd-pipeline","name":"CI/CD Pipeline","category":"devops","description":"Gitea+Jenkins+Harbor","difficulty":"intermediate","tags":["cicd"],"nodes":[{"name":"gitea","type":"docker","image":"gitea/gitea:latest","x":150,"y":200},{"name":"jenkins","type":"docker","image":"jenkins/jenkins:lts","x":350,"y":200},{"name":"harbor","type":"docker","image":"goharbor/harbor-core","x":550,"y":200}],"links":[{"src":"gitea","dst":"jenkins"},{"src":"jenkins","dst":"harbor"}]},
    "threat-hunting": {"id":"threat-hunting","name":"Threat Hunting Lab","category":"security","description":"Suricata+Zeek+TheHive","difficulty":"advanced","tags":["ids","zeek"],"nodes":[{"name":"suricata","type":"docker","image":"jasonish/suricata:latest","x":200,"y":150},{"name":"zeek","type":"docker","image":"zeekurity/zeek:latest","x":400,"y":150},{"name":"thehive","type":"docker","image":"strangebee/thehive:5","x":300,"y":350}],"links":[{"src":"suricata","dst":"thehive"},{"src":"zeek","dst":"thehive"}]},
    "vyos-routing": {"id":"vyos-routing","name":"VyOS Routing Lab","category":"networking","description":"BGP/OSPF routing","difficulty":"intermediate","tags":["vyos","routing"],"nodes":[{"name":"r1","type":"qemu","image":None,"x":150,"y":200},{"name":"r2","type":"qemu","image":None,"x":400,"y":200},{"name":"pc1","type":"docker","image":"ubuntu:22.04","x":100,"y":400},{"name":"pc2","type":"docker","image":"ubuntu:22.04","x":450,"y":400}],"links":[{"src":"r1","dst":"r2"},{"src":"pc1","dst":"r1"},{"src":"pc2","dst":"r2"}]},
    "mlops-lab": {"id":"mlops-lab","name":"MLOps Lab","category":"ai-ml","description":"MLflow+Jupyter+MinIO","difficulty":"intermediate","tags":["mlops"],"nodes":[{"name":"jupyter","type":"docker","image":"jupyter/datascience-notebook","x":200,"y":150},{"name":"mlflow","type":"docker","image":"ghcr.io/mlflow/mlflow","x":400,"y":150},{"name":"minio","type":"docker","image":"minio/minio","x":300,"y":350}],"links":[{"src":"jupyter","dst":"mlflow"},{"src":"mlflow","dst":"minio"}]},
    "caldera": {"id":"caldera","name":"MITRE Caldera","category":"security","description":"ATT&CK adversary sim","difficulty":"advanced","tags":["caldera","mitre"],"nodes":[{"name":"caldera","type":"docker","image":"mitre/caldera:latest","x":300,"y":100},{"name":"agent-1","type":"docker","image":"ubuntu:22.04","x":150,"y":300},{"name":"agent-2","type":"docker","image":"ubuntu:22.04","x":450,"y":300}],"links":[{"src":"caldera","dst":"agent-1"},{"src":"caldera","dst":"agent-2"}]},
}

@router.get("/")
async def list_templates(category: str = None):
    t = list(TEMPLATES.values())
    if category: t = [x for x in t if x["category"] == category]
    return t

@router.get("/categories")
async def list_categories():
    cats = {}
    for t in TEMPLATES.values():
        cats[t["category"]] = cats.get(t["category"], 0) + 1
    return [{"name": k, "count": v} for k, v in cats.items()]

@router.get("/{template_id}")
async def get_template(template_id: str):
    t = TEMPLATES.get(template_id)
    if not t: raise HTTPException(status_code=404, detail="Template not found")
    return t

@router.post("/{template_id}/deploy")
async def deploy_template(template_id: str, lab_name: str = None):
    template = TEMPLATES.get(template_id)
    if not template: raise HTTPException(status_code=404, detail="Not found")
    lab_id = str(uuid.uuid4())
    async for db in get_db():
        await db.execute("INSERT INTO labs (id,name,description,category) VALUES (?,?,?,?)",
            (lab_id, lab_name or template["name"], template["description"], template["category"]))
        nm = {}
        for n in template["nodes"]:
            nid = str(uuid.uuid4())
            nm[n["name"]] = nid
            await db.execute("INSERT INTO nodes (id,lab_id,name,type,image,config,x,y) VALUES (?,?,?,?,?,?,?,?)",
                (nid,lab_id,n["name"],n["type"],n.get("image"),json.dumps({}),n["x"],n["y"]))
        for lnk in template.get("links",[]):
            s,d = nm.get(lnk["src"]),nm.get(lnk["dst"])
            if s and d:
                await db.execute("INSERT INTO links (id,lab_id,src_node_id,dst_node_id) VALUES (?,?,?,?)",
                    (str(uuid.uuid4()),lab_id,s,d))
        await db.commit()
    return {"lab_id":lab_id,"name":lab_name or template["name"],"nodes_created":len(template["nodes"]),"status":"created"}
