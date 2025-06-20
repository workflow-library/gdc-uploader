# GDC Uploader API Reference

## Core Functions

### Upload Module

```python
from gdc_uploader import upload_file_with_progress

# Upload a file
result = upload_file_with_progress(
    file_path=Path("sample.fastq.gz"),
    file_id="abc123", 
    token="your-token",
    chunk_size=8192
)
```

### Validation Module

```python
from gdc_uploader import validate_manifest, validate_token

# Validate manifest
entries = validate_manifest(Path("manifest.json"))

# Validate token
token = validate_token(Path("token.txt"))

# Find specific file
entry = find_manifest_entry(entries, "sample.fastq.gz")
```

### Utility Functions

```python
from gdc_uploader import find_file, format_size

# Find file in common directories
file_path = find_file("sample.fastq.gz")

# Format file size
size_str = format_size(1234567890)  # "1.1 GB"
```

## Error Handling

All functions raise `ValueError` for validation errors and `requests.RequestException` for upload failures.

```python
try:
    upload_file_with_progress(...)
except ValueError as e:
    print(f"Validation error: {e}")
except requests.RequestException as e:
    print(f"Upload failed: {e}")
```