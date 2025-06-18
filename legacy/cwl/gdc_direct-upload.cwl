#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: CommandLineTool
label: "GDC Direct Upload"
doc: |
  Direct upload to GDC using gdc-client without the .NET wrapper.
  This is a simplified version that uses the gdc-client directly.
  
  Version: 2025.05.29.1
  Last Updated: 2025-05-29
  Changes: Initial direct gdc-client implementation

# ==============================================================================
# REQUIREMENTS SECTION
# ==============================================================================
requirements:
  DockerRequirement:
    dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"
  ShellCommandRequirement: {}
  ResourceRequirement:
    ramMin: 2048
    coresMin: 2

# ==============================================================================
# COMMAND SECTION
# ==============================================================================
baseCommand: ["gdc-direct-upload"]
# Script arguments will be handled by the external script

# ==============================================================================
# INPUTS SECTION
# ==============================================================================
inputs:
  metadata_file:
    type: File
    doc: "Path to GDC metadata JSON file"

  files_directory:
    type: Directory
    doc: "Directory containing files to upload"

  token_file:
    type: File?
    doc: "Path to GDC authentication token file"

  files_only:
    type: boolean?
    default: false
    doc: "Check if files exist without uploading"

# ==============================================================================
# OUTPUTS SECTION
# ==============================================================================
outputs:
  upload_report:
    type: File
    outputBinding:
      glob: "upload-report.tsv"
    doc: "Upload report with status of each file"

  log_files:
    type: File[]?
    outputBinding:
      glob: "/tmp/*.log"
    doc: "Log files from uploads"

# ==============================================================================
# MISC
# ==============================================================================
stdout: gdc-upload-stdout.log
stderr: gdc-upload-stderr.log

