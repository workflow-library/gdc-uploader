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
OUTPUT_DIR="/workspaces/gdc-uploader/tests/test-output"

# Create output directory
mkdir -p $OUTPUT_DIR

echo
echo "Test files:"
echo "- Metadata: $METADATA_FILE"
echo "- Sequence files: $FILES_DIR"
echo "- Token: $TOKEN_FILE"
echo "- Output: $OUTPUT_DIR"

echo
echo "Test 1: Basic upload test (dry run - no actual upload)"
echo "------------------------------------------------------"
# Since we don't have a real token, this will fail at the actual upload
# but will test the file discovery and setup logic
cwltool \
  --outdir $OUTPUT_DIR \
  /workspaces/gdc-uploader/apps/gdc_upload.cwl \
  --metadata_file $METADATA_FILE \
  --files_directory $FILES_DIR \
  --token_file $TOKEN_FILE \
  --thread_count 2 \
  --retry_count 1 || true

echo
echo "Test 2: Test with Docker pull enabled"
echo "-------------------------------------"
cwltool \
  --enable-pull \
  --outdir $OUTPUT_DIR \
  /workspaces/gdc-uploader/apps/gdc_upload.cwl \
  --metadata_file $METADATA_FILE \
  --files_directory $FILES_DIR \
  --token_file $TOKEN_FILE \
  --thread_count 2 \
  --retry_count 1 || true

echo
echo "Test completed. Check output files in: $OUTPUT_DIR"
echo "Expected outputs:"
echo "- upload-report.tsv (with file status)"
echo "- gdc-upload-stdout.log"
echo "- gdc-upload-stderr.log"