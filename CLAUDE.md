# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The gdc-uploader is a Python tool for uploading genomic data files to the Genomic Data Commons (GDC) using their HTTP API. It features environment-aware progress display, chunked uploads for large files, and CWL workflow integration.

## Development Commands

### Installation and Setup
```bash
# Install in development mode (editable)
pip install -e .

# Install dependencies
pip install -r requirements.txt
```

### Running the Tool
```bash
# Main command (after installation)
gdc-http-upload --manifest manifest.json --file sample.fastq.gz --token token.txt

# Running as Python module (for development)
python -m gdc_uploader.upload --manifest manifest.json --file sample.fastq.gz --token token.txt
```

### Testing
```bash
# Run all tests with pytest
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=gdc_uploader tests/

# Run CWL tests
cd tests && ./run-cwl-test.sh
```

### Docker
```bash
# Build Docker image
docker build -t gdc-uploader .

# Run with Docker
docker run -v $(pwd):/data gdc-uploader gdc-http-upload -m /data/manifest.json -f sample.fastq.gz -t /data/token.txt
```

## Architecture Overview

### Core Modules
- **src/gdc_uploader/upload.py**: Main entry point with CLI and upload logic. Handles environment detection (TTY, SBP, CWL) and progress display strategies.
- **src/gdc_uploader/validate.py**: Manifest parsing (JSON/YAML) and token validation logic.
- **src/gdc_uploader/utils.py**: Helper functions for file discovery, chunked reading, and size formatting.

### Key Design Patterns
1. **Environment Detection**: The upload module detects execution environment (TTY, Seven Bridges Platform, CWL) and adjusts progress display accordingly.
2. **Progress Handling**: Uses tqdm for TTY environments, simple progress for CWL, and JSON progress for SBP integration.
3. **File Discovery**: Automatically searches in common subdirectories (fastq/, bam/, data/) when looking for files.
4. **Chunked Upload**: Reads and uploads files in chunks (default 8MB) for memory efficiency with large genomic files.

### Testing Structure
- **tests/unit/**: Unit tests for each module (test_upload.py, test_validate.py, test_utils.py)
- **tests/integration/**: Integration tests including SBP environment tests
- **tests/fixtures/**: Sample manifest files and test data
- **tests/run-cwl-test.sh**: Script for testing CWL functionality

### CWL Integration
The project includes Common Workflow Language support via:
- **cwl/gdc_uploader.cwl**: CWL tool definition
- **Dockerfile**: Container image for CWL compatibility (no ENTRYPOINT/CMD)

### Entry Points
- CLI command: `gdc-http-upload` (defined in pyproject.toml)
- Python module: `python -m gdc_uploader.upload`
- Main function: `gdc_uploader.upload:main`

## Important Notes
- The project uses modern Python packaging with pyproject.toml
- No linting configuration is currently set up (no .flake8, .eslintrc, etc.)
- The tool supports both JSON and YAML manifest formats
- File paths are resolved relative to the manifest location with automatic subdirectory search