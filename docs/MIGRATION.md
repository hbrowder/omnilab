# Migration Guide: EVE-NG / GNS3 → OmniLab

Complete guide for migrating your existing network labs from EVE-NG or GNS3 to OmniLab.

---

## 🎯 Why Migrate?

| Feature | EVE-NG | GNS3 | OmniLab |
|---------|--------|------|---------|
| **Permission Management** | Manual `fixpermissions` after every upload | Auto | Auto (no manual steps!) |
| **Image Upload** | SSH/SCP as root | GUI (limited) | API + GUI + CLI |
| **Multi-User** | Complex LDAP setup | None | Built-in JWT RBAC |
| **Template Management** | Hardcoded | JSON files | Database + API |
| **Lab Sharing** | Export/re-import | .gns3project files | Native share/clone API |
| **NAT Networks** | Manual iptables | Cloud nodes | One-click API |
| **Packet Capture** | tcpdump CLI | Built-in | API + WebSocket streaming |
| **Modern UI** | 2015 design | Desktop app | 2026 React SPA |

---

## 📦 Migration Methods

### Method 1: Automated Migration Tool (Recommended)

**From EVE-NG Server:**
```bash
# 1. Export lab to portable ZIP
cd /opt/unetlab/labs
python3 ~/omnilab/scripts/migrate_lab.py export-eve \
  --lab "My CCNA Lab.unl" \
  --output ~/ccna-lab.zip

# ZIP contains:
#   - manifest.json (metadata)
#   - lab.json (OmniLab format)
#   - images/*.qcow2 (referenced QEMU images)
#   - configs/* (startup configs)
```

**On OmniLab Server:**
```bash
# 2. Import into OmniLab
python3 ~/omnilab/scripts/migrate_lab.py import \
  --file ccna-lab.zip \
  --api http://localhost:5000 \
  --token "your-jwt-token"  # Optional if auth enabled

# Migration creates:
#   ✓ Lab in database
#   ✓ All nodes with configs
#   ✓ Networks/connections
#   ✓ Images uploaded to ~/.omnilab/images/
```

### Method 2: Manual Migration (Small Labs)

**Step 1:** Export from EVE-NG
```bash
# On EVE-NG server
cd /opt/unetlab/labs
tar -czf my-lab-export.tar.gz "My Lab.unl"

# Copy images manually
cp /opt/unetlab/addons/qemu/vios-15.6/virtioa.qcow2 ~/cisco-iosv-15.6.qcow2
```

**Step 2:** Create lab in OmniLab
```bash
# Use API or GUI
curl -X POST http://omnilab:5000/api/labs/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "My Lab", "description": "Migrated from EVE-NG"}'
```

**Step 3:** Upload images
```bash
curl -X POST http://omnilab:5000/api/template-library/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@cisco-iosv-15.6.qcow2" \
  -F "name=Cisco IOSv 15.6" \
  -F "vendor=Cisco" \
  -F "category=Networking"
```

**Step 4:** Recreate nodes via GUI or API

---

## 🔄 EVE-NG → OmniLab Mapping

### Templates

| EVE-NG Template | OmniLab Template |
|----------------|------------------|
| `iol` | `cisco-iol` |
| `viosl2` | `cisco-iosvl2` |
| `vios` | `cisco-iosv` |
| `csr1000v` | `cisco-csr1000v` |
| `asav` | `cisco-asav` |
| `vmx` | `juniper-vmx` |
| `vsrx` | `juniper-vsrx` |
| `vqfx` | `juniper-vqfx` |
| `veos` | `arista-veos` |
| `paloalto` | `palo-alto-panorama` |
| `linux` | `linux-generic` |
| `vpcs` | `vpcs` |

### Image Paths

**EVE-NG:**
```
/opt/unetlab/addons/qemu/vios-15.6/virtioa.qcow2
                             ↓
```

**OmniLab:**
```
~/.omnilab/images/cisco-iosv-15.6.qcow2
```

### Configs

**EVE-NG:** `/opt/unetlab/tmp/<pod>/<lab>/<node>/startup-config`  
**OmniLab:** Embedded in node JSON `config` field

---

## 🚀 GNS3 Migration

**From GNS3:**
```bash
# Export GNS3 project
python3 ~/omnilab/scripts/migrate_lab.py export-gns3 \
  --project ~/GNS3/projects/my-lab \
  --output ~/my-lab.zip

# Import to OmniLab (same as EVE-NG)
python3 ~/omnilab/scripts/migrate_lab.py import \
  --file my-lab.zip \
  --api http://localhost:5000
```

---

## ✅ Post-Migration Checklist

### 1. Verify Images
```bash
# Check all images have correct permissions (auto-fixed!)
curl http://localhost:5000/api/system/permissions
```

**Expected:**
```json
{
  "status": "ok",
  "total_images": 12,
  "issues": [],
  "auto_fixed": [],
  "message": "No manual fixpermissions needed!"
}
```

### 2. Test Labs
- [ ] Start each migrated lab
- [ ] Verify console access to nodes
- [ ] Test network connectivity
- [ ] Verify startup configs applied

### 3. Update Workflows

**Old (EVE-NG):**
```bash
# Every time you upload an image:
scp image.qcow2 root@eve:/opt/unetlab/addons/qemu/vendor-1.0/virtioa.qcow2
ssh root@eve '/opt/unetlab/wrappers/unl_wrapper -a fixpermissions'  # Manual!
```

**New (OmniLab):**
```bash
# One command, auto-permissions:
curl -X POST http://omnilab:5000/api/template-library/upload \
  -F "file=@image.qcow2" \
  -F "name=Vendor 1.0" \
  -F "vendor=Vendor"
# Done! No fixpermissions needed.
```

---

## 🆘 Troubleshooting

### "Image not found" during migration

**Cause:** EVE-NG image path doesn't match OmniLab detection heuristic.

**Fix:** Manually copy images:
```bash
# On EVE-NG server
cd /opt/unetlab/addons/qemu
tar -czf images-export.tar.gz */virtioa.qcow2

# On OmniLab server
tar -xzf images-export.tar.gz -C ~/.omnilab/images/
# Upload via API
```

### "Permission denied" after manual copy

**OmniLab auto-fixes this!**
```bash
curl -X POST http://localhost:5000/api/system/permissions/fix
```

Unlike EVE-NG, you'll rarely need this — upload API sets correct permissions automatically.

### "Node type not recognized"

**Cause:** Custom EVE-NG template not in mapping table.

**Fix:** Create custom template in OmniLab:
```bash
curl -X POST http://localhost:5000/api/template-library/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Custom Vendor",
    "type": "qemu",
    "image": "custom-vendor-1.0.qcow2",
    "vendor": "Custom",
    "category": "Networking",
    "cpu": 2,
    "ram": 2048
  }'
```

---

## 📊 Migration Example

**EVE-NG Lab:** `CCNA Lab.unl` (15 routers, 10 switches, 5 hosts)

**Before (EVE-NG):**
```bash
# Manual process:
1. SSH to EVE-NG server
2. Navigate to /opt/unetlab/labs
3. Find lab file
4. Export nodes manually
5. Copy images via SCP (run fixpermissions!)
6. Re-create lab structure
Time: ~2 hours
```

**After (OmniLab Migration Tool):**
```bash
# Automated:
python3 migrate_lab.py export-eve --lab "CCNA Lab.unl" --output ccna.zip
python3 migrate_lab.py import --file ccna.zip --api http://omnilab:5000

Time: 3 minutes
```

**Result:**
- ✅ 30 nodes migrated
- ✅ All configs preserved
- ✅ Images auto-uploaded with correct permissions
- ✅ No manual fixpermissions needed
- ✅ Lab ready to start

---

## 🎓 Best Practices

### 1. Test Migration on Non-Production First
```bash
# Export from prod EVE-NG
ssh eve-ng 'cd /opt/unetlab/labs && tar -czf ~/labs-backup.tar.gz *.unl'

# Import to dev OmniLab
python3 migrate_lab.py import --file labs-backup.tar.gz --api http://dev-omnilab:5000

# Verify, then migrate prod
```

### 2. Batch Migration Script
```bash
#!/bin/bash
# migrate-all-labs.sh

for lab in /opt/unetlab/labs/*.unl; do
  name=$(basename "$lab" .unl)
  echo "Migrating: $name"
  python3 migrate_lab.py export-eve --lab "$lab" --output "/tmp/${name}.zip"
  python3 migrate_lab.py import --file "/tmp/${name}.zip" --api http://omnilab:5000
done
```

### 3. Version Control Your Labs
```bash
# OmniLab has native export API
curl http://omnilab:5000/api/labs/export/{lab-id} > lab-v1.json
git add lab-v1.json && git commit -m "Lab checkpoint"
```

---

## 💡 Key Advantages

1. **No More fixpermissions** - OmniLab API handles permissions automatically
2. **Portable Format** - ZIP archives work anywhere
3. **Version Control Ready** - Labs are JSON, not XML
4. **Multi-User** - Share labs with role-based access (admin/instructor/student)
5. **Modern API** - Automate everything with REST API
6. **Cloud Ready** - Deploy to Docker/K8s without SSH access

---

## 📚 Related Documentation

- [CRE-54: Lab Import/Export](../references/CRE-54-lab-export.md)
- [CRE-55: Template Management](../references/CRE-55-templates.md)
- [CRE-53: Multi-User RBAC](../references/CRE-53-auth.md)
- [Deployment Guide](DEPLOYMENT.md)

---

**Questions?** Open an issue or check the [OmniLab Wiki](https://github.com/hbrowder/omnilab/wiki)
