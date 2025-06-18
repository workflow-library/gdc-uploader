#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: CommandLineTool
label: "GDC JSON File Filter"
doc: |
  Filter GDC metadata JSON file by specific file_name.
  
  This tool takes a GDC metadata JSON file and a target filename, then returns
  a filtered JSON containing only the matching file entries. Supports both
  exact and partial matching (case-insensitive).
  
  Useful for extracting metadata for specific files from large datasets.
  
  For detailed usage information, run: gdc_filter_json.py --help
  
  Version: 2025.05.30.1
  Last Updated: 2025-05-30
  Changes: Initial version with comprehensive help support

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
baseCommand: ["gdc_filter_json.py"]

# ==============================================================================
# INPUTS SECTION
# ==============================================================================
inputs:
  json_file:
    type: File
    inputBinding:
      position: 1
    doc: "GDC metadata JSON file to filter"
  
  target_file:
    type: File
    inputBinding:
      position: 2
      valueFrom: $(self.path)
    doc: "Target file (basename will be extracted automatically for filtering)"
  
  output_filename:
    type: string?
    default: "filtered_metadata.json"
    inputBinding:
      prefix: --output
    doc: "Output filename (default: filtered_metadata.json)"
  
  strict_matching:
    type: boolean?
    inputBinding:
      prefix: --strict
    doc: "Use exact filename matching instead of partial matching"
  
  compact:
    type: boolean?
    inputBinding:
      prefix: --compact
    doc: "Compact JSON output (no indentation)"

# ==============================================================================
# OUTPUTS SECTION
# ==============================================================================
outputs:
  filtered_json:
    type: File
    outputBinding:
      glob: $(inputs.output_filename)
    doc: "Filtered JSON file containing only matching entries"

# ==============================================================================
# MISC
# ==============================================================================
stdout: filter-json-stdout.log
stderr: filter-json-stderr.log