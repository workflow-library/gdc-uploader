#!/bin/bash

echo "Running CWL test for gdc-uploader..."
echo "=================================="

# Store current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Run from the project root directory
cd "$PROJECT_ROOT"

# Validate the CWL file
echo "Validating CWL file..."
cwltool --validate cwl/gdc_uploader.cwl

# Run the test
echo -e "\nRunning CWL with test inputs..."
cd tests
cwltool ../cwl/gdc_uploader.cwl test-job.yml

echo -e "\nTest complete!"