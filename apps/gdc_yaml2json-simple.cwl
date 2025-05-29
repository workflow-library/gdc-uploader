#!/usr/bin/env cwl-runner

cwlVersion: v1.2
class: CommandLineTool
label: "Simple YAML to JSON Converter"
doc: |
  Convert YAML metadata files to JSON format for GDC uploader.
  Uses a simple built-in parser for basic YAML structures.
  
  Version: 2025.05.29.2

baseCommand: ["gdc_yaml2json.py"]

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: yaml2json.py
        entry: |
          #!/usr/bin/env python3
          import sys
          import json
          
          # Simple YAML parser for basic list structures
          def parse_yaml(content):
              result = []
              current_item = None
              
              for line in content.split('\n'):
                  line = line.rstrip()
                  if not line or line.startswith('#'):
                      continue
                  
                  # Check for list item start
                  if line.startswith('- '):
                      if current_item:
                          result.append(current_item)
                      current_item = {}
                      line = line[2:]
                  
                  # Parse key-value pairs
                  if ':' in line and current_item is not None:
                      parts = line.split(':', 1)
                      if len(parts) == 2:
                          key = parts[0].strip()
                          value = parts[1].strip()
                          
                          # Handle different value types
                          if value.isdigit():
                              value = int(value)
                          elif value in ['true', 'false']:
                              value = value == 'true'
                          
                          current_item[key] = value
              
              if current_item:
                  result.append(current_item)
              
              return result
          
          with open(sys.argv[1], 'r') as f:
              content = f.read()
          
          data = parse_yaml(content)
          
          with open('metadata.json', 'w') as f:
              json.dump(data, f, indent=2)

inputs:
  yaml_file:
    type: File
    inputBinding:
      position: 1
    doc: "YAML metadata file to convert"

outputs:
  json_file:
    type: File
    outputBinding:
      glob: metadata.json
    doc: "Converted JSON metadata file"

# ==============================================================================
# X-OWL SECTION
# ==============================================================================
x-owl:
  dockerfile: gdc--.Dockerfile
  script: gdc_yaml2json.py