# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

gdc-uploader is a .NET Core console application that serves as a wrapper for the GDC Data Transfer Tool (gdc-client). It manages uploads of genomic sequence data files (BAM/FASTQ) to the National Cancer Institute's Genomic Data Commons.

## Project Structure

```
gdcupload-master/
├── src/upload2gdc/         # Main application
├── tests/gdc-client-simulator/  # Testing simulator
├── cwl/                    # CWL workflow definitions
│   ├── gdc-uploader.cwl
│   └── metadata-generator.cwl
├── Dockerfile              # Docker image definition
├── .dockerignore
└── upload2gdc.sln         # Solution file
```

## Build and Run Commands

### Build
```bash
cd gdcupload-master
dotnet build
```

### Run
```bash
# Show help
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll --help

# Upload files
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll --ur ~/gdc-upload-report.tsv --md ~/gdc-metadata-file.json --files /proj/seq/tracseq/delivery --token ~/token.txt

# Check if files are in place (dry run)
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll --md metadata.json --files /path/to/files --filesonly

# Generate GDC metadata
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll --mdgen uploadList.txt --mdgentype smallrna
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll --mdgen uploadList.txt --mdgentype rnaseq
dotnet src/upload2gdc/bin/Debug/net5.0/upload2gdc.dll --mdgen uploadList.txt --mdgentype rnaseqexome
```

### Docker Commands
```bash
# Build Docker image
docker build -t gdc-uploader .

# Run with Docker
docker run -v /path/to/data:/data -v /path/to/token:/token gdc-uploader \
  --md /data/metadata.json \
  --files /data/files \
  --token /token/gdc-token.txt
```

### Test with Simulator
```bash
# Build and run the GDC client simulator for testing
dotnet run --project tests/gdc-client-simulator [UUID] [speed]

# Speed options: fast (5-10s), normal (15-30s), slow (200-600s, most realistic)
# Example:
dotnet run --project tests/gdc-client-simulator abc-123-def fast
```

The simulator mimics gdc-client behavior with ~50% failure rate to test error handling and retry logic.

## Architecture

### Solution Structure
- **upload2gdc.sln**: Main solution file containing both projects
- **upload2gdc/**: Main upload application
  - Multi-threaded upload management with configurable thread count
  - Retry mechanism for failed uploads
  - Progress tracking and reporting
- **gdc-client-simulator/**: Testing tool that simulates GDC client responses

### Key Components

**Upload Flow**:
1. **Program.cs**: Orchestrates the upload process
   - Parses command-line arguments
   - Manages thread pool for parallel uploads
   - Monitors upload progress and generates reports
   - Handles retries for failed uploads

2. **GenerateMetadata.cs**: 
   - Calls TracSeq API to retrieve experiment data
   - Generates GDC-compliant JSON metadata for different experiment types (RNA-seq, small RNA, RNA-seq exome)
   - Supports both production and development GDC servers

3. **Util.cs**: 
   - File discovery logic using regex patterns
   - Thread-safe logging utilities
   - Progress reporting functions

### External Dependencies
- **gdc-client**: The actual GDC Data Transfer Tool executable must be available in the system PATH
- **TracSeq API**: Used for retrieving experiment metadata
- **GDC Token**: Authentication token required for uploads

### Thread Safety
- Uses thread-safe collections (ConcurrentDictionary, ConcurrentBag) for managing upload state
- Each upload thread maintains its own log file
- Thread-safe progress reporting with locks on shared resources