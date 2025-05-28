#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool
label: "GDC Uploader"
doc: |
  Manage uploads of sequence data to the NIH Genomic Data Commons using the gdc data transfer tool.
  This tool is a wrapper for the GDC Data Transfer Tool (gdc-client) that manages uploads of 
  genomic sequence data files to the National Cancer Institute.

requirements:
  DockerRequirement:
    dockerPull: "gdc-uploader:latest"
  ResourceRequirement:
    ramMin: 2048
    coresMin: 2

baseCommand: ["dotnet", "/app/upload2gdc.dll"]

inputs:
  upload_report:
    type: File?
    inputBinding:
      prefix: --ur
    doc: "Path to upload report TSV file"

  metadata_file:
    type: File
    inputBinding:
      prefix: --md
    doc: "Path to GDC metadata JSON file"

  files_directory:
    type: Directory
    inputBinding:
      prefix: --files
    doc: "Directory containing files to upload"

  token_file:
    type: File
    inputBinding:
      prefix: --token
    doc: "Path to GDC authentication token file"

  thread_count:
    type: int?
    default: 4
    inputBinding:
      prefix: --tc
    doc: "Number of concurrent upload threads (default: 4)"

  skip_file:
    type: File?
    inputBinding:
      prefix: --sk
    doc: "Path to file containing UUIDs to skip"

  files_only:
    type: boolean?
    inputBinding:
      prefix: --filesonly
    doc: "Check if files exist without uploading"

  retry_count:
    type: int?
    default: 1
    inputBinding:
      prefix: --rc
    doc: "Number of times to retry failed uploads (default: 1)"

  multipart:
    type: boolean?
    inputBinding:
      prefix: --mp
    doc: "Use multipart upload mode"

outputs:
  upload_report:
    type: File
    outputBinding:
      glob: "*.tsv"
    doc: "Upload report with status of each file"

  log_files:
    type:
      type: array
      items: File
    outputBinding:
      glob: "*.log"
    doc: "Log files from upload threads"

stdout: gdc-upload-stdout.log
stderr: gdc-upload-stderr.log