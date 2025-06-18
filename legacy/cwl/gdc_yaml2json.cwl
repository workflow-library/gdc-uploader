#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: CommandLineTool
label: "YAML to JSON Converter"
doc: |
  Convert YAML metadata files to JSON format for GDC uploader.
  
  This tool converts YAML-formatted metadata to the JSON format required by the GDC Data Transfer Tool.
  Supports complex nested structures with read groups, file metadata, and project information.
  Uses PyYAML for robust parsing of complex YAML structures.
  
  For detailed usage information, run: gdc_yaml2json.py --help
  
  Version: 2025.05.30.4
  Last Updated: 2025-05-30
  Changes: Converted to sidecar script pattern, removed embedded code, enhanced help support, removed x-owl until namespace fixed

# ==============================================================================
# REQUIREMENTS SECTION
# ==============================================================================
requirements:
  DockerRequirement:
    dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"

hints:
  - class: 'sbg:useSbgFS'
    value: 'true'

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
    inputBinding:
      position: 1
    doc: "YAML metadata file to convert"
  
  output_filename:
    type: string?
    default: "metadata.json"
    inputBinding:
      position: 2
    doc: "Output JSON filename (default: metadata.json)"

# ==============================================================================
# OUTPUTS SECTION
# ==============================================================================
outputs:
  json_file:
    type: File
    outputBinding:
      glob: $(inputs.output_filename)
    doc: "Converted JSON metadata file"

# ==============================================================================
# MISC
# ==============================================================================
stdout: yaml2json-stdout.log
stderr: yaml2json-stderr.log

