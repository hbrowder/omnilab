#!/bin/bash
# Example: Migrate an EVE-NG lab to OmniLab
#
# Usage:
#   ./migrate-eve-lab.sh "My CCNA Lab.unl" http://omnilab:5000
#

set -e

LAB_FILE="$1"
OMNILAB_API="${2:-http://localhost:5000}"

if [ -z "$LAB_FILE" ]; then
  echo "Usage: $0 <eve-lab.unl> [omnilab-api-url]"
  exit 1
fi

echo "========================================"
echo "EVE-NG → OmniLab Migration"
echo "========================================"
echo "Lab: $LAB_FILE"
echo "OmniLab API: $OMNILAB_API"
echo ""

# Step 1: Export from EVE-NG
OUTPUT_ZIP="/tmp/$(basename "$LAB_FILE" .unl).zip"
echo "📦 Exporting lab to ZIP..."
python3 ../scripts/migrate_lab.py export-eve \
  --lab "$LAB_FILE" \
  --output "$OUTPUT_ZIP"

# Step 2: Check OmniLab health
echo ""
echo "🔍 Checking OmniLab health..."
curl -sf "$OMNILAB_API/api/system/health" | python3 -m json.tool

# Step 3: Import to OmniLab
echo ""
echo "📥 Importing to OmniLab..."
python3 ../scripts/migrate_lab.py import \
  --file "$OUTPUT_ZIP" \
  --api "$OMNILAB_API"

# Step 4: Verify permissions
echo ""
echo "✅ Verifying image permissions..."
curl -sf "$OMNILAB_API/api/system/permissions" | python3 -m json.tool

echo ""
echo "========================================"
echo "Migration Complete!"
echo "========================================"
echo "No fixpermissions needed — OmniLab handled it automatically."
echo "Lab is ready to start."
