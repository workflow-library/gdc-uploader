# GDC Uploader Technical Architecture

## Overview

The GDC Uploader is a containerized tool that manages parallel uploads of genomic data files to the NIH Genomic Data Commons (GDC) using the official gdc-client tool.

## Architecture Components

### 1. CWL Workflows (cwl/)
- **gdc_upload.cwl** - Main upload workflow with parallel execution
- **gdc_direct-upload.cwl** - Simplified single-file upload
- **gdc_metadata-generate.cwl** - TracSeq integration for metadata generation
- **gdc_yaml2json.cwl** - YAML to JSON metadata conversion

### 2. Shell Scripts (cwl/)
- **gdc_upload.sh** - Main orchestration script
  - Parses GDC metadata JSON
  - Discovers files in multiple directory patterns
  - Manages parallel uploads via GNU parallel
  - Handles retry logic
  - Generates upload reports

- **gdc_direct-upload.sh** - Direct upload wrapper
- **gdc_yaml2json.py** - Python script for YAML conversion

### 3. Docker Container
- **Base**: Ubuntu 20.04
- **Key Components**:
  - gdc-client v1.6.1 (official GDC tool)
  - GNU parallel for concurrent uploads
  - jq for JSON parsing
  - Python 3 with PyYAML

### 4. File Discovery Logic

The system searches for files in this order:
1. Common subdirectories: `fastq/`, `uBam/`, `sequence-files/`
2. Base directory
3. Recursive search (fallback)

### 5. Parallel Upload Strategy

```
Metadata JSON → Extract UUIDs → GNU Parallel → gdc-client upload
     ↓              ↓                ↓              ↓
 [{id, file}]   (id, filename)   N threads    Individual uploads
```

## Data Flow

1. **Input**: 
   - GDC metadata JSON (with file UUIDs)
   - Directory containing genomic files
   - GDC authentication token

2. **Processing**:
   ```bash
   jq '.[] | "\(.id) \(.file_name)"' metadata.json | \
   parallel -j $THREADS upload_file {1} {2}
   ```

3. **Output**:
   - upload-report.tsv (status per file)
   - Individual log files per upload
   - Process logs (stdout/stderr)

## Security Considerations

- Token files should have restricted permissions (600)
- Containers run with read-only root filesystem
- Network isolation in CWL execution
- No credentials stored in images

## Error Handling

1. **File Not Found**: Logged and marked as FAILED
2. **Upload Failure**: Automatic retry (configurable)
3. **Network Issues**: Handled by gdc-client retry logic
4. **Authentication**: Clear error messages for token issues

## Performance

- Parallel uploads: 1-32 threads (default: 4)
- Memory usage: ~100MB per thread
- Network bandwidth: Limited by GDC server
- Retry overhead: Exponential backoff in gdc-client

## Integration Points

### CWL Platforms
- Seven Bridges Genomics
- Terra/FireCloud
- DNAnexus
- Any CWL-compliant platform

### File Systems
- Local filesystem
- Network-attached storage
- Cloud storage (when mounted)

### Monitoring
- Exit codes indicate success/failure
- Detailed logs for troubleshooting
- TSV report for batch status

## Limitations

1. Requires pre-generated GDC metadata
2. Files must match metadata filenames exactly
3. Token must have upload permissions
4. No built-in scheduling or queuing
5. Limited to gdc-client capabilities