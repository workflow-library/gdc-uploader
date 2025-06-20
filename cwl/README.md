# CWL Tool Definition for GDC Uploader

This directory contains the Common Workflow Language (CWL) tool definition for the GDC HTTP uploader.

## Files

- `gdc_uploader.cwl` - Main CWL tool definition
- `test-job.yml` - Example job file with all parameters
- `test-job-minimal.yml` - Minimal job file with only required parameters

## Running the Tool

```bash
# Run with minimal parameters
cwl-runner gdc_uploader.cwl test-job-minimal.yml

# Run with all parameters including logging
cwl-runner gdc_uploader.cwl test-job.yml
```

## Input Parameters

### Required Parameters

- **manifest** (File): GDC manifest file in JSON or YAML format
- **file_to_upload** (File): The actual file to upload to GDC
- **token** (File): GDC authentication token file

### Optional Parameters

- **progress_mode** (string): Progress display mode
  - `auto` (default): Automatically detect environment
  - `simple`: Simple progress for non-TTY environments
  - `bar`: Progress bar (requires TTY)
  - `none`: No progress output

- **output_file** (string): Path for log file output
  - If specified, creates a detailed log with timestamps
  - Example: `"upload.log"`

- **append_log** (boolean): Append to existing log file
  - `false` (default): Overwrite existing log file
  - `true`: Append to existing log file

## Outputs

- **upload_log**: Standard output captured to `upload_output.txt`
- **log_file**: Optional log file (only if `output_file` is specified)

## Example Job Files

### Minimal Job
```yaml
manifest:
  class: File
  path: /data/manifest.json

file_to_upload:
  class: File
  path: /data/sample.bam

token:
  class: File
  path: /secure/token.txt
```

### Full Job with Logging
```yaml
manifest:
  class: File
  path: /data/manifest.json

file_to_upload:
  class: File
  path: /data/sample.bam

token:
  class: File
  path: /secure/token.txt

output_file: "gdc_upload.log"
append_log: false
progress_mode: "simple"
```

## Docker Image

The tool uses the Docker image: `ghcr.io/workflow-library/gdc-uploader:latest`

## Environment

The tool automatically sets `CWL_RUNTIME=true` environment variable, which triggers:
- Simple progress mode (no progress bars)
- Environment-aware output formatting