#!/bin/bash
#
# Seven Bridges Style CWL Testing
# This simulates how Seven Bridges executes CWL workflows
#

set -e

# Find next task number in test-output directory
BASE_OUTPUT_DIR="/workspaces/gdc-uploader/tests/test-output"
TASK_NUM=$(find $BASE_OUTPUT_DIR -maxdepth 1 -name "task_*" -type d 2>/dev/null | wc -l)
TASK_NUM=$((TASK_NUM + 1))
TASK_DIR="$BASE_OUTPUT_DIR/task_$(printf "%03d" $TASK_NUM)"

echo "========================================"
echo "Seven Bridges Style CWL Test - Task $TASK_NUM"
echo "========================================"

# Create task directory (simulates Seven Bridges temp dir)
mkdir -p "$TASK_DIR"
cd "$TASK_DIR"

echo "Working directory: $(pwd)"
echo "Input data location: /workspaces/gdc-uploader/tests/test-data (read-only simulation)"
echo

# Absolute paths (like Seven Bridges generates)
METADATA_FILE="/workspaces/gdc-uploader/tests/test-data/gdc-metadata.json"
FILES_DIR="/workspaces/gdc-uploader/tests/test-data"
TOKEN_FILE="/workspaces/gdc-uploader/tests/test-data/gdc-token.txt"
CWL_FILE="/workspaces/gdc-uploader/cwl/gdc_upload.cwl"

echo "Step 1: Validate CWL workflow"
echo "-----------------------------"
owlkit cwl validate "$CWL_FILE"

echo
echo "Step 2: Running upload test (dry run)"
echo "------------------------------------"
# This will test file discovery and report generation
# Actual uploads will fail due to test token
owlkit cwl run "$CWL_FILE" \
  --metadata-file "$METADATA_FILE" \
  --files-directory "$FILES_DIR" \
  --token-file "$TOKEN_FILE" \
  --thread-count 2 \
  --retry-count 1 \
  --output-dir . \
  --strict-limits || true

echo
echo "Test completed in: $(pwd)"
echo "Output files:"
ls -la *.tsv *.log 2>/dev/null || echo "No output files found"

echo
echo "Upload report content:"
cat upload-report.tsv 2>/dev/null || echo "No upload report generated"