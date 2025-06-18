#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: CommandLineTool
label: "gdc_upload"
doc: |
  Upload genomic data files to the NCI Genomic Data Commons using parallel processing
  
  Version: 2.0.0
  Generated from prompt: gdc_upload.md

# ==============================================================================
# REQUIREMENTS SECTION
# ==============================================================================
requirements:
  DockerRequirement:
    dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"
  ResourceRequirement:
    ramMin: 2048
    coresMin: 2

# ==============================================================================
# COMMAND SECTION
# ==============================================================================
baseCommand: ["gdc-upload"]

# ==============================================================================
# INPUTS SECTION
# ==============================================================================
inputs:
  metadata_file:
    type: File
    inputBinding:
      prefix: -m
    doc: "GDC metadata JSON file containing file UUIDs and paths"
  token_file:
    type: File
    inputBinding:
      prefix: -t
    doc: "GDC authentication token file"
  files_directory:
    type: Directory
    inputBinding:
      position: 1
    doc: "Directory containing the files to upload"
  thread_count:
    type: int
    doc: "Number of parallel upload threads"
  retry_count:
    type: int
    doc: "Number of retry attempts for failed uploads"

# ==============================================================================
# OUTPUTS SECTION
# ==============================================================================
outputs:
  upload_report:
    type: File
    outputBinding:
      glob: "upload-report.tsv"
    doc: "Tab-separated report of upload results"
  log_files:
    type: File
    outputBinding:
      glob: "*.log"
    doc: "Upload log files for debugging"