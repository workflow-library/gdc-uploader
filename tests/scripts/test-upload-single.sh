#!/bin/bash
#
# Test script for gdc_upload_single workflow using owlkit
#

set -e

echo "========================================"
echo "GDC Upload Single File Test"
echo "========================================"

# Hardcoded paths to test data
METADATA_FILE="/workspaces/gdc-uploader/tests/test-data/gdc-metadata.json"
TARGET_FILE="/workspaces/gdc-uploader/tests/test-data/fastq/210528_UNC01_0001_TEST0001_sample1.fastq.gz"
TOKEN_FILE="/workspaces/gdc-uploader/tests/test-data/gdc-token.txt"
BASE_OUTPUT_DIR="/workspaces/gdc-uploader/tests/test-output"

# Find next task number
TASK_NUM=$(find $BASE_OUTPUT_DIR -maxdepth 1 -name "task_*" -type d 2>/dev/null | wc -l)
TASK_NUM=$((TASK_NUM + 1))
OUTPUT_DIR="$BASE_OUTPUT_DIR/task_$(printf "%03d" $TASK_NUM)"

# Create task-specific output directory
mkdir -p $OUTPUT_DIR

echo "Running test in: $OUTPUT_DIR"

echo
echo "Test files:"
echo "- Metadata: $METADATA_FILE"
echo "- Target file: $TARGET_FILE"
echo "- Token: $TOKEN_FILE"
echo "- Output: $OUTPUT_DIR"

echo
echo "Step 1: Validate CWL"
echo "--------------------"
owlkit cwl validate /workspaces/gdc-uploader/cwl/gdc_upload_single.cwl

echo
echo "Step 2: Run single file upload (dry run - no actual upload)"
echo "-----------------------------------------------------------"
# Since we don't have a real token, this will fail at the actual upload
# but will test the file processing logic
owlkit cwl run /workspaces/gdc-uploader/cwl/gdc_upload_single.cwl \
  --metadata-file $METADATA_FILE \
  --target-file $TARGET_FILE \
  --token-file $TOKEN_FILE \
  --retry-count 2 \
  --output-dir $OUTPUT_DIR || true

echo
echo "Test completed. Check output files in: $OUTPUT_DIR"
echo "Expected outputs:"
echo "- upload-report.tsv (with file status)"
echo "- gdc-upload-single-stdout.log"
echo "- gdc-upload-single-stderr.log"
echo "- upload-*.log (individual file upload log)"

# Show the upload report if it exists
if [ -f "$OUTPUT_DIR/upload-report.tsv" ]; then
    echo
    echo "Upload report content:"
    echo "----------------------"
    cat "$OUTPUT_DIR/upload-report.tsv"
fi

# Cleanup old test directories (keep last 10)
echo
echo "Cleaning up old test directories..."
cd $BASE_OUTPUT_DIR
ls -dt task_* 2>/dev/null | tail -n +11 | xargs rm -rf 2>/dev/null || true
echo "Kept last 10 test runs"