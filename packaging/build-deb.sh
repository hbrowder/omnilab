#!/usr/bin/env bash
# Build a .deb package for OmniLab.
#
# Usage:
#   packaging/build-deb.sh                       # uses VERSION file
#   packaging/build-deb.sh 1.2.3                 # explicit version override
#   VERSION=1.2.3 packaging/build-deb.sh         # via env
#
# Output: ./dist/omnilab_<version>_amd64.deb (+ .sha256)
#
# Run from the repo root. Expects:
#   - backend/        (FastAPI source)
#   - backend/requirements.txt
#   - frontend/dist/  (built SPA bundle — run `npm run build` first if missing)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

VERSION="${1:-${VERSION:-$(cat VERSION 2>/dev/null || echo "0.0.0")}}"
ARCH="amd64"
PKGNAME="omnilab"
BUILD_DIR="$(mktemp -d -t omnilab-deb-build-XXXXXX)"
OUT_DIR="$REPO_ROOT/dist"
DEB_NAME="${PKGNAME}_${VERSION}_${ARCH}.deb"

trap 'rm -rf "$BUILD_DIR"' EXIT

echo "==> Building $DEB_NAME (version $VERSION)"
mkdir -p "$OUT_DIR"

# Skeleton
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/opt/omnilab"
mkdir -p "$BUILD_DIR/etc/systemd/system"
mkdir -p "$BUILD_DIR/usr/local/bin"

# --- DEBIAN/control ---
cat > "$BUILD_DIR/DEBIAN/control" <<EOF
Package: omnilab
Version: $VERSION
Section: net
Priority: optional
Architecture: $ARCH
Depends: python3 (>= 3.10), python3-venv, python3-pip, docker.io | docker-ce, openvswitch-switch
Recommends: qemu-kvm, libvirt-daemon-system
Maintainer: OmniLab Team <support@omnilab.io>
Description: Open Multi-Node Infrastructure Lab
 OmniLab is a self-hosted network and infrastructure emulation platform
 for security, DevOps, and AI/ML labs.
 .
 Features:
  * Network device emulation (Cisco, Juniper, VyOS, etc.)
  * Security labs (Wazuh SIEM, Kali, Suricata)
  * DevOps labs (Kubernetes, Ansible, CI/CD)
  * AI/ML labs (Ollama, Jupyter, MLOps)
  * Visual drag-and-drop topology editor
  * One-click lab templates
Homepage: https://omnilab.io
EOF

# --- postinst ---
cat > "$BUILD_DIR/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e

if ! id omnilab &>/dev/null; then
    useradd -r -m -d /var/lib/omnilab -s /bin/bash omnilab
fi
usermod -aG docker omnilab 2>/dev/null || true

if [ ! -d /opt/omnilab/venv ]; then
    python3 -m venv /opt/omnilab/venv
    /opt/omnilab/venv/bin/pip install --quiet --upgrade pip
    /opt/omnilab/venv/bin/pip install --quiet -r /opt/omnilab/backend/requirements.txt
fi

chown -R omnilab:omnilab /opt/omnilab
mkdir -p /var/log/omnilab /opt/omnilab/data
chown -R omnilab:omnilab /var/log/omnilab /opt/omnilab/data

systemctl daemon-reload
systemctl enable omnilab.service
systemctl start omnilab.service

IP=$(hostname -I | awk '{print $1}')
cat <<MSG

============================================
  OmniLab installed successfully!
============================================

  Open: http://$IP:5000

  sudo systemctl status omnilab
  sudo journalctl -u omnilab -f

MSG
exit 0
EOF
chmod 0755 "$BUILD_DIR/DEBIAN/postinst"

# --- prerm ---
cat > "$BUILD_DIR/DEBIAN/prerm" <<'EOF'
#!/bin/bash
systemctl stop omnilab.service 2>/dev/null || true
systemctl disable omnilab.service 2>/dev/null || true
exit 0
EOF
chmod 0755 "$BUILD_DIR/DEBIAN/prerm"

# --- App payload ---
echo "==> Copying backend"
rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='*.bak*' \
      --exclude='omnilab.db' --exclude='.license.json' --exclude='.license_secret' \
      --exclude='.updates_state.json' --exclude='*.bak_*' \
      backend/ "$BUILD_DIR/opt/omnilab/backend/"

echo "==> Copying frontend bundle"
if [ ! -d "frontend/dist" ]; then
    echo "ERROR: frontend/dist not found. Run 'npm --prefix frontend install && npm --prefix frontend run build' first." >&2
    exit 1
fi
mkdir -p "$BUILD_DIR/opt/omnilab/frontend"
rsync -a frontend/dist/ "$BUILD_DIR/opt/omnilab/frontend/"

echo "==> Installing systemd unit"
cp packaging/omnilab.service "$BUILD_DIR/etc/systemd/system/omnilab.service"

echo "==> Installing CLI wrapper"
cp packaging/omnilab-cli "$BUILD_DIR/usr/local/bin/omnilab"
chmod 0755 "$BUILD_DIR/usr/local/bin/omnilab"

# --- Stamp version into payload ---
echo "$VERSION" > "$BUILD_DIR/opt/omnilab/VERSION"

# --- Build ---
echo "==> Running dpkg-deb"
dpkg-deb --build --root-owner-group "$BUILD_DIR" "$OUT_DIR/$DEB_NAME" >/dev/null

(cd "$OUT_DIR" && sha256sum "$DEB_NAME" > "$DEB_NAME.sha256")

SIZE=$(du -h "$OUT_DIR/$DEB_NAME" | cut -f1)
echo ""
echo "Built: $OUT_DIR/$DEB_NAME ($SIZE)"
echo "       $OUT_DIR/$DEB_NAME.sha256"
echo ""
echo "Install: sudo dpkg -i $OUT_DIR/$DEB_NAME"
