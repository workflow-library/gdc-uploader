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
├── tests/
│   └── gdc-client-simulator/  # Testing simulator
├── cwl/                    # CWL workflow definitions
├── Dockerfile             # Docker image definition
└── upload2gdc.sln         # Solution file
```

## Build and Setup

### Local Development

```bash
# Clone repository
git clone https://github.com/your-repo/gdc-uploader.git
cd gdc-uploader/gdcupload-master

# Build the solution
dotnet build

# Run tests with simulator
dotnet run --project tests/gdc-client-simulator
```

### Docker Build

```bash
# Build Docker image
docker build -t gdc-uploader .

# Run with Docker
docker run -v /path/to/data:/data -v /path/to/token:/token gdc-uploader \
  --md /data/metadata.json \
  --files /data/files \
  --token /token/gdc-token.txt
```

## Usage

### Upload Files

```bash
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll \
  --ur ~/gdc-upload-report.tsv \
  --md ~/gdc-metadata-file.json \
  --files /proj/seq/tracseq/delivery \
  --token ~/token.txt
```

### Check Files (Dry Run)

```bash
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll \
  --md metadata.json \
  --files /path/to/files \
  --filesonly
```

### Generate Metadata

```bash
# For different experiment types
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll --mdgen uploadList.txt --mdgentype smallrna
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll --mdgen uploadList.txt --mdgentype rnaseq
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll --mdgen uploadList.txt --mdgentype rnaseqexome

# Using development server
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll --mdgen uploadList.txt --mdgentype smallrna --mdgendev
```

## CWL Workflows

The `cwl/` directory contains Common Workflow Language definitions:
- `gdc-uploader.cwl` - Main upload workflow
- `metadata-generator.cwl` - Metadata generation workflow

## Testing

Use the GDC client simulator for testing upload logic:

```bash
dotnet run --project tests/gdc-client-simulator [UUID] [speed]
# Speed options: fast, normal, slow
```

## Requirements

- .NET 5.0 SDK
- GDC Data Transfer Tool (gdc-client)
- Valid GDC authentication token




