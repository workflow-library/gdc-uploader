#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool
label: "GDC Metadata Generator"
doc: |
  Generate GDC metadata JSON files from upload lists using the TracSeq API.
  Supports different experiment types: smallrna, rnaseq, and rnaseqexome.

requirements:
  DockerRequirement:
    dockerPull: "cgc-images.sbgenomics.com/david.roberson/gdc-utils:latest"
  ResourceRequirement:
    ramMin: 1024
    coresMin: 1

baseCommand: ["dotnet", "/app/upload2gdc.dll"]

inputs:
  upload_list:
    type: File
    inputBinding:
      prefix: --mdgen
    doc: "File containing list of items to generate metadata for"

  experiment_type:
    type:
      type: enum
      symbols:
        - smallrna
        - rnaseq
        - rnaseqexome
    inputBinding:
      prefix: --mdgentype
    doc: "Type of experiment for metadata generation"

  use_dev_server:
    type: boolean?
    inputBinding:
      prefix: --mdgendev
    doc: "Use GDC development server instead of production"

outputs:
  metadata_file:
    type: File
    outputBinding:
      glob: "*.json"
    doc: "Generated GDC metadata JSON file"

stdout: metadata-generation.log
stderr: metadata-generation-error.log

# ==============================================================================
# X-OWL SECTION  
# ==============================================================================
# Note: This CWL does not require x-owl metadata as it uses a dotnet application