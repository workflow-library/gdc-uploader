#!/usr/bin/env cwl-runner

# ==============================================================================
# CWL METADATA SECTION
# ==============================================================================
cwlVersion: v1.2
class: CommandLineTool
label: "GDC JSON File Splitter"
doc: |
  Split GDC metadata JSON file by file_name into individual JSON files.
  
  This tool takes a GDC metadata JSON file containing multiple files and creates
  separate JSON files for each file_name entry. Each output file maintains the
  same structure as the original but contains only one file entry.
  
  Useful for per-file processing, upload tracking, or workflow distribution.
  
  For detailed usage information, run: gdc_split_json.py --help
  
  Version: 2025.05.30.1
  Last Updated: 2025-05-30
  Changes: Initial version with comprehensive help support

# ==============================================================================
# REQUIREMENTS SECTION
# ==============================================================================
requirements:
  DockerRequirement:
    dockerPull: "ghcr.io/open-workflow-library/gdc-uploader:latest"

# ==============================================================================
# COMMAND SECTION
# ==============================================================================
baseCommand: ["gdc_split_json.py"]

# ==============================================================================
# INPUTS SECTION
# ==============================================================================
inputs:
  json_file:
    type: File
    inputBinding:
      position: 1
    doc: "GDC metadata JSON file to split"
  
  prefix:
    type: string?
    inputBinding:
      prefix: --prefix
    doc: "Prefix for output filenames"
  
  suffix:
    type: string?
    inputBinding:
      prefix: --suffix
    doc: "Suffix for output filenames (before .json extension)"
  
  compact:
    type: boolean?
    inputBinding:
      prefix: --compact
    doc: "Compact JSON output (no indentation)"

# ==============================================================================
# OUTPUTS SECTION
# ==============================================================================
outputs:
  split_files:
    type: File[]
    outputBinding:
      glob: "*.json"
    doc: "Individual JSON files, one per file_name in the input"

# ==============================================================================
# MISC
# ==============================================================================
stdout: split-json-stdout.log
stderr: split-json-stderr.log