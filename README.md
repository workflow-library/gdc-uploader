# GDC Uploader

Originally written by John McGee  
Edited by Hongwei Liu

## Overview

Manage uploads of sequence data to the NIH Genomic Data Commons using the gdc data transfer tool.

This Win/Linux/Mac console application is a wrapper for the GDC Data Transfer Tool (gdc-client).  
It manages uploads of genomic sequence data files to the National Cancer Institute.  
It requires that the data files are accessible via a file path from the OS upon which it runs.  
It is known to work on rc-dm2.its.unc.edu, an ITS-RC datamover node with the .NET Core SDK installed.  
https://gdc.cancer.gov/access-data/gdc-data-transfer-tool

## Project Structure

```
gdc-uploader/
├── src/
│   └── upload2gdc/         # Main application
├── cwl/                    # CWL workflow definitions
│   ├── gdc-uploader.cwl
│   └── metadata-generator.cwl
├── Dockerfile             # Docker image definition
├── tests/
│   ├── gdc-client-simulator/  # Testing simulator
│   └── test-cwl.sh           # CWL test script
└── upload2gdc.sln        # Solution file
```

## Build and Setup

### Docker Build

```bash
# Clone repository
git clone https://github.com/your-repo/gdc-uploader.git
cd gdc-uploader

# Build Docker image
docker build -t cgc-images.sbgenomics.com/david.roberson/gdc-utils:latest .
```

## Testing

Run the CWL test script to verify the setup:

```bash
cd tests
./test-cwl.sh
```

This test script:
- Creates test data files
- Generates a GDC metadata JSON file
- Runs the uploader in simulator mode
- Demonstrates all required inputs

## CWL Usage

### Upload Files with CWL

Create a job file (e.g., `upload-job.yml`):

```yaml
metadata_file:
  class: File
  path: /path/to/gdc-metadata.json
files_directory:
  class: Directory
  path: /path/to/sequence-files
token_file:
  class: File
  path: /path/to/gdc-token.txt
thread_count: 4
retry_count: 3
multipart: "yes"
```

Run with cwltool:

```bash
cwltool --outdir ./output cwl/gdc-uploader.cwl upload-job.yml
```

### Generate Metadata with CWL

Create a job file (e.g., `metadata-job.yml`):

```yaml
upload_list:
  class: File
  path: /path/to/upload-list.txt
experiment_type: rnaseq  # Options: smallrna, rnaseq, rnaseqexome
use_dev_server: false
```

Run with cwltool:

```bash
cwltool --outdir ./output cwl/metadata-generator.cwl metadata-job.yml
```

## Requirements

- .NET 5.0 SDK
- GDC Data Transfer Tool (gdc-client)
- Valid GDC authentication token




