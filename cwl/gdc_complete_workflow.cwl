#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL WORKFLOW METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: Workflow
label: "GDC Complete Upload Workflow"
doc: |
  Complete self-contained workflow for processing and uploading genomic files to GDC.
  
  This workflow contains all three tools embedded and performs:
  1. Convert YAML metadata to JSON format
  2. Filter JSON metadata for the specific input file
  3. Upload the file to GDC using the filtered metadata
  
  Version: 2025.05.30.6
  Last Updated: 2025-05-30
  Changes: Removed InitialWorkDirRequirement to allow sbg:useSbgFS hint to work properly

# ==============================================================================
# WORKFLOW REQUIREMENTS
# ==============================================================================
requirements:
  StepInputExpressionRequirement: {}
  SubworkflowFeatureRequirement: {}
  InlineJavascriptRequirement: {}

hints:
  - class: 'sbg:useSbgFS'
    value: 'true'

# ==============================================================================
# WORKFLOW INPUTS
# ==============================================================================
inputs:
  yaml_metadata:
    type: File
    doc: "YAML metadata file containing information for multiple files"
  
  target_file:
    type: File
    doc: "Single genomic file to process and upload"
  
  token_file:
    type: File
    doc: "GDC authentication token file"
  
  retry_count:
    type: int?
    default: 3
    doc: "Number of retry attempts for failed uploads"

# ==============================================================================
# WORKFLOW STEPS
# ==============================================================================
steps:
  # Step 1: Convert YAML to JSON
  yaml_to_json:
    run:
      class: CommandLineTool
      baseCommand: ["gdc_yaml2json.py"]
      requirements:
        DockerRequirement:
          dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"
      hints:
        - class: 'sbg:useSbgFS'
          value: 'true'
      inputs:
        yaml_file:
          type: File
          inputBinding:
            position: 1
        output_filename:
          type: string
          default: "metadata.json"
          inputBinding:
            position: 2
      outputs:
        json_file:
          type: File
          outputBinding:
            glob: $(inputs.output_filename)
    in:
      yaml_file: yaml_metadata
      output_filename: 
        valueFrom: "metadata.json"
    out: [json_file]
  
  # Step 2: Filter JSON by filename
  filter_metadata:
    run:
      class: CommandLineTool
      baseCommand: ["gdc_filter_json.py"]
      requirements:
        DockerRequirement:
          dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"
      hints:
        - class: 'sbg:useSbgFS'
          value: 'true'
      inputs:
        json_file:
          type: File
          inputBinding:
            position: 1
        target_file:
          type: File
          inputBinding:
            position: 2
            valueFrom: $(self.path)
        output_filename:
          type: string
          default: "filtered_metadata.json"
          inputBinding:
            prefix: --output
      outputs:
        filtered_json:
          type: File
          outputBinding:
            glob: $(inputs.output_filename)
    in:
      json_file: yaml_to_json/json_file
      target_file: target_file
      output_filename:
        valueFrom: "filtered_metadata.json"
    out: [filtered_json]
  
  # Step 3: Upload single file
  upload_file:
    run:
      class: CommandLineTool
      baseCommand: ["gdc_upload_single.sh"]
      requirements:
        DockerRequirement:
          dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"
      hints:
        - class: 'sbg:useSbgFS'
          value: 'true'
      inputs:
        metadata_file:
          type: File
          inputBinding:
            prefix: -m
        target_file:
          type: File
          inputBinding:
            position: 10
        token_file:
          type: File
          inputBinding:
            prefix: -t
        retry_count:
          type: int?
          default: 3
          inputBinding:
            prefix: -r
      outputs:
        upload_report:
          type: File
          outputBinding:
            glob: "upload-report.tsv"
        log_file:
          type: File?
          outputBinding:
            glob: "upload-*.log"
    in:
      metadata_file: filter_metadata/filtered_json
      target_file: target_file
      token_file: token_file
      retry_count: retry_count
    out: [upload_report, log_file]

# ==============================================================================
# WORKFLOW OUTPUTS
# ==============================================================================
outputs:
  converted_json:
    type: File
    outputSource: yaml_to_json/json_file
    doc: "Full JSON metadata converted from YAML"
  
  filtered_metadata:
    type: File
    outputSource: filter_metadata/filtered_json
    doc: "Filtered JSON metadata for the specific file"
  
  upload_report:
    type: File
    outputSource: upload_file/upload_report
    doc: "Upload report with status"
  
  upload_log:
    type: File?
    outputSource: upload_file/log_file
    doc: "Upload log file"