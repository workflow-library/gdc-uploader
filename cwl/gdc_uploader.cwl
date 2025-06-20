#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool
baseCommand: [gdc-http-upload]

arguments:
  - prefix: --file
    valueFrom: $(inputs.file_to_upload.basename)

requirements:
  - class: InlineJavascriptRequirement
  - class: DockerRequirement
    dockerPull: ghcr.io/workflow-library/gdc-uploader:latest
  - class: EnvVarRequirement
    envDef:
      CWL_RUNTIME: "true"

hints:
  - class: 'sbg:useSbgFS'
    value: 'true'

inputs:
  manifest:
    type: File
    inputBinding:
      prefix: --manifest
    doc: "GDC manifest file (JSON or YAML)"
  
  file_to_upload:
    type: File
    inputBinding:
      prefix: --file-path
    doc: "The actual file to upload to GDC"
  
  token:
    type: File
    inputBinding:
      prefix: --token
    doc: "GDC token file"
  
  progress_mode:
    type: string?
    default: "auto"
    inputBinding:
      prefix: --progress-mode
    doc: "Progress display mode: auto, simple, bar, or none"
  
  output_file:
    type: string?
    inputBinding:
      prefix: --output
    doc: "Save output to log file (optional)"
  
  append_log:
    type: boolean?
    default: false
    inputBinding:
      prefix: --append
    doc: "Append to output file instead of overwriting"

outputs:
  upload_log:
    type: stdout
  
  log_file:
    type: File?
    outputBinding:
      glob: $(inputs.output_file)

stdout: upload_output.txt

$namespaces:
  s: https://schema.org/

s:name: "GDC Upload"
s:description: "Upload file to GDC with progress monitoring"
s:programmingLanguage: "Python"
s:creator:
  s:name: "GDC Uploader"
s:dateCreated: "2025-06-20"