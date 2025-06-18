# GDC Metadata Format Documentation

This document describes the metadata format required for GDC uploads.

## Overview

The GDC Uploader requires a JSON metadata file that contains information about the files to be uploaded. This metadata must include:

- File UUID (assigned by GDC)
- File name
- Project ID
- Additional optional fields

## Basic Format

### Array Format (Recommended)

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "sample1.fastq.gz",
    "project_id": "TCGA-LUAD"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "file_name": "sample2.fastq.gz",
    "project_id": "TCGA-LUAD"
  }
]
```

### Object Format with Files Array

```json
{
  "files": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "file_name": "sample1.fastq.gz",
      "project_id": "TCGA-LUAD"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "file_name": "sample2.fastq.gz",
      "project_id": "TCGA-LUAD"
    }
  ]
}
```

## Required Fields

### `id` or `uuid`
- **Type**: String (UUID format)
- **Description**: The GDC-assigned UUID for the file
- **Example**: `"550e8400-e29b-41d4-a716-446655440000"`

### `file_name` or `filename`
- **Type**: String
- **Description**: The name of the file to upload
- **Example**: `"sample1.fastq.gz"`

### `project_id`
- **Type**: String
- **Description**: The GDC project identifier
- **Format**: Usually in format `PROGRAM-PROJECT`
- **Example**: `"TCGA-LUAD"`, `"TARGET-AML"`

## Optional Fields

### `local_file_path`
- **Type**: String
- **Description**: Full path to the file (for direct upload mode)
- **Example**: `"/data/sequencing/sample1.fastq.gz"`

### `file_size`
- **Type**: Integer
- **Description**: Size of the file in bytes
- **Example**: `1073741824`

### `md5sum`
- **Type**: String
- **Description**: MD5 checksum of the file
- **Example**: `"098f6bcd4621d373cade4e832627b4f6"`

### `data_type`
- **Type**: String
- **Description**: Type of genomic data
- **Example**: `"Aligned Reads"`, `"Unaligned Reads"`

### `experimental_strategy`
- **Type**: String
- **Description**: The experimental strategy used
- **Example**: `"RNA-Seq"`, `"WGS"`, `"WXS"`

## Extended Example

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "SAMPLE001_R1.fastq.gz",
    "project_id": "TCGA-LUAD",
    "file_size": 5368709120,
    "md5sum": "098f6bcd4621d373cade4e832627b4f6",
    "data_type": "Unaligned Reads",
    "experimental_strategy": "RNA-Seq",
    "local_file_path": "/data/project/fastq/SAMPLE001_R1.fastq.gz"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "file_name": "SAMPLE001_R2.fastq.gz",
    "project_id": "TCGA-LUAD",
    "file_size": 5368709120,
    "md5sum": "5d41402abc4b2a76b9719d911017c592",
    "data_type": "Unaligned Reads",
    "experimental_strategy": "RNA-Seq",
    "local_file_path": "/data/project/fastq/SAMPLE001_R2.fastq.gz"
  }
]
```

## YAML Format

You can also create metadata in YAML format and convert it to JSON:

### YAML Example

```yaml
- id: 550e8400-e29b-41d4-a716-446655440000
  file_name: sample1.fastq.gz
  project_id: TCGA-LUAD
  file_size: 5368709120
  data_type: Unaligned Reads
  experimental_strategy: RNA-Seq

- id: 550e8400-e29b-41d4-a716-446655440001
  file_name: sample2.fastq.gz
  project_id: TCGA-LUAD
  file_size: 5368709120
  data_type: Unaligned Reads
  experimental_strategy: RNA-Seq
```

### Convert YAML to JSON

```bash
gdc-yaml2json metadata.yaml metadata.json
```

## Generating Metadata

### From GDC Manifest

If you have a GDC manifest file, you can convert it to the required format:

```python
import pandas as pd
import json

# Read GDC manifest
df = pd.read_csv("gdc_manifest.txt", sep="\t")

# Create metadata
metadata = []
for _, row in df.iterrows():
    metadata.append({
        "id": row["id"],
        "file_name": row["filename"],
        "project_id": "YOUR-PROJECT-ID",  # Set your project ID
        "file_size": row["size"],
        "md5sum": row["md5"]
    })

# Save as JSON
with open("metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)
```

### From File List

```python
import os
import json
from pathlib import Path

files_dir = Path("/data/sequencing/")
metadata = []

# Generate metadata for FASTQ files
for file_path in files_dir.glob("*.fastq.gz"):
    metadata.append({
        "id": "GENERATE-UUID-FROM-GDC",  # Must be obtained from GDC
        "file_name": file_path.name,
        "project_id": "YOUR-PROJECT-ID",
        "file_size": file_path.stat().st_size,
        "local_file_path": str(file_path)
    })

# Save metadata
with open("metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)
```

## Validation

### Using the Built-in Validator

```bash
gdc-yaml2json --validate metadata.yaml metadata.json
```

### Python Validation

```python
import json
from pathlib import Path

def validate_metadata(metadata_file):
    """Validate GDC metadata format."""
    with open(metadata_file, 'r') as f:
        data = json.load(f)
    
    # Handle both array and object format
    if isinstance(data, dict) and 'files' in data:
        files = data['files']
    elif isinstance(data, list):
        files = data
    else:
        raise ValueError("Invalid metadata format")
    
    required_fields = ['id', 'file_name', 'project_id']
    
    for i, file_info in enumerate(files):
        # Check for required fields
        for field in required_fields:
            if field not in file_info and f"{field[:-1]}name" not in file_info:
                print(f"Error: Missing {field} in entry {i}")
                return False
        
        # Validate UUID format
        uuid = file_info.get('id') or file_info.get('uuid')
        if not uuid or len(uuid) != 36:
            print(f"Error: Invalid UUID format in entry {i}")
            return False
    
    print("Metadata validation passed!")
    return True

# Use validator
validate_metadata("metadata.json")
```

## Common Issues

### 1. Missing UUIDs

UUIDs must be obtained from GDC before upload. You cannot generate them yourself.

### 2. Incorrect Project ID Format

Project IDs typically follow the format `PROGRAM-PROJECT`:
- ✅ `TCGA-LUAD`
- ✅ `TARGET-AML`
- ❌ `TCGA/LUAD`
- ❌ `tcga-luad`

### 3. File Name Mismatches

Ensure `file_name` in metadata exactly matches the actual file name:
- ✅ `sample1.fastq.gz` matches `sample1.fastq.gz`
- ❌ `sample1.fastq` does not match `sample1.fastq.gz`
- ❌ `Sample1.fastq.gz` does not match `sample1.fastq.gz` (case sensitive)

## Best Practices

1. **Use Consistent Naming**: Keep file names consistent between metadata and actual files
2. **Include Checksums**: Add MD5 checksums for data integrity verification
3. **Organize by Project**: Group files by project_id for easier management
4. **Validate Before Upload**: Always validate metadata before starting uploads
5. **Keep Backups**: Save copies of metadata files for record keeping