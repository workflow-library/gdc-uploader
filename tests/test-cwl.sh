#!/bin/bash
#
# CWL Test Script for GDC Uploader
# This script demonstrates how to test the GDC uploader using CWL (Common Workflow Language)
#
# Prerequisites:
# - cwltool installed (pip install cwltool)
# - Docker installed and running
# - Docker image built: cgc-images.sbgenomics.com/david.roberson/gdc-utils:latest
#

set -e

echo "========================================"
echo "GDC Uploader CWL Test Script"
echo "========================================"
echo

# Create test directory structure
TEST_DIR="./cwl-test-data"
echo "Creating test directory: $TEST_DIR"
mkdir -p $TEST_DIR/input-files
mkdir -p $TEST_DIR/output

# Step 1: Create test data files
echo "Creating test data files..."
for i in {1..3}; do
    echo "Test sequence data for sample $i" > $TEST_DIR/input-files/sample_${i}.fastq
done

# Step 2: Create GDC metadata JSON file
# This file contains metadata about the genomic sequence files to be uploaded
# Format: Array of objects with type "submitted_unaligned_reads"
echo "Creating GDC metadata file..."
cat > $TEST_DIR/gdc-metadata.json << 'EOF'
[
  {
    "type": "submitted_unaligned_reads",
    "submitter_id": "sample_1_reads",
    "file_name": "sample_1.fastq",
    "file_size": 1024,
    "md5sum": "098f6bcd4621d373cade4e832627b4f6",
    "project_id": "TEST-PROJECT",
    "id": "550e8400-e29b-41d4-a716-446655440001"
  },
  {
    "type": "submitted_unaligned_reads",
    "submitter_id": "sample_2_reads",
    "file_name": "sample_2.fastq",
    "file_size": 2048,
    "md5sum": "5d41402abc4b2a76b9719d911017c592",
    "project_id": "TEST-PROJECT",
    "id": "550e8400-e29b-41d4-a716-446655440002"
  },
  {
    "type": "submitted_unaligned_reads",
    "submitter_id": "sample_3_reads",
    "file_name": "sample_3.fastq",
    "file_size": 4096,
    "md5sum": "7d793037a0760186574b0282f2f435e7",
    "project_id": "TEST-PROJECT",
    "id": "550e8400-e29b-41d4-a716-446655440003"
  }
]
EOF

# Step 3: Create GDC authentication token file
# In production, this would be your actual GDC token from https://portal.gdc.cancer.gov/
echo "Creating token file (dummy for testing)..."
echo "dummy-gdc-token-for-testing" > $TEST_DIR/gdc-token.txt

# Step 4: Create CWL job configuration file
# This YAML file defines all the inputs for the CWL workflow
echo "Creating CWL job configuration..."
cat > $TEST_DIR/gdc-upload-job.yml << EOF
# CWL Job Configuration for GDC Uploader

# REQUIRED: GDC metadata file containing information about files to upload
metadata_file:
  class: File
  path: $(pwd)/$TEST_DIR/gdc-metadata.json

# REQUIRED: Directory containing the actual sequence data files
files_directory:
  class: Directory
  path: $(pwd)/$TEST_DIR/input-files

# REQUIRED for production (optional for simulator): GDC authentication token
token_file:
  class: File
  path: $(pwd)/$TEST_DIR/gdc-token.txt

# OPTIONAL: Number of concurrent upload threads (default: 4)
thread_count: 2

# OPTIONAL: Number of retry attempts for failed uploads (default: 3)
retry_count: 2

# OPTIONAL: Use simulator mode for testing (doesn't actually upload)
simulator: true

# OPTIONAL: Check if files exist without uploading
files_only: false

# OPTIONAL: Multipart upload mode - "yes", "no", or "program" (default: "yes")
multipart: "yes"
EOF

# Step 5: Run the CWL workflow
echo
echo "========================================"
echo "Running CWL workflow with cwltool"
echo "========================================"
echo
echo "Command breakdown:"
echo "  cwltool                    - The CWL runner"
echo "  --outdir $TEST_DIR/output  - Where to save output files"
echo "  ../cwl/gdc-uploader.cwl    - The CWL workflow definition"
echo "  $TEST_DIR/gdc-upload-job.yml - The job configuration file"
echo

# Run from tests directory, so use ../ to access cwl directory
cwltool \
  --outdir $TEST_DIR/output \
  ../cwl/gdc-uploader.cwl \
  $TEST_DIR/gdc-upload-job.yml

echo
echo "========================================"
echo "Test Results"
echo "========================================"
echo
echo "Output files:"
ls -la $TEST_DIR/output/

echo
echo "Test completed successfully!"
echo "In production, remove 'simulator: true' from the job file to perform actual uploads."