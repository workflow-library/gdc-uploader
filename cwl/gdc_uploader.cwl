#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool
baseCommand: [python, -m, gdc_uploader.upload]

requirements:
  - class: InlineJavascriptRequirement
  - class: DockerRequirement
    dockerPull: ghcr.io/workflow-library/gdc-uploader:latest
  - class: EnvVarRequirement
    envDef:
      CWL_RUNTIME: "true"

inputs:
  manifest:
    type: File
    inputBinding:
      prefix: --manifest
    doc: "GDC manifest JSON file"
  
  filename:
    type: string
    inputBinding:
      prefix: --file
    doc: "Target filename to upload"
  
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

outputs:
  upload_log:
    type: stdout

stdout: upload_output.json

$namespaces:
  s: https://schema.org/

s:name: "GDC Upload"
s:description: "Upload file to GDC with progress monitoring"
s:programmingLanguage: "Python"
s:creator:
  s:name: "GDC Uploader"
s:dateCreated: "2025-06-20"