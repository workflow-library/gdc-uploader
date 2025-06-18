# GDC Uploader

A Python tool for uploading genomic sequence data files (BAM/FASTQ) to the National Cancer Institute's Genomic Data Commons (GDC) using the GDC Data Transfer Tool with parallel execution support.

## Features

- **Parallel Uploads**: Upload multiple files concurrently with configurable thread count
- **File Discovery**: Automatically searches for files in common genomic data directories
- **Progress Tracking**: Real-time upload progress with visual progress bars
- **Retry Logic**: Automatic retry attempts for failed uploads
- **Multiple Upload Modes**: Standard upload, direct upload, and single file upload
- **Format Conversion**: Convert YAML metadata to JSON format
- **CWL Support**: Common Workflow Language definitions for workflow integration

## Installation

### Using pip (recommended)

```bash
pip install gdc-uploader
```

### From source

```bash
git clone https://github.com/open-workflow-library/gdc-uploader.git
cd gdc-uploader
pip install -e .
```

### Using Docker

```bash
docker pull ghcr.io/open-workflow-library/gdc-uploader:latest
```

## Prerequisites

- Python 3.8 or higher
- GDC authentication token (obtain from [GDC Data Portal](https://portal.gdc.cancer.gov/))
- GDC metadata JSON file containing file UUIDs
- `gdc-client` executable (automatically included in Docker image)

## Quick Start

### 1. Prepare your GDC token

Save your GDC authentication token to a file:
```bash
echo "your-gdc-token-here" > token.txt
```

### 2. Prepare metadata

Create a metadata JSON file with your file information:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "sample1.fastq.gz",
    "project_id": "PROJECT-ID"
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "file_name": "sample2.fastq.gz",
    "project_id": "PROJECT-ID"
  }
]
```

### 3. Upload files

```bash
gdc-upload -m metadata.json -t token.txt -j 4 /path/to/files/
```

## Usage

### Command Line Interface

The package provides several commands:

#### Main Upload Command

```bash
gdc-upload [OPTIONS] FILES_DIRECTORY

Options:
  -m, --metadata FILE    Path to GDC metadata JSON file (required)
  -t, --token FILE       Path to GDC authentication token file (required)
  -j, --threads N        Number of parallel upload threads (default: 4)
  -r, --retries N        Number of retry attempts for failed uploads (default: 3)
  -h, --help            Show help message
```

Example:
```bash
gdc-upload -m metadata.json -t token.txt -j 8 /data/sequencing/
```

#### Direct Upload Command

For simplified uploads when file paths are specified in metadata:

```bash
gdc-direct-upload [OPTIONS]

Options:
  -m, --metadata FILE    Path to GDC metadata JSON file (required)
  -t, --token FILE       Path to GDC authentication token file (required)
  -j, --threads N        Number of parallel upload threads (default: 4)
  -r, --retries N        Number of retry attempts for failed uploads (default: 3)
```

#### Single File Upload

Upload a single file:

```bash
gdc-uploader upload-single [OPTIONS] TARGET_FILE

Options:
  -m, --metadata FILE    Path to GDC metadata JSON file (required)
  -t, --token FILE       Path to GDC authentication token file (required)
  -r, --retries N        Number of retry attempts for failed uploads (default: 3)
```

#### YAML to JSON Conversion

Convert YAML metadata to JSON format:

```bash
gdc-yaml2json INPUT_FILE [OUTPUT_FILE]

Options:
  --validate            Validate converted JSON structure
  --compact             Compact JSON output (no indentation)
```

### Python API

You can also use the package programmatically:

```python
from pathlib import Path
from gdc_uploader import GDCUploader

# Initialize uploader
uploader = GDCUploader(
    metadata_file=Path("metadata.json"),
    token_file=Path("token.txt"),
    threads=4,
    retries=3
)

# Run upload
uploader.run(files_dir=Path("/data/sequencing/"))
```

## File Discovery

The uploader searches for files in the following locations (in order):

1. `FILES_DIRECTORY/fastq/`
2. `FILES_DIRECTORY/uBam/`
3. `FILES_DIRECTORY/sequence-files/`
4. `FILES_DIRECTORY/` (recursive search)

This accommodates different file organization patterns commonly used in genomic data storage.

## Output Files

The uploader generates several output files:

- `upload-report.tsv` - Summary of all upload attempts with status
- `upload-{uuid}.log` - Individual upload logs for each file
- `gdc-upload-stdout.log` - Standard output log
- `gdc-upload-stderr.log` - Error output log

## Docker Usage

### Building the Docker image

```bash
docker build -t gdc-uploader:latest .
```

### Running with Docker

```bash
docker run -v /path/to/files:/data \
           -v /path/to/metadata.json:/metadata/metadata.json \
           -v /path/to/token.txt:/metadata/token.txt \
           gdc-uploader:latest \
           gdc-upload -m /metadata/metadata.json -t /metadata/token.txt /data
```

## CWL Integration

The package includes CWL (Common Workflow Language) definitions for workflow integration:

- `cwl/gdc_upload.cwl` - Main upload workflow
- `cwl/gdc_direct-upload.cwl` - Direct upload workflow
- `cwl/gdc_yaml2json.cwl` - YAML to JSON converter

Example CWL usage:

```bash
cwltool --outdir ./output \
        cwl/gdc_upload.cwl \
        --metadata_file metadata.json \
        --files_directory /path/to/files \
        --token_file token.txt \
        --thread_count 4
```

## Troubleshooting

### Common Issues

1. **Authentication Error**: Ensure your GDC token is valid and not expired
2. **File Not Found**: Check that file names in metadata match actual file names
3. **Network Issues**: The tool will automatically retry failed uploads
4. **Permission Denied**: Ensure you have read access to files and write access for logs

### Debug Mode

Enable detailed logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- National Cancer Institute's Genomic Data Commons
- GDC Data Transfer Tool developers
- Open Workflow Library community

## Support

For issues and questions:
- GitHub Issues: [https://github.com/open-workflow-library/gdc-uploader/issues](https://github.com/open-workflow-library/gdc-uploader/issues)
- GDC Support: [https://gdc.cancer.gov/support](https://gdc.cancer.gov/support)