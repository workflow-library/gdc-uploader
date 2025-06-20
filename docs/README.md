# GDC Uploader Documentation

## Quick Start Guide

The GDC Uploader is a simple tool for uploading files to the Genomic Data Commons (GDC) with environment-aware progress monitoring.

### Installation

```bash
pip install -e .
```

### Basic Usage

Upload a file using a manifest:

```bash
python -m gdc_uploader.upload \
  --manifest manifest.json \
  --file sample.fastq.gz \
  --token token.txt
```

### Progress Display

The uploader automatically detects your environment and chooses the appropriate progress display:

- **Interactive terminals**: Shows a progress bar with speed and ETA
- **Seven Bridges/CWL**: Shows simple percentage updates (10% increments)
- **Non-TTY environments**: Shows simple percentage updates

You can override the automatic detection:

```bash
# Force simple progress (good for logs)
python -m gdc_uploader.upload ... --progress-mode simple

# Force progress bar
python -m gdc_uploader.upload ... --progress-mode bar

# Disable progress
python -m gdc_uploader.upload ... --progress-mode none
```

### Requirements

- Python ≥ 3.9
- GDC manifest JSON file
- Valid GDC authentication token
- Files referenced in manifest

### Command Options

- `--manifest, -m`: Path to GDC manifest JSON file (required)
- `--file, -f`: Filename to upload from manifest (required)  
- `--token, -t`: Path to GDC token file (required)
- `--progress-mode, -p`: Progress display mode: auto, simple, bar, none (default: auto)

The tool will automatically search for files in common subdirectories like `fastq/`, `bam/`, and `data/`.

See [API.md](API.md) for programmatic usage and [EXAMPLES.md](EXAMPLES.md) for more examples.