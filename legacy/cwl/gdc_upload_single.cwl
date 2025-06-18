#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: CommandLineTool
label: "GDC Single File Uploader"
doc: |
  Upload a single genomic file to NIH Genomic Data Commons.
  
  This tool uploads a single file to the GDC using metadata and authentication token.
  The metadata JSON should contain information for the specific file being uploaded.
  
  For detailed usage information, run: gdc_upload_single.sh --help
  
  Version: 2025.05.30.1
  Last Updated: 2025-05-30
  Changes: Initial version for single file upload workflow

# ==============================================================================
# REQUIREMENTS SECTION
# ==============================================================================
requirements:
  DockerRequirement:
    dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"

# ==============================================================================
# HINTS SECTION
# ==============================================================================
hints:
  - class: 'sbg:useSbgFS'
    value: 'true'

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

  target_file:
    type: File
    inputBinding:
      position: 10
    doc: "Single file to upload to GDC"

  token_file:
    type: File
    inputBinding:
      prefix: -t
    doc: "GDC authentication token file"

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

# ==============================================================================
# MISC
# ==============================================================================
stdout: gdc-upload-single-stdout.log
stderr: gdc-upload-single-stderr.log