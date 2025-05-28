# GDC Uploader

Originally written by John McGee  
Edited by Hongwei Liu

## Overview

A .NET Core console application that manages uploads of genomic sequence data files (FASTQ/BAM) to the NIH Genomic Data Commons (GDC). This tool serves as a robust wrapper for the GDC Data Transfer Tool (gdc-client) with features like multi-threaded uploads, retry logic, and comprehensive testing capabilities.

**Key Features:**
- Multi-threaded parallel uploads with configurable thread count
- Automatic retry mechanism for failed uploads  
- File verification mode to check data availability before uploading
- Simulator mode for testing upload logic without actual transfers
- Support for TracSeq naming conventions and generic filename formats
- CWL (Common Workflow Language) integration for workflow platforms
- Docker containerization for consistent deployment

🔗 **GDC Resources:** https://gdc.cancer.gov/access-data/gdc-data-transfer-tool

## Project Structure

```
gdc-uploader/
├── src/
│   └── upload2gdc/         # Main application
├── cwl/                    # CWL workflow definitions
│   ├── gdc-uploader.cwl
│   └── metadata-generator.cwl
├── tests/
│   ├── test-data/            # Test data files
│   ├── test-cwl.sh           # CWL test script
│   └── TEST-RESULTS.md       # Test execution results
├── Dockerfile             # Docker image definition
└── upload2gdc.sln        # Solution file
```

## Quick Start

### 1. Build Docker Image

```bash
# Clone repository and build
git clone <repository-url>
cd gdc-uploader
docker build -t gdc-uploader .
```

### 2. Run Tests

```bash
# Verify everything works with included test data
cd tests
./test-cwl.sh
```

### 3. Production Usage

```bash
# Check files exist before uploading
cwltool --outdir ./output cwl/gdc-uploader.cwl \
  --upload_report /path/to/upload-report.tsv \
  --metadata_file /path/to/metadata.json \
  --files_directory /path/to/files \
  --files_only

# Production upload
cwltool --outdir ./output cwl/gdc-uploader.cwl \
  --upload_report /path/to/upload-report.tsv \
  --metadata_file /path/to/metadata.json \
  --files_directory /path/to/files \
  --token_file /path/to/gdc-token.txt \
  --thread_count 4
```

## Usage Modes

### File Verification Only
Check if all required files exist without uploading:
```bash
cwltool cwl/gdc-uploader.cwl \
  --metadata_file metadata.json \
  --files_directory /path/to/files \
  --files_only
```

### Simulator Mode (Testing)
Test upload logic without actual transfers:
```bash
cwltool cwl/gdc-uploader.cwl \
  --upload_report upload-report.tsv \
  --metadata_file metadata.json \
  --files_directory /path/to/files \
  --token_file token.txt \
  --simulator
```

### Production Upload
Real upload to GDC:
```bash
cwltool cwl/gdc-uploader.cwl \
  --upload_report upload-report.tsv \
  --metadata_file metadata.json \
  --files_directory /path/to/files \
  --token_file token.txt \
  --thread_count 4 \
  --retry_count 3
```

## File Requirements

### Input Files
- **Upload Report** (TSV): GDC-generated file with UUIDs and metadata
- **Metadata File** (JSON): GDC-compliant metadata for each file
- **Sequence Files**: FASTQ/BAM files organized in expected directory structure
- **GDC Token**: Authentication token from GDC portal

### Directory Structure
```
files_directory/
├── fastq/              # FASTQ files go here
│   ├── file1.fastq.gz
│   └── file2.fastq.gz
└── uBam/              # BAM files organized by run ID
    └── run_id/
        ├── file1.bam
        └── file2.bam
```

## Documentation

- 📖 **[Complete Usage Guide](docs/usage-diagram.md)** - Detailed workflows and command reference
- 🧪 **[Test Data](tests/test-data/)** - Sample files for testing
- 🐳 **[Docker Usage](docs/README.md)** - Container deployment guide
- 📋 **[CLAUDE.md](CLAUDE.md)** - Developer reference for AI assistance

## Requirements

- **Runtime**: .NET 5.0 or Docker
- **Dependencies**: GDC Data Transfer Tool (gdc-client) - included in Docker image
- **Authentication**: Valid GDC token from https://portal.gdc.cancer.gov/




