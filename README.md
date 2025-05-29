# GDC Uploader

Originally written by John McGee  
Edited by Hongwei Liu

## Overview

A tool that manages uploads of genomic sequence data files (FASTQ/BAM) to the NIH Genomic Data Commons (GDC) using the GDC Data Transfer Tool (gdc-client) directly with parallel execution support.

**Key Features:**
- Parallel uploads using GNU parallel with configurable thread count
- Automatic retry mechanism for failed uploads  
- Direct gdc-client integration without intermediate wrappers
- Support for various file organization patterns
- CWL (Common Workflow Language) integration for workflow platforms
- Docker containerization for consistent deployment

🔗 **GDC Resources:** https://gdc.cancer.gov/access-data/gdc-data-transfer-tool

## Project Structure

```
gdc-uploader/
├── apps/                    # OWL Apps Pattern - flat directory
│   ├── gdc.Dockerfile      # Docker image definition
│   ├── gdc_upload.cwl      # Main upload workflow
│   ├── gdc_upload.sh       # Upload script
│   ├── gdc_direct-upload.cwl    # Direct upload workflow
│   ├── gdc_direct-upload.sh     # Direct upload script
│   ├── gdc_metadata-generate.cwl # Metadata generation
│   ├── gdc_yaml2json.cwl   # YAML to JSON conversion
│   └── gdc_yaml2json.py    # YAML converter script
├── tests/
│   ├── test-data/         # Test data files
│   ├── test-cwl.sh        # CWL test script
│   └── TEST-RESULTS.md    # Test execution results
└── repos/                 # External repositories
```

## Quick Start

### 1. Build Docker Image

```bash
# Clone repository and build
git clone <repository-url>
cd gdc-uploader
docker build -f apps/gdc.Dockerfile -t cgc-images.sbgenomics.com/david.roberson/gdc-utils:latest .
```

### 2. Run Tests

```bash
# Verify everything works with included test data
cd tests
./test-cwl.sh
```

### 3. Production Usage

```bash
# Production upload
cwltool --outdir ./output apps/gdc_upload.cwl \
  --metadata_file /path/to/metadata.json \
  --files_directory /path/to/files \
  --token_file /path/to/gdc-token.txt \
  --thread_count 4
```

## Usage Examples

### Basic Upload
Upload files to GDC with default settings:
```bash
cwltool apps/gdc_upload.cwl \
  --metadata_file metadata.json \
  --files_directory /path/to/files \
  --token_file token.txt
```

### Parallel Upload with Retries
Upload with 8 parallel threads and 5 retry attempts:
```bash
cwltool apps/gdc_upload.cwl \
  --metadata_file metadata.json \
  --files_directory /path/to/files \
  --token_file token.txt \
  --thread_count 8 \
  --retry_count 5
```

### Direct Script Usage
You can also use the upload script directly without CWL:
```bash
./apps/gdc_upload.sh \
  -m metadata.json \
  -t token.txt \
  -j 4 \
  -r 3 \
  /path/to/files
```

## File Requirements

### Input Files
- **Metadata File** (JSON): GDC-compliant metadata with file UUIDs
- **Sequence Files**: FASTQ/BAM files 
- **GDC Token**: Authentication token from GDC portal

### Directory Structure
The tool supports flexible file organization:

**Option 1 - Structured:**
```
files_directory/
├── fastq/              # FASTQ files
│   ├── file1.fastq.gz
│   └── file2.fastq.gz
└── uBam/              # BAM files
    ├── file1.bam
    └── file2.bam
```

**Option 2 - Flat:**
```
files_directory/
├── file1.fastq.gz     # All files in base directory
├── file2.fastq.gz
├── file1.bam
└── file2.bam
```

## Output Files

The tool generates:
- `upload-report.tsv`: Report with upload status for each file
- `upload-*.log`: Individual log files for each file upload
- `gdc-upload-stdout.log`: Overall process output
- `gdc-upload-stderr.log`: Error output

## Documentation

- 📖 **[Complete Usage Guide](docs/usage-diagram.md)** - Detailed workflows and command reference
- 🧪 **[Test Data](tests/test-data/)** - Sample files for testing
- 🐳 **[Docker Usage](docs/README.md)** - Container deployment guide
- 📋 **[CLAUDE.md](CLAUDE.md)** - Developer reference

## Requirements

- **Dependencies**: 
  - GDC Data Transfer Tool (gdc-client) - included in Docker image
  - GNU parallel - included in Docker image
  - jq - included in Docker image
- **Authentication**: Valid GDC token from https://portal.gdc.cancer.gov/


