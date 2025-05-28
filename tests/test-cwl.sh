#!/bin/bash
#
# CWL test with hardcoded paths for Seven Bridges testing
#

set -e

echo "========================================"
echo "GDC Uploader CWL Test"
echo "========================================"

# Hardcoded paths to test data
UPLOAD_REPORT="/workspaces/gdc-uploader/tests/test-data/upload-report.tsv"
METADATA_FILE="/workspaces/gdc-uploader/tests/test-data/gdc-metadata.json"
FILES_DIR="/workspaces/gdc-uploader/tests/test-data"
TOKEN_FILE="/workspaces/gdc-uploader/tests/test-data/gdc-token.txt"
OUTPUT_DIR="/workspaces/gdc-uploader/tests/test-output"

# Create output directory
mkdir -p $OUTPUT_DIR

echo
echo "Test files:"
echo "- Upload Report: $UPLOAD_REPORT"
echo "- Metadata: $METADATA_FILE"
echo "- Sequence files: $FILES_DIR"
echo "- Token: $TOKEN_FILE"
echo "- Output: $OUTPUT_DIR"

echo
echo "Test 1: Check files only (verifies files exist)"
echo "-----------------------------------------------"
cwltool \
  --outdir $OUTPUT_DIR \
  /workspaces/gdc-uploader/cwl/gdc-uploader.cwl \
  --upload_report $UPLOAD_REPORT \
  --metadata_file $METADATA_FILE \
  --files_directory $FILES_DIR \
  --files_only

echo
echo "Test 2: Run with simulator (simulates uploads)"
echo "----------------------------------------------"
cwltool \
  --outdir $OUTPUT_DIR \
  /workspaces/gdc-uploader/cwl/gdc-uploader.cwl \
  --upload_report $UPLOAD_REPORT \
  --metadata_file $METADATA_FILE \
  --files_directory $FILES_DIR \
  --token_file $TOKEN_FILE \
  --simulator \
  --thread_count 2 \
  --retry_count 1 \
  --multipart yes

echo
echo "Test completed. Output files in: $OUTPUT_DIR"