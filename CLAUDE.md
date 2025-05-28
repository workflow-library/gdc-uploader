# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

gdc-uploader is a .NET Core console application that serves as a wrapper for the GDC Data Transfer Tool (gdc-client). It manages uploads of genomic sequence data files (BAM/FASTQ) to the National Cancer Institute's Genomic Data Commons.

## Project Structure

```
gdc-uploader/
├── src/upload2gdc/         # Main application
├── tests/
│   ├── gdc-client-simulator/  # Testing simulator
│   └── test-cwl.sh            # CWL test script
├── cwl/                    # CWL workflow definitions
│   ├── gdc-uploader.cwl
│   └── metadata-generator.cwl
├── Dockerfile              # Docker image definition
└── upload2gdc.sln         # Solution file
```

## Build and Run Commands

### Docker Build
```bash
docker build -t cgc-images.sbgenomics.com/david.roberson/gdc-utils:latest .
```

### CWL Testing
```bash
# Run the test script that demonstrates CWL usage
cd tests
./test-cwl.sh
```

### Production CWL Usage
```bash
# Upload files
cwltool --outdir ./output cwl/gdc-uploader.cwl upload-job.yml

# Generate metadata
cwltool --outdir ./output cwl/metadata-generator.cwl metadata-job.yml
```

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

## Important Guidelines

### Dockerfile Best Practices
- **NEVER** include `CMD` or `ENTRYPOINT` directives in Dockerfiles for this project
- The container will be executed via CWL tool (cwltool) or Seven Bridges platform
- The CWL definitions specify the entry points and commands