#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL WORKFLOW METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: Workflow
label: "GDC Upload Workflow"
doc: |
  Complete workflow for processing and uploading genomic files to GDC.
  
  This workflow performs the following steps:
  1. Convert YAML metadata to JSON format
  2. Filter JSON metadata for the specific input file
  3. Upload the file to GDC using the filtered metadata
  
  The workflow uses CWL expressions to extract the filename from the input file
  and automatically filter the metadata to match that specific file.
  
  Version: 2025.05.30.1
  Last Updated: 2025-05-30
  Changes: Initial workflow implementation

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
    run: gdc_yaml2json.cwl
    in:
      yaml_file: yaml_metadata
      output_filename: 
        valueFrom: "metadata.json"
    out: [json_file]
  
  # Step 2: Filter JSON by filename
  filter_metadata:
    run: gdc_filter_json.cwl
    in:
      json_file: yaml_to_json/json_file
      target_filename:
        # Extract just the filename (no path) from the input file
        valueFrom: $(inputs.target_file.basename)
      output_filename:
        valueFrom: "filtered_metadata.json"
    out: [filtered_json]
  
  # Step 3: Upload single file
  upload_file:
    run: gdc_upload_single.cwl
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

# ==============================================================================
# REQUIREMENTS
# ==============================================================================
requirements:
  StepInputExpressionRequirement: {}
  SubworkflowFeatureRequirement: {}