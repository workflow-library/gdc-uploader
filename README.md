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

### Examples

```bash
# Basic upload
gdc-http-upload -m manifest.json -f sample_001.bam -t ~/.gdc-token

# With full paths
gdc-http-upload --manifest /data/manifests/batch1.json --file sample.fastq.gz --token /secure/token.txt
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

The tool shows real-time upload progress:

```
Parsing manifest for 'sample.fastq.gz'...
Found file: fastq/sample.fastq.gz
File ID: 550e8400-e29b-41d4-a716-446655440000
Starting upload...
Uploading: 100%|████████████| 1.23G/1.23G [02:34<00:00, 8.23MB/s]
✓ Upload successful!
Response: {
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "uploaded"
}
```

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