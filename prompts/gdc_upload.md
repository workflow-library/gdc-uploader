---
name: gdc_upload
version: 2.0.0
description: Upload genomic data files to the NCI Genomic Data Commons using parallel processing
docker_image: ghcr.io/open-workflow-library/gdc-uploader:latest
requirements:
  ram_min: 2048
  cores_min: 2
  base_image: ubuntu:22.04
  system_packages:
    - parallel
    - jq
  python_packages:
    - click
    - requests
    - pyyaml
    - tqdm
    - rich
    - pydantic
---

# GDC Upload Tool

The primary tool for uploading genomic sequence data files (BAM, FASTQ) to the National Cancer Institute's Genomic Data Commons. This tool uses the official gdc-client with parallel processing support for efficient uploads.

## Inputs

- metadata_file: GDC metadata JSON file containing file UUIDs and paths (File)
- token_file: GDC authentication token file (File)
- files_directory: Directory containing the files to upload (Directory)
- thread_count: Number of parallel upload threads (int)
- retry_count: Number of retry attempts for failed uploads (int)

## Outputs

- upload_report: Tab-separated report of upload results (File)
- log_files: Upload log files for debugging (File)

## Command

```bash
gdc-upload -m {metadata_file} -t {token_file} -j {thread_count} -r {retry_count} {files_directory}
```

## Requirements

- Valid GDC authentication token
- GDC metadata JSON with file UUIDs
- Files referenced in metadata must exist
- Internet connectivity to GDC API

## Usage Examples

### Basic Upload
```bash
gdc-upload -m metadata.json -t token.txt /data/sequencing_files/
```

### Parallel Upload with 8 Threads
```bash
gdc-upload -m metadata.json -t token.txt -j 8 /data/sequencing_files/
```

### Upload with Retries
```bash
gdc-upload -m metadata.json -t token.txt -r 5 /data/sequencing_files/
```

## File Discovery

The tool searches for files in the following order:
1. Direct path from metadata
2. Common subdirectories: `fastq/`, `uBam/`, `sequence-files/`
3. Recursive search in the provided directory

## Output Format

The upload report (`upload-report.tsv`) contains:
- File UUID
- Filename
- Upload status (SUCCESS/FAILED/NOT_FOUND)
- Number of attempts
- Error message (if failed)

## Error Handling

- Automatic retry with exponential backoff
- Detailed error logging for troubleshooting
- Partial upload recovery support
- Network interruption handling

## Performance Optimization

- Parallel uploads using GNU parallel
- Connection pooling for API calls
- Efficient file discovery algorithms
- Progress tracking with minimal overhead

## Security Considerations

- Token file should have restricted permissions (600)
- Tokens expire after 30 days
- Never commit tokens to version control
- Use environment variables for CI/CD