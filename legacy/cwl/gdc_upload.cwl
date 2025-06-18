#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: CommandLineTool
label: "GDC Uploader"
doc: |
  Direct upload to the NIH Genomic Data Commons using the gdc-client.
  This tool manages uploads of genomic sequence data files to the 
  National Cancer Institute's Genomic Data Commons.
  
  Version: 2025.05.30.3
  Last Updated: 2025-05-30
  Changes: Added comprehensive help support to sidecar script, follows OWL pattern

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
# HINTS SECTION
# ==============================================================================
hints:
  - class: 'sbg:useSbgFS'
    value: 'true'

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
    doc: "Path to GDC metadata JSON file"

  files_directory:
    type: Directory
    inputBinding:
      position: 10
    doc: "Directory containing files to upload"

  token_file:
    type: File
    inputBinding:
      prefix: -t
    doc: "Path to GDC authentication token file"

  thread_count:
    type: int?
    default: 4
    inputBinding:
      prefix: -j
    doc: "Number of concurrent upload threads (default: 4)"

  retry_count:
    type: int?
    default: 3
    inputBinding:
      prefix: -r
    doc: "Number of times to retry failed uploads (default: 3)"

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
      glob: "*.log"
    doc: "Log files from upload threads"

# ==============================================================================
# MISC
# ==============================================================================
stdout: gdc-upload-stdout.log
stderr: gdc-upload-stderr.log

