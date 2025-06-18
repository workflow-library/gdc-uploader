#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool
label: "Test Elastic Storage Behavior"
doc: |
  Tests how Seven Bridges Elastic Storage handles large files.
  This will help determine if files are copied or streamed.

requirements:
  DockerRequirement:
    dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"
  ShellCommandRequirement: {}

hints:
  # Enable Elastic Storage
  - class: 'sbg:useElasticStorage'
    value: true
  
  # Minimal EBS
  - class: 'sbg:DiskRequirement'
    value: 10
  
  # Use efficient instance
  - class: 'sbg:AWSInstanceType'
    value: 'c6i.xlarge'

baseCommand: [bash, -c]

arguments:
  - |
    echo "=== Elastic Storage Test ==="
    echo "Date: $(date)"
    echo
    
    # Check file path
    FILE_PATH="$(inputs.test_file.path)"
    echo "File path: $FILE_PATH"
    echo "File size: $(stat -c%s "$FILE_PATH" 2>/dev/null || stat -f%z "$FILE_PATH") bytes"
    echo
    
    # Check mount information
    echo "=== Mount Information ==="
    df -hT "$FILE_PATH"
    echo
    mount | grep -E "(elastic|s3|fuse)" || echo "No elastic/s3/fuse mounts found"
    echo
    
    # Check if symlink
    if [ -L "$FILE_PATH" ]; then
        echo "File is a symbolic link to: $(readlink -f "$FILE_PATH")"
    else
        echo "File is not a symbolic link"
    fi
    echo
    
    # Test read performance (first 1GB)
    echo "=== Read Performance Test ==="
    echo "Reading first 1GB..."
    time dd if="$FILE_PATH" of=/dev/null bs=1M count=1024 2>&1
    echo
    
    # Check disk usage before and after
    echo "=== Disk Usage ==="
    df -h
    echo
    
    # Monitor I/O for 10 seconds
    echo "=== I/O Statistics ==="
    iostat -x 1 10 &
    IOSTAT_PID=$!
    
    # Read another chunk
    echo "Reading 1GB from middle of file..."
    FILE_SIZE=$(stat -c%s "$FILE_PATH" 2>/dev/null || stat -f%z "$FILE_PATH")
    SKIP_GB=$((FILE_SIZE / 2 / 1073741824))
    time dd if="$FILE_PATH" of=/dev/null bs=1M count=1024 skip=$((SKIP_GB * 1024)) 2>&1
    
    wait $IOSTAT_PID
    
    echo
    echo "=== Test Complete ==="

inputs:
  test_file:
    type: File
    doc: "Large file (BAM) to test with"

outputs:
  test_report:
    type: stdout
    doc: "Test results"

stdout: elastic_storage_test_report.txt