"""
EVE-NG to OmniLab Migration Tool

Converts EVE-NG labs (.unl files) to OmniLab format.

EVE-NG Lab Structure:
- Labs: /opt/unetlab/labs/*.unl (XML format)
- Images: /opt/unetlab/addons/qemu/<vendor-version>/virtioa.qcow2
- Configs: /opt/unetlab/tmp/<pod_id>/<lab_id>/<node_id>/startup-config

OmniLab Structure:
- Labs: PostgreSQL/SQLite (JSON)
- Images: ~/.omnilab/images/*.qcow2
- Configs: Embedded in node config JSON

Usage:
    # From EVE-NG server
    python3 migrate_from_eve.py export --lab-id 12345 --output ~/my-lab.zip
    
    # On OmniLab server
    python3 migrate_from_eve.py import --file my-lab.zip
"""
import argparse
import base64
import json
import os
import re
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Dict, List, Optional


# ── EVE-NG annotation (drawing) parsing ──────────────────────────────────────
#
# EVE-NG stores canvas drawings under <objects><textobjects>. Each <textobject>
# has type="text|circle|square" and a <data> element holding base64-encoded HTML
# (an absolutely-positioned <div>). Geometry lives in the div's inline CSS, not
# as XML attributes; shape color lives in an inner <svg> <ellipse>/<rect>.
# We decode that into OmniLab's flat textobjects schema
# (type/x/y/width/height/fill/stroke/text/z_index — see routes/textobjects.py).

# EVE-NG declares type="text|circle|square|shape". The shape primitive is not
# reliable from that attribute (a type="shape" can hold an <ellipse>), so for
# anything non-text we infer the OmniLab type from the inner SVG element.
# Fallback map for non-text objects with no recognizable SVG primitive.
ANNOTATION_TYPE_MAP = {"circle": "circle", "square": "rectangle"}


def _omni_type(eve_type: str, html: str) -> str:
    """Decide the OmniLab textobject type from EVE type + decoded SVG."""
    if eve_type == "text":
        return "text"
    if re.search(r"<(?:ellipse|circle)\b", html):
        return "circle"
    if re.search(r"<rect\b", html):
        return "rectangle"
    return ANNOTATION_TYPE_MAP.get(eve_type, "rectangle")

# OmniLab defaults (mirrors TextObjectCreate) — used for text, which has no shape fill
_DEFAULT_FILL = "rgba(88,166,255,0.3)"
_DEFAULT_STROKE = "rgba(88,166,255,1)"

_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_BREAK_RE = re.compile(r"</p>|</div>|<br\s*/?>", re.I)


def _parse_inline_style(style: str) -> Dict[str, str]:
    """Parse a CSS 'k: v; k: v' string into a lowercased dict."""
    out: Dict[str, str] = {}
    for part in (style or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def _px(val: Optional[str]) -> Optional[float]:
    """'176px' → 176.0 ; 'auto'/None/'' → None."""
    if not val:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", val)
    return float(m.group()) if m else None


def _html_to_text(inner_html: str) -> str:
    """Flatten CKEditor block HTML to plain text, block boundaries → newlines."""
    s = _BLOCK_BREAK_RE.sub("\n", inner_html)
    s = _TAG_RE.sub("", s)
    s = unescape(s).replace("\xa0", " ")
    lines = [ln.strip() for ln in s.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def parse_annotations(root: ET.Element) -> List[Dict]:
    """Convert EVE-NG <objects><textobjects> into OmniLab textobject dicts."""
    annotations: List[Dict] = []
    for to in root.findall(".//textobjects/textobject"):
        eve_type = (to.get("type") or "text").lower()

        data_b64 = (to.findtext("data") or "").strip()
        if not data_b64:
            continue
        try:
            html = base64.b64decode(data_b64).decode("utf-8", "replace")
        except Exception:
            continue

        omni_type = _omni_type(eve_type, html)

        # Geometry from the outer div's inline style (first style= wins)
        style_m = re.search(r'style="([^"]*)"', html)
        style = _parse_inline_style(style_m.group(1) if style_m else "")
        try:
            z_index = int(float(style.get("z-index", 0)))
        except (TypeError, ValueError):
            z_index = 0

        obj: Dict = {
            "type": omni_type,
            "x": _px(style.get("left")) or 0.0,
            "y": _px(style.get("top")) or 0.0,
            "width": _px(style.get("width")),
            "height": _px(style.get("height")),
            "z_index": z_index,
            "name": to.get("name", ""),
            "original_eve_id": to.get("id"),
        }

        if omni_type == "text":
            inner = re.sub(r"^<div\b[^>]*>", "", html.strip(), count=1)
            inner = re.sub(r"</div>\s*$", "", inner, count=1)
            obj["text"] = _html_to_text(inner)
            obj["fill"] = _DEFAULT_FILL
            obj["stroke"] = _DEFAULT_STROKE
        else:
            # Color from the SVG primitive. \bstroke=" won't match stroke-width=".
            shape_m = re.search(r"<(?:rect|ellipse)\b[^>]*>", html)
            shape_tag = shape_m.group(0) if shape_m else ""
            fill_m = re.search(r'\bfill="([^"]*)"', shape_tag)
            stroke_m = re.search(r'\bstroke="([^"]*)"', shape_tag)
            obj["fill"] = fill_m.group(1) if fill_m else "#FFFFFF"
            obj["stroke"] = stroke_m.group(1) if stroke_m else "#000000"
            obj["text"] = ""

        annotations.append(obj)
    return annotations


class EVENGMigrator:
    """Migrate labs from EVE-NG to OmniLab."""
    
    # EVE-NG template name → OmniLab template mapping
    TEMPLATE_MAP = {
        "iol": "cisco-iol",
        "viosl2": "cisco-iosvl2",
        "vios": "cisco-iosv",
        "csr1000v": "cisco-csr1000v",
        "asav": "cisco-asav",
        "vwlc": "cisco-vwlc",
        "vqfx": "juniper-vqfx",
        "vmx": "juniper-vmx",
        "vsrx": "juniper-vsrx",
        "veos": "arista-veos",
        "linux": "linux-generic",
        "vpcs": "vpcs",
        "paloalto": "palo-alto-panorama",
    }
    
    def __init__(self, eve_labs_dir="/opt/unetlab/labs", eve_images_dir="/opt/unetlab/addons/qemu"):
        self.eve_labs_dir = Path(eve_labs_dir)
        self.eve_images_dir = Path(eve_images_dir)
    
    def export_lab(self, lab_path: str, output_zip: str) -> Dict:
        """
        Export an EVE-NG lab to a portable ZIP format.
        
        ZIP structure:
            manifest.json       # Lab metadata
            lab.json            # OmniLab-compatible lab definition
            images/             # Referenced QEMU images
            configs/            # Node startup configs
        """
        lab_file = Path(lab_path)
        if not lab_file.exists():
            raise FileNotFoundError(f"Lab file not found: {lab_path}")
        
        print(f"📦 Exporting EVE-NG lab: {lab_file.name}")
        
        # Parse EVE-NG .unl file (XML)
        tree = ET.parse(lab_file)
        root = tree.getroot()
        
        lab_name = root.get("name", lab_file.stem)
        lab_version = root.get("version", "1")
        lab_author = root.get("author", "unknown")
        lab_description = root.findtext("description", "")
        
        # Convert nodes
        nodes = []
        images_needed = set()
        
        for node_elem in root.findall(".//node"):
            node_type = node_elem.get("template")
            node_name = node_elem.get("name")
            node_id = node_elem.get("id")
            
            # Map to OmniLab template
            omni_template = self.TEMPLATE_MAP.get(node_type, "linux-generic")
            
            # Extract config
            config_path = node_elem.get("config")
            startup_config = ""
            if config_path:
                config_file = self.eve_labs_dir / config_path
                if config_file.exists():
                    startup_config = config_file.read_text()
            
            # Image reference
            image = node_elem.get("image", "")
            if image:
                images_needed.add(image)
            
            node_data = {
                "id": str(uuid.uuid4()),
                "name": node_name,
                "type": omni_template,
                "image": image,
                "left": int(node_elem.get("left", 100)),
                "top": int(node_elem.get("top", 100)),
                "cpu": int(node_elem.get("cpu", 1)),
                "ram": int(node_elem.get("ram", 512)),
                "console": node_elem.get("console", "telnet"),
                "config": startup_config,
                "original_eve_id": node_id,
                "original_eve_template": node_type,
            }
            nodes.append(node_data)
        
        # Convert networks
        networks = []
        for network_elem in root.findall(".//network"):
            net_id = network_elem.get("id")
            net_name = network_elem.get("name", f"Net-{net_id}")
            net_type = network_elem.get("type", "bridge")
            
            network_data = {
                "id": str(uuid.uuid4()),
                "name": net_name,
                "type": net_type,
                "visibility": int(network_elem.get("visibility", 1)),
                "original_eve_id": net_id,
            }
            networks.append(network_data)

        # Convert annotations (drawing-tool text/shapes)
        annotations = parse_annotations(root)

        # Build OmniLab lab JSON
        omni_lab = {
            "id": str(uuid.uuid4()),
            "name": lab_name,
            "description": lab_description,
            "author": lab_author,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "nodes": nodes,
            "networks": networks,
            "textobjects": annotations,
            "metadata": {
                "migrated_from": "eve-ng",
                "eve_version": lab_version,
                "migration_date": datetime.utcnow().isoformat(),
            }
        }
        
        # Create ZIP archive
        output_path = Path(output_zip)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Write manifest
            manifest = {
                "format": "omnilab-migration",
                "version": "1.0",
                "source": "eve-ng",
                "lab_name": lab_name,
                "node_count": len(nodes),
                "network_count": len(networks),
                "annotation_count": len(annotations),
                "images": list(images_needed),
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            
            # Write lab definition
            zf.writestr("lab.json", json.dumps(omni_lab, indent=2))
            
            # Copy referenced images (if available)
            for image_name in images_needed:
                image_path = self.find_eve_image(image_name)
                if image_path:
                    zf.write(image_path, f"images/{image_name}")
                    print(f"  ✓ Packed image: {image_name}")
                else:
                    print(f"  ⚠ Image not found (manual copy needed): {image_name}")
        
        print(f"\n✅ Export complete: {output_path}")
        print(f"   Nodes: {len(nodes)}, Networks: {len(networks)}, Annotations: {len(annotations)}")
        print(f"   Images: {len(images_needed)} referenced")
        
        return manifest
    
    def find_eve_image(self, image_name: str) -> Optional[Path]:
        """Find an EVE-NG image by name."""
        # EVE-NG images are in /opt/unetlab/addons/qemu/<vendor-version>/virtioa.qcow2
        for vendor_dir in self.eve_images_dir.glob("*"):
            image_file = vendor_dir / "virtioa.qcow2"
            if image_file.exists():
                # Check if this matches the requested image (name heuristic)
                if image_name in vendor_dir.name or vendor_dir.name in image_name:
                    return image_file
        return None
    
    def import_lab(self, zip_path: str, omnilab_api_url: str = "http://localhost:5000", token: Optional[str] = None):
        """
        Import a migrated lab ZIP into OmniLab.
        
        Uses OmniLab API to create lab + upload images.
        """
        import requests
        
        zip_file = Path(zip_path)
        if not zip_file.exists():
            raise FileNotFoundError(f"Migration archive not found: {zip_path}")
        
        print(f"📥 Importing lab from: {zip_file.name}")
        
        with zipfile.ZipFile(zip_file, 'r') as zf:
            # Read manifest
            manifest = json.loads(zf.read("manifest.json"))
            print(f"   Lab: {manifest['lab_name']}")
            print(f"   Source: {manifest['source']}")
            print(f"   Nodes: {manifest['node_count']}, Networks: {manifest['network_count']}, "
                  f"Annotations: {manifest.get('annotation_count', 0)}")
            
            # Read lab definition
            lab_data = json.loads(zf.read("lab.json"))
            
            # Extract to temp directory
            temp_dir = Path("/tmp") / f"omnilab-import-{uuid.uuid4().hex[:8]}"
            zf.extractall(temp_dir)
        
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        # Upload images first
        print("\n📦 Uploading images...")
        image_dir = temp_dir / "images"
        if image_dir.exists():
            for image_file in image_dir.glob("*.qcow2"):
                print(f"   Uploading {image_file.name}...")
                with open(image_file, 'rb') as f:
                    files = {"file": (image_file.name, f, "application/octet-stream")}
                    r = requests.post(
                        f"{omnilab_api_url}/api/template-library/upload",
                        files=files,
                        headers=headers,
                        timeout=300  # Large files
                    )
                    if r.status_code in (200, 201):
                        print(f"   ✓ {image_file.name}")
                    else:
                        print(f"   ✗ Failed: {r.text}")
        
        # Create lab via API
        print(f"\n🧪 Creating lab: {lab_data['name']}")
        r = requests.post(
            f"{omnilab_api_url}/api/labs/",
            json={
                "name": lab_data["name"],
                "description": lab_data["description"],
            },
            headers=headers
        )
        
        if r.status_code not in (200, 201):
            print(f"❌ Lab creation failed: {r.text}")
            return
        
        lab_id = r.json()["id"]
        print(f"   ✓ Lab ID: {lab_id}")
        
        # Create nodes
        print(f"\n🖥️  Creating {len(lab_data['nodes'])} nodes...")
        for node in lab_data["nodes"]:
            # Parse config if it's a string
            config = node.get("config", {})
            if isinstance(config, str):
                config = json.loads(config) if config else {}
            
            r = requests.post(
                f"{omnilab_api_url}/api/nodes/",
                json={
                    "lab_id": lab_id,
                    "name": node["name"],
                    "type": node["type"],
                    "image": node["image"],
                    "x": node["left"],
                    "y": node["top"],
                    "config": config,
                },
                headers=headers
            )
            if r.status_code in (200, 201):
                print(f"   ✓ {node['name']} ({node['type']})")
            else:
                print(f"   ✗ {node['name']} ({node['type']}) - {r.status_code}: {r.text[:100]}")

        # Create annotations (drawing-tool text/shapes)
        annotations = lab_data.get("textobjects", [])
        if annotations:
            print(f"\n🎨 Creating {len(annotations)} annotations...")
            fields = ("type", "x", "y", "width", "height", "fill", "stroke", "text", "z_index")
            created = 0
            for obj in annotations:
                body = {k: obj[k] for k in fields if obj.get(k) is not None}
                r = requests.post(
                    f"{omnilab_api_url}/api/labs/{lab_id}/textobjects",
                    json=body,
                    headers=headers,
                )
                if r.status_code in (200, 201):
                    created += 1
                else:
                    label = obj.get("name") or obj.get("type")
                    print(f"   ✗ {label} - {r.status_code}: {r.text[:100]}")
            print(f"   ✓ {created}/{len(annotations)} annotations")

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        print(f"\n✅ Import complete!")
        print(f"   Lab URL: {omnilab_api_url}/labs/{lab_id}")


class GNS3Migrator:
    """Migrate labs from GNS3 to OmniLab."""
    
    def export_lab(self, gns3_project_path: str, output_zip: str):
        """
        Export a GNS3 project to OmniLab format.
        
        GNS3 project structure:
            project.gns3        # JSON project file
            project-files/      # Node configs, images
        """
        project_dir = Path(gns3_project_path)
        project_file = project_dir / "project.gns3"
        
        if not project_file.exists():
            # Try .gns3project extension
            project_file = project_dir.with_suffix(".gns3project")
        
        if not project_file.exists():
            raise FileNotFoundError(f"GNS3 project file not found in {project_dir}")
        
        print(f"📦 Exporting GNS3 project: {project_dir.name}")
        
        with open(project_file) as f:
            gns3_data = json.load(f)
        
        lab_name = gns3_data.get("name", project_dir.name)
        
        # Convert nodes
        nodes = []
        for node in gns3_data.get("topology", {}).get("nodes", []):
            node_type = node.get("node_type", "qemu")
            
            node_data = {
                "id": str(uuid.uuid4()),
                "name": node.get("name"),
                "type": node.get("properties", {}).get("qemu_path", "linux-generic"),
                "left": node.get("x", 0),
                "top": node.get("y", 0),
                "cpu": node.get("properties", {}).get("cpus", 1),
                "ram": node.get("properties", {}).get("ram", 512),
                "console": node.get("console_type", "telnet"),
                "original_gns3_id": node.get("node_id"),
            }
            nodes.append(node_data)
        
        # Convert links
        networks = []
        for link in gns3_data.get("topology", {}).get("links", []):
            network_data = {
                "id": str(uuid.uuid4()),
                "name": f"Link-{link.get('link_id', '')}",
                "type": "bridge",
                "original_gns3_id": link.get("link_id"),
            }
            networks.append(network_data)
        
        # Build OmniLab lab
        omni_lab = {
            "id": str(uuid.uuid4()),
            "name": lab_name,
            "description": f"Migrated from GNS3 project: {lab_name}",
            "nodes": nodes,
            "networks": networks,
            "metadata": {
                "migrated_from": "gns3",
                "migration_date": datetime.utcnow().isoformat(),
            }
        }
        
        # Create ZIP
        output_path = Path(output_zip)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            manifest = {
                "format": "omnilab-migration",
                "version": "1.0",
                "source": "gns3",
                "lab_name": lab_name,
                "node_count": len(nodes),
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("lab.json", json.dumps(omni_lab, indent=2))
        
        print(f"✅ Export complete: {output_path}")
        return manifest


def main():
    parser = argparse.ArgumentParser(description="Migrate labs from EVE-NG/GNS3 to OmniLab")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # EVE-NG export
    eve_export = subparsers.add_parser("export-eve", help="Export EVE-NG lab to ZIP")
    eve_export.add_argument("--lab", required=True, help="Path to EVE-NG .unl file")
    eve_export.add_argument("--output", required=True, help="Output ZIP file path")
    
    # GNS3 export
    gns3_export = subparsers.add_parser("export-gns3", help="Export GNS3 project to ZIP")
    gns3_export.add_argument("--project", required=True, help="Path to GNS3 project directory")
    gns3_export.add_argument("--output", required=True, help="Output ZIP file path")
    
    # Import
    import_cmd = subparsers.add_parser("import", help="Import lab ZIP into OmniLab")
    import_cmd.add_argument("--file", required=True, help="Migration ZIP file")
    import_cmd.add_argument("--api", default="http://localhost:5000", help="OmniLab API URL")
    import_cmd.add_argument("--token", help="Auth token (for multi-user deployments)")
    
    args = parser.parse_args()
    
    if args.command == "export-eve":
        migrator = EVENGMigrator()
        migrator.export_lab(args.lab, args.output)
    
    elif args.command == "export-gns3":
        migrator = GNS3Migrator()
        migrator.export_lab(args.project, args.output)
    
    elif args.command == "import":
        migrator = EVENGMigrator()  # Importer is platform-agnostic
        migrator.import_lab(args.file, args.api, args.token)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
