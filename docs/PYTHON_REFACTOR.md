# Python Package Refactoring Summary

This document summarizes the major refactoring of gdc-uploader from shell scripts to a Python package.

## What Changed

### 1. Project Structure
- Created proper Python package structure under `src/gdc_uploader/`
- Moved Dockerfile to root directory
- Added `pyproject.toml` and `setup.py` for package configuration

### 2. Shell Scripts → Python Modules
All shell scripts have been converted to Python modules:
- `gdc_upload.sh` → `src/gdc_uploader/upload.py`
- `gdc_direct-upload.sh` → `src/gdc_uploader/direct_upload.py`
- `gdc_upload_single.sh` → `src/gdc_uploader/upload_single.py`
- `gdc_yaml2json.py` → `src/gdc_uploader/utils.py`

### 3. CLI Commands
The package provides the following CLI commands:
- `gdc-uploader` - Main command group
- `gdc-upload` - Upload with file discovery
- `gdc-direct-upload` - Direct upload
- `gdc-yaml2json` - YAML to JSON converter

### 4. Backward Compatibility
- Shell script wrappers remain in `cwl/` directory for compatibility
- CWL files updated to use new Python commands
- Docker image installs the Python package

## Installation

### Local Development
```bash
pip install -e .
```

### Docker
```bash
docker build -t gdc-uploader:latest .
```

## Usage

### Command Line
```bash
# Upload files
gdc-upload -m metadata.json -t token.txt -j 4 /path/to/files

# Direct upload
gdc-direct-upload -m metadata.json -t token.txt

# Convert YAML to JSON
gdc-yaml2json input.yaml output.json
```

### Python API
```python
from gdc_uploader import GDCUploader

uploader = GDCUploader(metadata_file, token_file, threads=4)
uploader.run(files_dir)
```

## Dependencies
- click (CLI framework)
- requests (HTTP client)
- pyyaml (YAML parsing)
- tqdm (progress bars)
- requests-toolbelt (upload progress)

## Benefits of Python Package
1. **Better Error Handling**: Python exceptions vs bash error codes
2. **Progress Bars**: Visual upload progress using tqdm
3. **Maintainability**: Cleaner code structure, type hints
4. **Testing**: Easier to write unit tests
5. **Distribution**: Can be installed via pip
6. **API Usage**: Can be imported and used programmatically