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
UPLOAD_REPORT="/workspaces/gdc-uploader/tests/test-data/upload-report.tsv"
METADATA_FILE="/workspaces/gdc-uploader/tests/test-data/gdc-metadata.json"
FILES_DIR="/workspaces/gdc-uploader/tests/test-data"
TOKEN_FILE="/workspaces/gdc-uploader/tests/test-data/gdc-token.txt"
CWL_FILE="/workspaces/gdc-uploader/cwl/gdc-uploader.cwl"

echo "Test 1: Files-only check"
echo "-------------------------"
cwltool --enable-pull --outdir . "$CWL_FILE" \
  --upload_report "$UPLOAD_REPORT" \
  --metadata_file "$METADATA_FILE" \
  --files_directory "$FILES_DIR" \
  --files_only

echo
echo "Test 2: Simulator mode"
echo "----------------------"
cwltool --enable-pull --outdir . "$CWL_FILE" \
  --upload_report "$UPLOAD_REPORT" \
  --metadata_file "$METADATA_FILE" \
  --files_directory "$FILES_DIR" \
  --token_file "$TOKEN_FILE" \
  --simulator \
  --thread_count 2

echo
echo "Test completed in: $(pwd)"
echo "Output files:"
ls -la *.log