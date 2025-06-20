# GDC Uploader Examples

## Basic Upload

Upload a single file with automatic progress detection:

```bash
python -m gdc_uploader.upload \
  --manifest manifest.json \
  --file sample1.fastq.gz \
  --token token.txt
```

## Progress Mode Examples

Force simple progress for Seven Bridges or log files:

```bash
python -m gdc_uploader.upload \
  --manifest manifest.json \
  --file sample1.fastq.gz \
  --token token.txt \
  --progress-mode simple
```

Disable progress output entirely:

```bash
python -m gdc_uploader.upload \
  --manifest manifest.json \
  --file sample1.fastq.gz \
  --token token.txt \
  --progress-mode none
```

## Batch Upload

Upload multiple files using a shell loop:

```bash
for file in sample1.fastq.gz sample2.fastq.gz sample3.fastq.gz; do
  python -m gdc_uploader.upload \
    --manifest manifest.json \
    --file "$file" \
    --token token.txt
done
```

## CWL Workflow

Run using CWL:

```bash
cwltool cwl/upload.cwl \
  --manifest manifest.json \
  --filename "sample.fastq.gz" \
  --token token.txt
```

## Python API

Programmatic usage:

```python
from pathlib import Path
from gdc_uploader import (
    validate_manifest,
    find_manifest_entry,
    validate_token,
    upload_file_with_progress,
    find_file
)

# Load and validate inputs
manifest_entries = validate_manifest(Path("manifest.json"))
entry = find_manifest_entry(manifest_entries, "sample.fastq.gz")
token = validate_token(Path("token.txt"))

# Find and upload file
file_path = find_file("sample.fastq.gz")
if file_path:
    result = upload_file_with_progress(
        file_path=file_path,
        file_id=entry['id'],
        token=token
    )
    print(f"Upload complete: {result}")
```

## Docker Usage

Build and run with Docker:

```bash
# Build image
docker build -t gdc-uploader .

# Run upload
docker run -v $(pwd):/data gdc-uploader \
  python -m gdc_uploader.upload \
  --manifest /data/manifest.json \
  --file sample.fastq.gz \
  --token /data/token.txt
```