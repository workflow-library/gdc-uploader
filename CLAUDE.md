# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

gdc-uploader is a tool that manages uploads of genomic sequence data files (BAM/FASTQ) to the National Cancer Institute's Genomic Data Commons using the GDC Data Transfer Tool (gdc-client) directly with parallel execution support.

## Project Structure

Follows the OWL (Open Workflow Library) Apps Folder Pattern with flat structure.

```
gdc-uploader/
├── cwl/                    # All CWL, Docker, and scripts (flat)
│   ├── gdc.Dockerfile      # Docker image definition
│   ├── gdc_upload.cwl      # Main upload workflow
│   ├── gdc_upload.sh       # Main upload script
│   ├── gdc_direct-upload.cwl    # Direct upload workflow
│   ├── gdc_direct-upload.sh     # Direct upload script
│   ├── gdc_metadata-generate.cwl # Metadata generation
│   ├── gdc_yaml2json.cwl   # YAML to JSON conversion
│   └── gdc_yaml2json.py    # YAML converter script
├── tests/
│   └── test-cwl.sh         # CWL test script
└── README.md              # Main documentation
```

## Architecture

### Current Implementation
- **Direct gdc-client usage**: The system now uses gdc-client directly without any wrapper applications
- **Parallel execution**: GNU parallel manages concurrent uploads with configurable thread count
- **Shell-based**: All logic is implemented in bash scripts for simplicity
- **CWL integration**: Provides CWL definitions for workflow platform compatibility

### Key Components

**Upload Flow**:
1. **gdc_upload.sh**: Main script that:
   - Parses command-line arguments
   - Reads GDC metadata JSON to extract file UUIDs
   - Searches for files in the specified directory
   - Uses GNU parallel to upload files concurrently
   - Handles retries for failed uploads
   - Generates upload report

2. **File Discovery**: 
   - Searches in common subdirectories (fastq/, uBam/, sequence-files/)
   - Falls back to recursive search if needed
   - Supports both structured and flat file organization

3. **Additional Workflows**:
   - **gdc_direct-upload.sh**: Simplified upload workflow for basic scenarios
   - **gdc_yaml2json.py**: Converts YAML metadata to JSON format required by GDC
   - **gdc_metadata-generate.cwl**: Generates GDC metadata from upload lists (uses TracSeq API)

### External Dependencies
- **gdc-client**: The GDC Data Transfer Tool executable (included in Docker image)
- **GNU parallel**: For concurrent upload management
- **jq**: For JSON parsing
- **Python3 + PyYAML**: For YAML to JSON conversion
- **GDC Token**: Authentication token required for uploads

## Build and Run Commands

### Docker Build
```bash
docker build -f cwl/gdc.Dockerfile -t gdc-uploader:latest .

# Or for Seven Bridges deployment:
docker build -f cwl/gdc.Dockerfile -t cgc-images.sbgenomics.com/david.roberson/gdc-utils:latest .
```

### CWL Testing
```bash
cd tests
./test-cwl.sh
```

### Direct Script Usage
```bash
./cwl/gdc_upload.sh \
  -m metadata.json \
  -t token.txt \
  -j 4 \
  -r 3 \
  /path/to/files
```

### CWL Usage
```bash
cwltool \
  --outdir ./output \
  cwl/gdc_upload.cwl \
  --metadata_file /path/to/gdc-metadata.json \
  --files_directory /path/to/sequence-files \
  --token_file /path/to/gdc-token.txt \
  --thread_count 4 \
  --retry_count 3
```

## Important Guidelines

### Dockerfile Best Practices
- **NEVER** include `CMD` or `ENTRYPOINT` directives in Dockerfiles for this project
- The container will be executed via CWL tool (cwltool) or Seven Bridges platform
- The CWL definitions specify the entry points and commands

### Seven Bridges Platform Integration
- **Working Directory**: Seven Bridges executes from temporary directories
- **Input Files**: All input directories and files are mounted as read-only
- **File Discovery**: The script searches for files in various patterns to accommodate different organization
- **Output Handling**: All outputs are written to the current working directory

## Testing

### Test Directory Management
Tests use task-numbered directories to organize outputs:
- Each test run creates a new `task_XXX` directory under `tests/test-output/`
- Task numbers auto-increment (task_001, task_002, etc.)
- Old test directories are automatically cleaned up (keeps last 10 runs)
- This prevents test output conflicts and maintains history

### Standard Local Testing (using OWLKit)
```bash
./tests/scripts/test-cwl.sh
# Output will be in: tests/test-output/task_XXX/
# Now uses: owlkit cwl run and owlkit cwl validate
```

### Seven Bridges Style Testing (using OWLKit)
```bash
./tests/scripts/test-sb-style.sh
# Output will be in: tests/test-output/task_XXX/
# Now uses: owlkit cwl run with --strict-limits
```

### Test Data
The project includes test data in `tests/test-data/`:
- Sample FASTQ files in `fastq/` subdirectory
- GDC metadata in both JSON and YAML formats
- Test token file (for dry runs)
- Expected output format (upload-report.tsv)

### Running Tests with Docker
```bash
# Build local test image
cd cwl && docker build -f gdc.Dockerfile -t gdc-uploader:test .

# Update CWL to use test image
# Edit cwl/gdc_upload.cwl: dockerPull: "gdc-uploader:test"

# Run tests
cd tests && ./scripts/test-cwl.sh
```

## VS Code Configuration

- Do not auto open files in VS Code

## Development Notes

### Versioning
- Create a versioning system in the CWL doc section (date + increment)
- Update version in CWL files when making changes

### Key Transitions
- The system now uses direct gdc-client calls instead of C# wrapper
- Moved from complex application architecture to simple shell scripts

### Testing Best Practices
- Always run tests using cwltool
- Test both local and Seven Bridges style execution
- Verify file discovery works with different directory structures