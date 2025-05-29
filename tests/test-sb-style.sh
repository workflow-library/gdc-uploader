#!/bin/bash
#
# Seven Bridges Style CWL Testing
# This simulates how Seven Bridges executes CWL workflows
#

set -e

# Find next task number
TASK_NUM=$(find tasks -name "task_*" 2>/dev/null | wc -l)
TASK_NUM=$((TASK_NUM + 1))
TASK_DIR="tasks/task_$(printf "%03d" $TASK_NUM)"

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
CWL_FILE="/workspaces/gdc-uploader/apps/gdc_upload.cwl"

echo "Running upload test (dry run)"
echo "-----------------------------"
# This will test file discovery and report generation
# Actual uploads will fail due to test token
cwltool --enable-pull --outdir . "$CWL_FILE" \
  --metadata_file "$METADATA_FILE" \
  --files_directory "$FILES_DIR" \
  --token_file "$TOKEN_FILE" \
  --thread_count 2 \
  --retry_count 1 || true

echo
echo "Test completed in: $(pwd)"
echo "Output files:"
ls -la *.tsv *.log 2>/dev/null || echo "No output files found"

echo
echo "Upload report content:"
cat upload-report.tsv 2>/dev/null || echo "No upload report generated"