# CWL Command Reference

This document shows how to run the GDC Uploader using cwltool with command-line arguments.

## Prerequisites

- cwltool installed (`pip install cwltool`)
- Docker installed and running
- Valid GDC authentication token
- GDC-compliant metadata JSON file

## Main Upload Workflow

### Basic Upload
```bash
cwltool \
  --outdir ./output \
  cwl/gdc_upload.cwl \
  --metadata_file /path/to/gdc-metadata.json \
  --files_directory /path/to/sequence-files \
  --token_file /path/to/gdc-token.txt
```

### Upload with Custom Settings
```bash
cwltool \
  --outdir ./output \
  cwl/gdc_upload.cwl \
  --metadata_file /path/to/gdc-metadata.json \
  --files_directory /path/to/sequence-files \
  --token_file /path/to/gdc-token.txt \
  --thread_count 8 \
  --retry_count 5
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--metadata_file` | File | Required | GDC metadata JSON file with file UUIDs |
| `--files_directory` | Directory | Required | Directory containing files to upload |
| `--token_file` | File | Required | GDC authentication token file |
| `--thread_count` | int | 4 | Number of parallel upload threads |
| `--retry_count` | int | 3 | Number of retry attempts for failed uploads |

## Other Workflows

### Generate Metadata from YAML
```bash
cwltool \
  --outdir ./output \
  cwl/gdc_yaml2json.cwl \
  --yaml_file /path/to/metadata.yaml
```

### Direct Upload (Simplified)
```bash
cwltool \
  --outdir ./output \
  cwl/gdc_direct-upload.cwl \
  --metadata_file /path/to/gdc-metadata.json \
  --files_directory /path/to/files \
  --token_file /path/to/token.txt
```

### Generate Metadata (TracSeq Integration)
```bash
cwltool \
  --outdir ./output \
  cwl/gdc_metadata-generate.cwl \
  --upload_list /path/to/upload-list.txt \
  --experiment_type rnaseq \
  --use_dev_server false
```

## Docker Options

### Use Local Docker Image
```bash
# Build local image
cd cwl && docker build -f gdc.Dockerfile -t gdc-uploader:local .

# Run with local image (edit CWL to use local tag)
cwltool --no-container-pull --outdir ./output cwl/gdc_upload.cwl ...
```

### Resource Limits
```bash
# Enforce memory and CPU limits
cwltool \
  --strict-memory-limit \
  --strict-cpu-limit \
  --outdir ./output \
  cwl/gdc_upload.cwl ...
```

## Output Files

The workflow generates the following outputs:
- `upload-report.tsv` - Summary of upload status for each file
- `gdc-upload-stdout.log` - Standard output from the upload process
- `gdc-upload-stderr.log` - Error output (if any)
- `upload-{UUID}.log` - Individual log file for each file upload

## Important Notes

- All file paths must be absolute paths when using cwltool
- The token file should have restricted permissions (chmod 600)
- Files are discovered in common subdirectories (fastq/, uBam/, sequence-files/)
- Failed uploads are automatically retried based on retry_count
- Use task-numbered output directories to avoid conflicts between runs