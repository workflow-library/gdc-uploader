#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: CommandLineTool
label: "GDC Single File Uploader - Streaming Version"
doc: |
  Upload a single genomic file to NIH Genomic Data Commons with S3 streaming.
  
  This version attempts to stream directly from S3 without copying to disk.
  
  Version: 2025.01.17.1
  Last Updated: 2025-01-17
  Changes: Streaming configuration for Seven Bridges

# ==============================================================================
# REQUIREMENTS SECTION
# ==============================================================================
requirements:
  DockerRequirement:
    dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"
  ShellCommandRequirement: {}

# ==============================================================================
# HINTS SECTION
# ==============================================================================
hints:
  # Disable sbgFS to avoid file copying
  - class: 'sbg:useSbgFS'
    value: 'false'
  
  # Enable streaming if available
  - class: 'sbg:AWSInstanceType'
    value: 'c5.xlarge'
  
  # Minimize disk requirements
  - class: 'sbg:DiskRequirement'
    value: 50  # Only need space for logs/temp files

# ==============================================================================
# COMMAND SECTION
# ==============================================================================
baseCommand: ["gdc_upload_single.sh"]

# ==============================================================================
# INPUTS SECTION
# ==============================================================================
inputs:
  metadata_file:
    type: File
    inputBinding:
      prefix: -m
    doc: "GDC metadata JSON file containing file information"
    # Load metadata to disk (small file)
    streamable: false

  target_file:
    type: File
    inputBinding:
      position: 10
    doc: "Single file to upload to GDC"
    # Enable streaming for large BAM
    streamable: true

  token_file:
    type: File
    inputBinding:
      prefix: -t
    doc: "GDC authentication token file"
    # Load token to disk (small file)
    streamable: false

  retry_count:
    type: int?
    default: 3
    inputBinding:
      prefix: -r
    doc: "Number of retry attempts for failed uploads (default: 3)"

# ==============================================================================
# OUTPUTS SECTION
# ==============================================================================
outputs:
  upload_report:
    type: File
    outputBinding:
      glob: "upload-report.tsv"
    doc: "Upload report with status of the file"

  log_file:
    type: File?
    outputBinding:
      glob: "upload-*.log"
    doc: "Upload log file"

  stdout_log:
    type: stdout
    doc: "Standard output"

  stderr_log:
    type: stderr
    doc: "Standard error"

# ==============================================================================
# STANDARD OUTPUT/ERROR
# ==============================================================================
stdout: gdc-upload-stdout.log
stderr: gdc-upload-stderr.log

# ==============================================================================
# SUCCESS CODES
# ==============================================================================
successCodes: [0]
temporaryFailCodes: []
permanentFailCodes: [1, 2, 3]