# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

gdc-uploader is a tool that manages uploads of genomic sequence data files (BAM/FASTQ) to the National Cancer Institute's Genomic Data Commons using the GDC Data Transfer Tool (gdc-client) directly with parallel execution support.

## Project Structure

Follows the OWL (Open Workflow Library) Apps Folder Pattern with flat structure.

```
gdc-uploader/
├── apps/                    # All CWL, Docker, and scripts (flat)
│   ├── gdc.Dockerfile      # Docker image definition
│   ├── gdc_upload.cwl      # Main upload workflow
│   ├── gdc_upload.sh       # Main upload script
│   ├── gdc_direct-upload.cwl    # Direct upload workflow
│   ├── gdc_direct-upload.sh     # Direct upload script
│   ├── gdc_metadata-generate.cwl # Metadata generation
│   ├── gdc_yaml2json.cwl   # YAML to JSON conversion
│   └── gdc_yaml2json.py    # YAML converter script
├── tests/
│   └── test-cwl.sh         # CWL test script
└── README.md              # Main documentation
```

## Architecture

### Current Implementation
- **Direct gdc-client usage**: The system now uses gdc-client directly without any wrapper applications
- **Parallel execution**: GNU parallel manages concurrent uploads with configurable thread count
- **Shell-based**: All logic is implemented in bash scripts for simplicity
- **CWL integration**: Provides CWL definitions for workflow platform compatibility

### Key Components

**Upload Flow**:
1. **gdc_upload.sh**: Main script that:
   - Parses command-line arguments
   - Reads GDC metadata JSON to extract file UUIDs
   - Searches for files in the specified directory
   - Uses GNU parallel to upload files concurrently
   - Handles retries for failed uploads
   - Generates upload report

2. **File Discovery**: 
   - Searches in common subdirectories (fastq/, uBam/, sequence-files/)
   - Falls back to recursive search if needed
   - Supports both structured and flat file organization

### External Dependencies
- **gdc-client**: The GDC Data Transfer Tool executable (included in Docker image)
- **GNU parallel**: For concurrent upload management
- **jq**: For JSON parsing
- **GDC Token**: Authentication token required for uploads

## Build and Run Commands

### Docker Build
```bash
docker build -f apps/gdc.Dockerfile -t gdc-uploader:latest .
```

### CWL Testing
```bash
cd tests
./test-cwl.sh
```

### Direct Script Usage
```bash
./apps/gdc_upload.sh \
  -m metadata.json \
  -t token.txt \
  -j 4 \
  -r 3 \
  /path/to/files
```

### CWL Usage
```bash
cwltool \
  --outdir ./output \
  apps/gdc_upload.cwl \
  --metadata_file /path/to/gdc-metadata.json \
  --files_directory /path/to/sequence-files \
  --token_file /path/to/gdc-token.txt \
  --thread_count 4 \
  --retry_count 3
```

## Important Guidelines

### Dockerfile Best Practices
- **NEVER** include `CMD` or `ENTRYPOINT` directives in Dockerfiles for this project
- The container will be executed via CWL tool (cwltool) or Seven Bridges platform
- The CWL definitions specify the entry points and commands

### Seven Bridges Platform Integration
- **Working Directory**: Seven Bridges executes from temporary directories
- **Input Files**: All input directories and files are mounted as read-only
- **File Discovery**: The script searches for files in various patterns to accommodate different organization
- **Output Handling**: All outputs are written to the current working directory

## Testing

### Standard Local Testing
```bash
./tests/test-cwl.sh
```

### Seven Bridges Style Testing
```bash
./tests/test-sb-style.sh
```

## VS Code Configuration

- Do not auto open files in VS Code

## Memories

- Always run tests using cwltool
- Create a versioning system in the cwl doc section (date + increment)
- The system now uses direct gdc-client calls instead of C# wrapper