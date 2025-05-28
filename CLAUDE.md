# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

gdc-uploader is a .NET Core console application that serves as a wrapper for the GDC Data Transfer Tool (gdc-client). It manages uploads of genomic sequence data files (BAM/FASTQ) to the National Cancer Institute's Genomic Data Commons.

## Project Structure

```
gdc-uploader/
├── src/upload2gdc/         # Main application
├── tests/
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
docker build -t gdc-uploader:latest .
```

### CWL Testing
```bash
# Run the test script that demonstrates CWL usage
cd tests
./test-cwl.sh
```

### CWL Usage with Command-Line Arguments

#### Upload Files
```bash
cwltool \
  --outdir ./output \
  cwl/gdc-uploader.cwl \
  --metadata_file /path/to/gdc-metadata.json \
  --files_directory /path/to/sequence-files \
  --token_file /path/to/gdc-token.txt \
  --thread_count 4 \
  --retry_count 3 \
  --simulator true \
  --multipart "yes"
```

#### Generate Metadata
```bash
cwltool \
  --outdir ./output \
  cwl/metadata-generator.cwl \
  --upload_list /path/to/upload-list.txt \
  --experiment_type rnaseq \
  --use_dev_server false
```

#### Check Files Only (Dry Run)
```bash
cwltool \
  --outdir ./output \
  cwl/gdc-uploader.cwl \
  --metadata_file /path/to/gdc-metadata.json \
  --files_directory /path/to/sequence-files \
  --files_only true \
  --simulator true
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

### Seven Bridges Platform Integration
- **Execution Environment**: Seven Bridges creates temporary working directories (e.g., `task-002`) and changes the current working directory to that location
- **Input Files**: All input directories and files are mounted as **read-only** from separate locations (e.g., `/sbgenomics/Projects/.../`)
- **Command Generation**: Seven Bridges automatically generates CWL command lines based on the workflow definition and executes them from the temporary working directory
- **File Discovery**: The application has been enhanced to find files in both structured subdirectories (`fastq/`, `uBam/`) and directly in the base input directory to accommodate different file organization patterns
- **Output Handling**: All outputs are written to the temporary working directory and then collected by Seven Bridges

## Testing

The repository includes CWL definitions and test data. Multiple testing approaches are available:

### Standard Local Testing
```bash
# Run the basic test script
./tests/test-cwl.sh
```

### Seven Bridges Style Testing (Recommended)
To simulate Seven Bridges execution environment:

```bash
# Run Seven Bridges style test (creates task directories)
./tests/test-sb-style.sh
```

This approach:
- Creates incremental task directories (`./tests/tasks/task_001`, `task_002`, etc.)
- Changes working directory to the task directory (simulates Seven Bridges behavior)
- Uses absolute paths for all inputs (like Seven Bridges generates)
- Uses `--enable-pull` for Docker (ensures latest image is used)
- Outputs logs to the task directory

### Manual Seven Bridges Style Testing
```bash
# Create task directory
cd tests
mkdir -p tasks/task_999 && cd tasks/task_999

# Run with absolute paths and Docker
cwltool --enable-pull --outdir . /workspaces/gdc-uploader/cwl/gdc-uploader.cwl \
  --upload_report /workspaces/gdc-uploader/tests/test-data/upload-report.tsv \
  --metadata_file /workspaces/gdc-uploader/tests/test-data/gdc-metadata.json \
  --files_directory /workspaces/gdc-uploader/tests/test-data \
  --files_only

# Check results
cat gdc-upload-stdout.log
```

### Testing Best Practices for Seven Bridges Compatibility
- **Always use `--enable-pull`** to ensure Docker images are pulled
- **Use absolute paths** for all file inputs (like Seven Bridges does)
- **Test from temporary directories** to simulate Seven Bridges execution environment
- **Verify read-only input compatibility** (inputs should never be modified)

### Task Directory Management
- **Task directories**: `./tests/tasks/task_XXX` (incremental numbering)
- **Purpose**: Simulate Seven Bridges temporary working directories
- **Contents**: Each task directory contains:
  - `gdc-upload-stdout.log` - Application output
  - `gdc-upload-stderr.log` - Error output (usually empty)
  - Any additional output files generated by the workflow
- **Cleanup**: Task directories can be safely removed for cleanup
- **Debugging**: Check logs in task directories when investigating issues

### Known Issues Fixed
- Fixed array index out of bounds errors when parsing non-TracSeq format filenames
- Fixed console input blocking issues when running in non-interactive environments (e.g., Docker containers)  
- Fixed file discovery to work with files in both expected subdirectories (fastq/, uBam/) AND directly in the base directory (critical for Seven Bridges platform compatibility)

### Seven Bridges Specific Considerations
- **Working Directory**: Seven Bridges executes from temporary directories (e.g., `/sbgenomics/workspaces/.../tasks/task-002/`) 
- **Input Paths**: Input files are mounted from project locations (e.g., `/sbgenomics/Projects/.../`) as read-only
- **Path Resolution**: All file paths in command lines are absolute paths generated by Seven Bridges
- **Log Files**: Application logs are written to the temporary working directory and collected as outputs
- **File Organization**: Input files may be organized flat or in subdirectories depending on how they were uploaded to the project

## VS Code Configuration

- Do not auto open files in VS Code

## Memories

- Always run tests using cwltool
- Create a versioning system in the cwl doc section could be today's date and the just incrementing for each time you change it