---
name: gdc_yaml2json
version: 1.0.0
description: Convert YAML metadata files to JSON format required by GDC
docker_image: ghcr.io/open-workflow-library/gdc-uploader:latest
requirements:
  ram_min: 512
  cores_min: 1
  python_packages:
    - pyyaml
---

# GDC YAML to JSON Converter

Converts YAML-formatted metadata files to the JSON format required by the GDC API. This tool simplifies metadata preparation by allowing users to write metadata in the more human-friendly YAML format.

## Inputs

- yaml_file: Input YAML metadata file (File)
- output_file: Output JSON file path, optional (string)

## Outputs

- json_file: Converted JSON metadata file (File)

## Command

```bash
gdc-yaml2json {yaml_file} -o {output_file}
```

## Requirements

- Valid YAML syntax in input file
- PyYAML Python package

## Usage Examples

### Basic Conversion
```bash
gdc-yaml2json metadata.yaml -o metadata.json
```

### Output to stdout
```bash
gdc-yaml2json metadata.yaml
```

## YAML Format Example

```yaml
- id: 550e8400-e29b-41d4-a716-446655440000
  file_name: sample1.fastq.gz
  file_size: 1234567890
  md5sum: d8e8fca2dc0f896fd7cb4cb0031ba249
  project_id: TCGA-LUAD
  
- id: 550e8400-e29b-41d4-a716-446655440001
  file_name: sample2.fastq.gz
  file_size: 2345678901
  md5sum: e8f8fca2dc0f896fd7cb4cb0031ba250
  project_id: TCGA-LUAD
```

## JSON Output Format

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "sample1.fastq.gz",
    "file_size": 1234567890,
    "md5sum": "d8e8fca2dc0f896fd7cb4cb0031ba249",
    "project_id": "TCGA-LUAD"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "file_name": "sample2.fastq.gz",
    "file_size": 2345678901,
    "md5sum": "e8f8fca2dc0f896fd7cb4cb0031ba250",
    "project_id": "TCGA-LUAD"
  }
]
```

## Error Handling

- Validates YAML syntax before conversion
- Preserves data types (numbers, strings, booleans)
- Reports line numbers for syntax errors
- Handles special characters and Unicode

## Best Practices

- Use consistent indentation (2 or 4 spaces)
- Quote strings containing special characters
- Validate JSON output before use with GDC
- Keep metadata files in version control