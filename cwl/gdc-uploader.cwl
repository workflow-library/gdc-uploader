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
    dockerPull: "cgc-images.sbgenomics.com/david.roberson/gdc-utils:latest"
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
    type: File?
    inputBinding:
      prefix: --token
    doc: "Path to GDC authentication token file (not required when using simulator)"

  thread_count:
    type: int?
    default: 4
    inputBinding:
      prefix: --threads
    doc: "Number of concurrent upload threads (default: 10)"

  skip_file:
    type: File?
    inputBinding:
      prefix: --skip
    doc: "Path to file containing UUIDs to skip"

  files_only:
    type: boolean?
    inputBinding:
      prefix: --filesonly
    doc: "Check if files exist without uploading"

  retry_count:
    type: int?
    default: 3
    inputBinding:
      prefix: --retries
    doc: "Number of times to retry failed uploads (default: 3)"

  multipart:
    type: string?
    default: "yes"
    inputBinding:
      prefix: --multipart
    doc: "For uploads, force multipart (yes), force single chunk (no), or allow for dtt default behavior (program)"

  simulator:
    type: boolean?
    inputBinding:
      prefix: --sim
    doc: "Use simulator instead of the gdc data transfer tool"

outputs:
  upload_report_output:
    type: File?
    outputBinding:
      glob: "*.tsv"
    doc: "Upload report with status of each file"

  log_files:
    type: File[]?
    outputBinding:
      glob: "*.log"
    doc: "Log files from upload threads"

stdout: gdc-upload-stdout.log
stderr: gdc-upload-stderr.log