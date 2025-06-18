#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: CommandLineTool
label: "gdc_yaml2json"
doc: |
  Convert YAML metadata files to JSON format required by GDC
  
  Version: 1.0.0
  Generated from prompt: gdc_yaml2json.md

# ==============================================================================
# REQUIREMENTS SECTION
# ==============================================================================
requirements:
  DockerRequirement:
    dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"
  ResourceRequirement:
    ramMin: 512
    coresMin: 1

# ==============================================================================
# COMMAND SECTION
# ==============================================================================
baseCommand: ["gdc-yaml2json"]

# ==============================================================================
# INPUTS SECTION
# ==============================================================================
inputs:
  yaml_file:
    type: File
    doc: "Input YAML metadata file"
  output_file:
    type: string
    doc: "Output JSON file path, optional"

# ==============================================================================
# OUTPUTS SECTION
# ==============================================================================
outputs:
  json_file:
    type: File
    doc: "Converted JSON metadata file"