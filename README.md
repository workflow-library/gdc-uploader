# GDC HTTP Upload

A simple, focused tool for uploading files to the Genomic Data Commons (GDC) using HTTP with real-time progress monitoring.

## Overview

This tool provides a streamlined way to upload genomic data files to the GDC using their HTTP API. It features:

- Real-time progress monitoring with visual progress bar
- Chunked upload for memory efficiency
- Support for large files (tested up to 100GB)
- Simple command-line interface
- Minimal dependencies

## Installation

```bash
pip install -e .
```

Or using pip:

```bash
pip install gdc-uploader
```

## Requirements

- Python 3.8+
- click>=8.0
- requests>=2.25
- tqdm>=4.60

## Usage

### Basic Command

```bash
gdc-http-upload --manifest manifest.json --file sample.fastq.gz --token token.txt
```

### Options

- `--manifest`, `-m`: Path to GDC manifest JSON file (required)
- `--file`, `-f`: Target filename to upload from the manifest (required)
- `--token`, `-t`: Path to file containing GDC authentication token (required)
- `--progress-mode`, `-p`: Progress display mode: `auto`, `simple`, `bar`, `none` (default: auto)
- `--output`, `-o`: Save output to log file (default: no file output)
- `--append`: Append to output file instead of overwriting

### Examples

```bash
# Basic upload
gdc-http-upload -m manifest.json -f sample_001.bam -t ~/.gdc-token

# With full paths
gdc-http-upload --manifest /data/manifests/batch1.json --file sample.fastq.gz --token /secure/token.txt

# Save output to log file
gdc-http-upload -m manifest.json -f sample.bam -t token.txt -o upload.log

# Append to existing log file
gdc-http-upload -m manifest.json -f sample2.bam -t token.txt -o upload.log --append
```

## Manifest Format

The tool expects a GDC manifest in JSON format:

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "sample1.fastq.gz",
    "project_id": "PROJECT-ID"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001", 
    "file_name": "sample2.fastq.gz",
    "project_id": "PROJECT-ID"
  }
]
```

## Progress Display

The tool shows real-time upload progress with GB sizes and MB/s speed:

```text
Parsing manifest for 'sample.fastq.gz'...
Found file: fastq/sample.fastq.gz
File ID: 550e8400-e29b-41d4-a716-446655440000
File size: 10,737,418,240 bytes
Starting upload...
Uploading: 25.00% (2.50/10.00 GB) - 15.75 MB/s
Uploading: 50.00% (5.00/10.00 GB) - 16.23 MB/s
Uploading: 75.00% (7.50/10.00 GB) - 15.98 MB/s
Uploading: 100.00% (10.00/10.00 GB) - 16.05 MB/s
✓ Upload successful!
Response: {
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "uploaded"
}
```

## Log File Output

When using the `--output` option, the tool creates a detailed log file with timestamps:

```text
============================================================
GDC Upload Log - 2024-01-15T10:30:45.123456
============================================================

[2024-01-15 10:30:45] Parsing manifest for 'sample.fastq.gz'...
[2024-01-15 10:30:45] Manifest: manifest.json
[2024-01-15 10:30:45] Target file: sample.fastq.gz
[2024-01-15 10:30:45] Token file: token.txt
[2024-01-15 10:30:45] Progress mode: auto
[2024-01-15 10:30:45] 
[2024-01-15 10:30:45] Found file: /data/fastq/sample.fastq.gz
[2024-01-15 10:30:45] File ID: 550e8400-e29b-41d4-a716-446655440000
[2024-01-15 10:30:45] File size: 10,737,418,240 bytes
[2024-01-15 10:30:45] Starting upload...
[2024-01-15 10:30:50] Uploading: 5.00% (0.50/10.00 GB) - 102.40 MB/s
[2024-01-15 10:30:55] Uploading: 10.00% (1.00/10.00 GB) - 102.40 MB/s
...
[2024-01-15 10:32:15] Uploading: 100.00% (10.00/10.00 GB) - 85.90 MB/s
[2024-01-15 10:32:15] ✓ Upload successful!
[2024-01-15 10:32:15] Response: {
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "uploaded",
  "size": 10737418240,
  "created_datetime": "2024-01-15T10:32:15Z"
}

============================================================
Log ended at 2024-01-15T10:32:15.654321
============================================================
```

The log file includes:
- Timestamps for each operation
- Complete upload parameters
- Progress updates with speeds
- Full API response
- Any errors encountered

## File Discovery

The tool automatically searches for files in common subdirectories:
- Current directory
- `fastq/`
- `bam/`
- `data/`

## Error Handling

The tool provides clear error messages for:
- File not found in manifest
- File not found on disk
- Authentication failures
- Network errors
- Invalid manifest format

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: [https://github.com/open-workflow-library/gdc-uploader/issues](https://github.com/open-workflow-library/gdc-uploader/issues)
- GDC Support: [https://gdc.cancer.gov/support](https://gdc.cancer.gov/support)