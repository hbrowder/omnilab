# Permission Management: EVE-NG vs OmniLab

## The EVE-NG Pain Point

### Every Single Image Upload Requires Manual Fix:

```bash
# Step 1: Upload image via SSH
scp Panorama-KVM-10.0.4.qcow2 root@eve-ng:/opt/unetlab/addons/qemu/panorama-10.0.4/

# Step 2: SSH to server
ssh root@eve-ng

# Step 3: Rename file
cd /opt/unetlab/addons/qemu/panorama-10.0.4
mv Panorama-KVM-10.0.4.qcow2 virtioa.qcow2

# Step 4: THE MANDATORY FIX ⚠️
/opt/unetlab/wrappers/unl_wrapper -a fixpermissions

# Why? Because:
# - You uploaded as 'root' (root:root ownership)
# - Web UI runs as 'www-data'
# - QEMU processes run as 'www-data'
# - www-data can't read root-owned files!
```

**Result:** 4-step process, easy to forget, breaks web UI if missed.

---

## The OmniLab Solution

### Upload Once, Works Automatically:

```bash
# Single command - no SSH, no manual fixes:
curl -X POST http://omnilab:5000/api/template-library/upload \
  -F "file=@Panorama-KVM-10.0.4.qcow2" \
  -F "name=Palo Alto Panorama 10.0.4" \
  -F "vendor=Palo Alto" \
  -F "category=Security"

# Done! Backend automatically:
# ✓ Writes file with correct ownership (service user)
# ✓ Sets permissions to 644 (rw-r--r--)
# ✓ Makes it available to QEMU immediately
# ✓ No manual fixpermissions needed!
```

**Result:** 1-step process, impossible to forget, always works.

---

## Health Check API (Bonus)

### Check if any images have permission issues:

```bash
curl http://omnilab:5000/api/system/permissions
```

**Response:**
```json
{
  "status": "ok",
  "total_images": 12,
  "issues": [],
  "auto_fixed": [],
  "message": "No manual fixpermissions needed!"
}
```

### Force fix (if needed):

```bash
curl -X POST http://omnilab:5000/api/system/permissions/fix
```

**Response:**
```json
{
  "success": true,
  "fixed": 0,
  "errors": [],
  "files": []
}
```

---

## Why EVE-NG Has This Problem

### Multi-User Architecture Conflict:

```
┌─────────────┐
│ SSH Upload  │  → Files owned by root:root (644)
└─────────────┘
      ↓
┌─────────────┐
│  Web UI     │  → Runs as www-data, can't read root files
└─────────────┘
      ↓
┌─────────────┐
│ QEMU Process│  → Runs as www-data, can't read root files
└─────────────┘

Solution: Run fixpermissions to chown everything to www-data
          (must repeat after EVERY upload)
```

### OmniLab Architecture:

```
┌─────────────┐
│ API Upload  │  → Backend writes as 'omnilab' user
└─────────────┘
      ↓
┌─────────────┐
│ Backend     │  → Runs as 'omnilab' user, owns files
└─────────────┘
      ↓
┌─────────────┐
│ QEMU Process│  → Runs as 'omnilab' user, reads own files
└─────────────┘

Solution: No fixpermissions needed - single user owns everything
```

---

## Docker Deployment (Best Practice)

### OmniLab in Docker:

```yaml
# docker-compose.yml
services:
  omnilab:
    image: omnilab:latest
    user: "1000:1000"  # Single UID/GID
    volumes:
      - ./images:/app/images
    cap_add:
      - NET_ADMIN  # For NAT networks only
```

**Benefits:**
- All processes run as UID 1000
- No root access needed
- Predictable permissions always
- Works identically dev → staging → prod

---

## Real-World Impact

### EVE-NG User Workflow:
```bash
# Upload 20 images for CCNA lab:
for img in cisco-iosv-*.qcow2; do
  scp $img root@eve:/opt/unetlab/addons/qemu/cisco-iosv/virtioa.qcow2
  ssh root@eve '/opt/unetlab/wrappers/unl_wrapper -a fixpermissions'
done

# Time: ~30 minutes (manual rename, fixpermissions each time)
# Forgot fixpermissions? Lab won't start, debug for 15 minutes
```

### OmniLab User Workflow:
```bash
# Upload 20 images:
for img in cisco-iosv-*.qcow2; do
  curl -X POST http://omnilab:5000/api/template-library/upload \
    -F "file=@$img" \
    -F "name=Cisco IOSv $(echo $img | grep -oP '\d+\.\d+')" \
    -F "vendor=Cisco"
done

# Time: ~5 minutes (parallel uploads, auto-permissions)
# Never fails - API handles everything
```

---

## Summary

| Aspect | EVE-NG | OmniLab |
|--------|--------|---------|
| **Upload Method** | SSH/SCP as root | API (curl/GUI/Python) |
| **Permission Fix** | Manual after EVERY upload | Automatic always |
| **Error-Prone?** | Yes (easy to forget) | No (impossible to forget) |
| **Time per Upload** | 3-5 minutes (rename + fix) | 30 seconds (one command) |
| **Multi-User Safe?** | No (root access required) | Yes (JWT auth, no root) |
| **Docker Compatible?** | Complex (root in container) | Native (unprivileged) |
| **Health Check** | None | Built-in API |

**Bottom Line:** OmniLab eliminates the #1 EVE-NG pain point by design. 🎉
