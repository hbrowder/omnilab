#!/bin/bash
# Batch migrate all EVE-NG labs to OmniLab
#
# Usage:
#   # On EVE-NG server
#   ./batch-migrate-eve.sh /opt/unetlab/labs http://omnilab:5000 [jwt-token]
#
#   # With authentication
#   ./batch-migrate-eve.sh /opt/unetlab/labs http://omnilab:5000 "eyJhbG..."

set -e

EVE_LABS_DIR="${1:-/opt/unetlab/labs}"
OMNILAB_API="${2:-http://localhost:5000}"
JWT_TOKEN="$3"

if [ ! -d "$EVE_LABS_DIR" ]; then
  echo "Error: EVE-NG labs directory not found: $EVE_LABS_DIR"
  echo "Usage: $0 <eve-labs-dir> [omnilab-api] [jwt-token]"
  exit 1
fi

echo "========================================"
echo "BATCH MIGRATION: EVE-NG → OmniLab"
echo "========================================"
echo "Source: $EVE_LABS_DIR"
echo "Target: $OMNILAB_API"
echo ""

# Find all .unl files
LAB_FILES=($(find "$EVE_LABS_DIR" -name "*.unl" -type f))
TOTAL_LABS=${#LAB_FILES[@]}

if [ $TOTAL_LABS -eq 0 ]; then
  echo "No .unl files found in $EVE_LABS_DIR"
  exit 1
fi

echo "Found $TOTAL_LABS lab(s) to migrate"
echo ""

# Create temp directory for exports
EXPORT_DIR="/tmp/omnilab-batch-export-$(date +%s)"
mkdir -p "$EXPORT_DIR"
echo "Export directory: $EXPORT_DIR"
echo ""

SUCCESS=0
FAILED=0
SKIPPED=0

# Export all labs first
echo "========================================"
echo "PHASE 1: EXPORTING LABS"
echo "========================================"

for LAB_FILE in "${LAB_FILES[@]}"; do
  LAB_NAME=$(basename "$LAB_FILE" .unl)
  OUTPUT_ZIP="$EXPORT_DIR/${LAB_NAME}.zip"
  
  echo "[$((SUCCESS+FAILED+SKIPPED+1))/$TOTAL_LABS] Exporting: $LAB_NAME"
  
  if python3 scripts/migrate_lab.py export-eve \
      --lab "$LAB_FILE" \
      --output "$OUTPUT_ZIP" 2>&1 | grep -q "Export complete"; then
    echo "  ✓ Exported to $OUTPUT_ZIP"
    ((SUCCESS++))
  else
    echo "  ✗ Export failed"
    ((FAILED++))
    # Continue with other labs
  fi
  echo ""
done

echo "Export summary: $SUCCESS succeeded, $FAILED failed"
echo ""

# Check OmniLab health
echo "========================================"
echo "CHECKING OMNILAB HEALTH"
echo "========================================"
HEALTH_CHECK=$(curl -sf "$OMNILAB_API/api/system/health" 2>&1 || echo "failed")
if echo "$HEALTH_CHECK" | grep -q "ok"; then
  echo "✓ OmniLab is healthy"
else
  echo "✗ OmniLab health check failed: $HEALTH_CHECK"
  echo "Fix OmniLab before importing labs"
  exit 1
fi
echo ""

# Import all labs
echo "========================================"
echo "PHASE 2: IMPORTING LABS"
echo "========================================"

SUCCESS=0
FAILED=0
IMPORTED_LABS=()
FAILED_LABS=()

for ZIP_FILE in "$EXPORT_DIR"/*.zip; do
  if [ ! -f "$ZIP_FILE" ]; then
    continue
  fi
  
  LAB_NAME=$(basename "$ZIP_FILE" .zip)
  echo "[$((SUCCESS+FAILED+1))/$TOTAL_LABS] Importing: $LAB_NAME"
  
  # Build import command
  IMPORT_CMD="python3 scripts/migrate_lab.py import --file \"$ZIP_FILE\" --api \"$OMNILAB_API\""
  if [ -n "$JWT_TOKEN" ]; then
    IMPORT_CMD="$IMPORT_CMD --token \"$JWT_TOKEN\""
  fi
  
  if eval "$IMPORT_CMD" 2>&1 | grep -q "Import complete"; then
    echo "  ✓ Imported successfully"
    ((SUCCESS++))
    IMPORTED_LABS+=("$LAB_NAME")
  else
    echo "  ✗ Import failed"
    ((FAILED++))
    FAILED_LABS+=("$LAB_NAME")
  fi
  echo ""
done

# Verify permissions
echo "========================================"
echo "VERIFYING PERMISSIONS"
echo "========================================"
PERM_CHECK=$(curl -sf "$OMNILAB_API/api/system/permissions" 2>&1 || echo "failed")
if echo "$PERM_CHECK" | grep -q '"status": "ok"'; then
  echo "✓ All image permissions are correct"
  echo "  (No manual fixpermissions needed!)"
else
  echo "⚠ Permission check result:"
  echo "$PERM_CHECK" | python3 -m json.tool 2>/dev/null || echo "$PERM_CHECK"
fi
echo ""

# Final summary
echo "========================================"
echo "MIGRATION COMPLETE"
echo "========================================"
echo "Exported: $TOTAL_LABS labs"
echo "Imported: $SUCCESS labs"
echo "Failed:   $FAILED labs"
echo ""

if [ $SUCCESS -gt 0 ]; then
  echo "Successfully migrated labs:"
  for lab in "${IMPORTED_LABS[@]}"; do
    echo "  ✓ $lab"
  done
  echo ""
fi

if [ $FAILED -gt 0 ]; then
  echo "Failed migrations (manual review needed):"
  for lab in "${FAILED_LABS[@]}"; do
    echo "  ✗ $lab"
  done
  echo ""
fi

echo "Export files saved to: $EXPORT_DIR"
echo ""
echo "🎉 OmniLab is ready! No fixpermissions needed."
echo "========================================"

# Exit with error if any imports failed
[ $FAILED -eq 0 ]
