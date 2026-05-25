#!/usr/bin/env python3
"""
Auto-discover EVE-NG images and create OmniLab templates.

Scans /opt/unetlab/addons/qemu/* directories and generates
template definitions for all detected images.

Usage:
    # Scan EVE-NG images
    python3 discover-eve-templates.py --eve-images /opt/unetlab/addons/qemu
    
    # Upload to OmniLab
    python3 discover-eve-templates.py \
        --eve-images /opt/unetlab/addons/qemu \
        --upload http://omnilab:5000 \
        --token "eyJhbG..."
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
import subprocess


class EVETemplateDiscovery:
    """Auto-discover EVE-NG templates."""
    
    # Vendor detection patterns (folder name → vendor)
    VENDOR_PATTERNS = {
        r'cisco|vios|iol|csr|asa': 'Cisco',
        r'juniper|vmx|vsrx|vqfx|vjunos': 'Juniper',
        r'arista|veos': 'Arista',
        r'palo|panorama': 'Palo Alto',
        r'fortinet|fortigate': 'Fortinet',
        r'checkpoint': 'Check Point',
        r'f5|bigip': 'F5',
        r'mikrotik': 'MikroTik',
        r'opnsense': 'OPNsense',
        r'pfsense': 'pfSense',
        r'vyos': 'VyOS',
        r'cumulus': 'Cumulus',
        r'ubuntu|debian|centos|rhel|fedora': 'Linux',
        r'windows|win': 'Microsoft',
    }
    
    # Category detection
    CATEGORY_PATTERNS = {
        r'router|vios|iol|csr|vmx|vsrx': 'Routing',
        r'switch|viosl2|vqfx': 'Switching',
        r'firewall|asa|asav|srx|fortigate': 'Security',
        r'load.?balance|bigip|f5': 'Load Balancer',
        r'linux|ubuntu|debian|centos': 'Linux',
        r'windows|win': 'Windows',
        r'vpcs': 'End Device',
    }
    
    def __init__(self, eve_images_dir: str = "/opt/unetlab/addons/qemu"):
        self.eve_images_dir = Path(eve_images_dir)
        if not self.eve_images_dir.exists():
            raise FileNotFoundError(f"EVE-NG images directory not found: {eve_images_dir}")
    
    def detect_vendor(self, folder_name: str) -> str:
        """Detect vendor from folder name."""
        folder_lower = folder_name.lower()
        for pattern, vendor in self.VENDOR_PATTERNS.items():
            if re.search(pattern, folder_lower):
                return vendor
        return "Other"
    
    def detect_category(self, folder_name: str) -> str:
        """Detect category from folder name."""
        folder_lower = folder_name.lower()
        for pattern, category in self.CATEGORY_PATTERNS.items():
            if re.search(pattern, folder_lower):
                return category
        return "Other"
    
    def extract_version(self, folder_name: str) -> Optional[str]:
        """Extract version from folder name."""
        # Common patterns: vendor-15.6.3, vendor-v1.2, vendor_1.0
        match = re.search(r'[_-]v?(\d+[\.\d]*)', folder_name)
        if match:
            return match.group(1)
        return None
    
    def get_image_size_gb(self, image_path: Path) -> float:
        """Get image size in GB."""
        if image_path.exists():
            size_bytes = image_path.stat().st_size
            return round(size_bytes / (1024**3), 2)
        return 0.0
    
    def discover_templates(self) -> List[Dict]:
        """Scan EVE-NG directory and discover all templates."""
        templates = []
        
        print(f"🔍 Scanning: {self.eve_images_dir}")
        print("")
        
        for vendor_dir in sorted(self.eve_images_dir.iterdir()):
            if not vendor_dir.is_dir():
                continue
            
            # Look for virtioa.qcow2 (EVE-NG standard)
            image_file = vendor_dir / "virtioa.qcow2"
            if not image_file.exists():
                # Try other common names
                for alt_name in ["hda.qcow2", "disk.qcow2", "sda.qcow2"]:
                    alt_path = vendor_dir / alt_name
                    if alt_path.exists():
                        image_file = alt_path
                        break
            
            if not image_file.exists():
                print(f"  ⊘ {vendor_dir.name} (no image file)")
                continue
            
            folder_name = vendor_dir.name
            vendor = self.detect_vendor(folder_name)
            category = self.detect_category(folder_name)
            version = self.extract_version(folder_name)
            size_gb = self.get_image_size_gb(image_file)
            
            # Build template name
            template_name = folder_name
            if version:
                template_name = f"{vendor} {folder_name.replace(version, '').strip('-_')} {version}"
            
            template = {
                "name": template_name,
                "vendor": vendor,
                "category": category,
                "version": version or "unknown",
                "type": "qemu",
                "image": image_file.name,
                "image_path": str(image_file),
                "size_gb": size_gb,
                "cpu": 1,  # Conservative defaults
                "ram": 512,
                "console_type": "telnet",
                "eve_folder": folder_name,
            }
            
            templates.append(template)
            print(f"  ✓ {template_name} ({vendor}, {category}, {size_gb} GB)")
        
        return templates
    
    def upload_to_omnilab(self, templates: List[Dict], api_url: str, token: Optional[str] = None):
        """Upload discovered templates to OmniLab."""
        import requests
        
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        print(f"\n📤 Uploading {len(templates)} templates to OmniLab...")
        print("")
        
        success = 0
        failed = 0
        
        for template in templates:
            # Upload image first
            image_path = template["image_path"]
            print(f"  Uploading {template['name']}...")
            
            try:
                # Upload image file
                with open(image_path, 'rb') as f:
                    files = {"file": (template["image"], f, "application/octet-stream")}
                    data = {
                        "name": template["name"],
                        "vendor": template["vendor"],
                        "category": template["category"],
                    }
                    r = requests.post(
                        f"{api_url}/api/template-library/upload",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=600  # Large files
                    )
                    
                    if r.status_code in (200, 201):
                        print(f"    ✓ Uploaded successfully")
                        success += 1
                    else:
                        print(f"    ✗ Failed: {r.status_code} - {r.text[:100]}")
                        failed += 1
            
            except Exception as e:
                print(f"    ✗ Error: {e}")
                failed += 1
        
        print("")
        print(f"Upload complete: {success} succeeded, {failed} failed")
        
        # Verify permissions
        print("\n✅ Verifying permissions...")
        r = requests.get(f"{api_url}/api/system/permissions", headers=headers)
        perm_data = r.json()
        
        if perm_data.get("status") == "ok":
            print(f"  ✓ All {perm_data['total_images']} images have correct permissions")
            print("  (No manual fixpermissions needed!)")
        else:
            print(f"  ⚠ Issues found: {perm_data.get('issues', [])}")
            print(f"  Auto-fixed: {perm_data.get('auto_fixed', [])}")


def main():
    parser = argparse.ArgumentParser(description="Auto-discover EVE-NG templates")
    parser.add_argument("--eve-images", default="/opt/unetlab/addons/qemu",
                       help="EVE-NG images directory")
    parser.add_argument("--upload", help="Upload to OmniLab API URL")
    parser.add_argument("--token", help="JWT token for OmniLab API")
    parser.add_argument("--output", help="Save templates JSON to file")
    
    args = parser.parse_args()
    
    try:
        discovery = EVETemplateDiscovery(args.eve_images)
        templates = discovery.discover_templates()
        
        print("")
        print("=" * 60)
        print(f"DISCOVERED {len(templates)} TEMPLATES")
        print("=" * 60)
        
        # Group by vendor
        by_vendor = {}
        for t in templates:
            vendor = t["vendor"]
            by_vendor.setdefault(vendor, []).append(t)
        
        for vendor in sorted(by_vendor.keys()):
            count = len(by_vendor[vendor])
            print(f"  {vendor}: {count} template(s)")
        
        # Save to file
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump(templates, f, indent=2)
            print(f"\n💾 Saved to: {output_path}")
        
        # Upload to OmniLab
        if args.upload:
            discovery.upload_to_omnilab(templates, args.upload, args.token)
        
        print("\n🎉 Discovery complete!")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
