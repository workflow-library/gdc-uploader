#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: CommandLineTool
label: "GDC Spot Instance Upload"
doc: |
  Upload a single file to GDC with automatic resume capability.
  Designed for use on spot instances that may be interrupted.
  
  This tool:
  - Filters the manifest for the specific file
  - Uses gdc-client with resume support
  - Saves state for automatic resume after interruption
  - Handles spot instance termination gracefully
  
  Version: 2025.01.17.1
  Last Updated: 2025-01-17
  Changes: Initial implementation for spot instance resilience

# ==============================================================================
# REQUIREMENTS SECTION
# ==============================================================================
requirements:
  DockerRequirement:
    dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"
  ResourceRequirement:
    ramMin: 4096
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
baseCommand: ["gdc-uploader", "spot-upload"]

# ==============================================================================
# INPUTS SECTION
# ==============================================================================
inputs:
  manifest_file:
    type: File
    inputBinding:
      position: 1
    doc: "YAML or JSON manifest file containing metadata for all files"

  token_file:
    type: File
    inputBinding:
      position: 2
    doc: "GDC authentication token file"

  target_file:
    type: File
    inputBinding:
      position: 3
    doc: "The specific file to upload"

  state_file:
    type: string?
    default: "upload_state.json"
    inputBinding:
      prefix: --state-file
    doc: "Path to save upload state for resume (default: upload_state.json)"

  retry_count:
    type: int?
    default: 3
    inputBinding:
      prefix: --retries
    doc: "Number of retry attempts for failed uploads (default: 3)"

# ==============================================================================
# OUTPUTS SECTION
# ==============================================================================
outputs:
  upload_log:
    type: File
    outputBinding:
      glob: "spot-upload.log"
    doc: "Main upload log file"

  gdc_log:
    type: File?
    outputBinding:
      glob: "gdc-upload-*.log"
    doc: "GDC client log file"

  state_file:
    type: File?
    outputBinding:
      glob: "upload_state.json"
    doc: "Upload state file (if interrupted)"

  stdout:
    type: stdout
    doc: "Standard output stream"

  stderr:
    type: stderr
    doc: "Standard error stream"

# ==============================================================================
# STANDARD OUTPUT/ERROR
# ==============================================================================
stdout: spot-upload-stdout.log
stderr: spot-upload-stderr.log

# ==============================================================================
# SUCCESS CODES
# ==============================================================================
successCodes: [0]
temporaryFailCodes: []
permanentFailCodes: [1, 2]