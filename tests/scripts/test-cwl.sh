#!/bin/bash
#
# CWL test with hardcoded paths for testing
#

set -e

echo "========================================"
echo "GDC Uploader CWL Test"
echo "========================================"

# Hardcoded paths to test data
METADATA_FILE="/workspaces/gdc-uploader/tests/test-data/gdc-metadata.json"
FILES_DIR="/workspaces/gdc-uploader/tests/test-data"
TOKEN_FILE="/workspaces/gdc-uploader/tests/test-data/gdc-token.txt"
BASE_OUTPUT_DIR="/workspaces/gdc-uploader/tests/test-output"

# Find next task number
TASK_NUM=$(find $BASE_OUTPUT_DIR -maxdepth 1 -name "task_*" -type d 2>/dev/null | wc -l)
TASK_NUM=$((TASK_NUM + 1))
OUTPUT_DIR="$BASE_OUTPUT_DIR/task_$(printf "%03d" $TASK_NUM)"

# Create task-specific output directory
mkdir -p $OUTPUT_DIR

echo "Running tests in: $OUTPUT_DIR"

echo
echo "Test files:"
echo "- Metadata: $METADATA_FILE"
echo "- Sequence files: $FILES_DIR"
echo "- Token: $TOKEN_FILE"
echo "- Output: $OUTPUT_DIR"

echo
echo "Test 1: CWL Validation"
echo "---------------------"
owlkit cwl validate /workspaces/gdc-uploader/cwl/gdc_upload.cwl

echo
echo "Test 2: Basic upload test (dry run - no actual upload)"
echo "------------------------------------------------------"
# Since we don't have a real token, this will fail at the actual upload
# but will test the file discovery and setup logic
owlkit cwl run /workspaces/gdc-uploader/cwl/gdc_upload.cwl \
  --metadata-file $METADATA_FILE \
  --files-directory $FILES_DIR \
  --token-file $TOKEN_FILE \
  --thread-count 2 \
  --retry-count 1 \
  --output-dir $OUTPUT_DIR || true

echo
echo "Test 3: Test with strict resource limits"
echo "----------------------------------------"
owlkit cwl run /workspaces/gdc-uploader/cwl/gdc_upload.cwl \
  --metadata-file $METADATA_FILE \
  --files-directory $FILES_DIR \
  --token-file $TOKEN_FILE \
  --thread-count 2 \
  --retry-count 1 \
  --output-dir $OUTPUT_DIR \
  --strict-limits || true

echo
echo "Test completed. Check output files in: $OUTPUT_DIR"
echo "Expected outputs:"
echo "- upload-report.tsv (with file status)"
echo "- gdc-upload-stdout.log"
echo "- gdc-upload-stderr.log"

# Cleanup old test directories (keep last 10)
echo
echo "Cleaning up old test directories..."
cd $BASE_OUTPUT_DIR
ls -dt task_* 2>/dev/null | tail -n +11 | xargs rm -rf 2>/dev/null || true
echo "Kept last 10 test runs"