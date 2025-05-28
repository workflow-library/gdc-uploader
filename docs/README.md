# GDC Uploader Examples

This directory contains example configuration files for running the GDC uploader with CWL.

## Files

### Job Configuration Files

- **gdc-upload-job.yml** / **gdc-upload-job.json** - Example job configurations for uploading files to GDC
- **metadata-generator-job.yml** / **metadata-generator-job.json** - Example job configurations for generating GDC metadata

### Sample Data Files

- **sample-gdc-metadata.json** - Example GDC metadata file format
- **sample-upload-list.txt** - Example upload list for metadata generation

## Usage

### Running with YAML configuration

```bash
# Upload files
cwltool --outdir ./output ../cwl/gdc-uploader.cwl gdc-upload-job.yml

# Generate metadata
cwltool --outdir ./output ../cwl/metadata-generator.cwl metadata-generator-job.yml
```

### Running with JSON configuration

```bash
# Upload files
cwltool --outdir ./output ../cwl/gdc-uploader.cwl gdc-upload-job.json

# Generate metadata
cwltool --outdir ./output ../cwl/metadata-generator.cwl metadata-generator-job.json
```

## Key Features

### Testing and Validation
- **File Check Mode** (`--files_only`): Verify all files exist without uploading
- **Simulator Mode** (`--simulator`): Test upload logic without actual transfers
- **Built-in Test Data**: Complete test dataset included for immediate testing

### Robust Upload Management
- **Multi-threaded uploads**: Configurable thread count for parallel transfers
- **Retry logic**: Automatic retry of failed uploads with configurable retry count
- **Progress tracking**: Real-time progress reporting and logging
- **Resume capability**: Can resume interrupted uploads

### File Format Support
- **FASTQ files**: Stored in `fastq/` subdirectory
- **BAM files**: Stored in `uBam/run_id/` structure
- **TracSeq naming convention**: Automatic parsing of TracSeq format filenames
- **Generic filename support**: Handles non-TracSeq format files gracefully

## Docker Usage

```bash
# Build the Docker image
docker build -t cgc-images.sbgenomics.com/david.roberson/gdc-utils:latest .

# Run file check
docker run --rm -v /local/data:/data cgc-images.sbgenomics.com/david.roberson/gdc-utils:latest \
  /app/upload2gdc --md /data/metadata.json --files /data --filesonly

# Run with simulator
docker run --rm -v /local/data:/data cgc-images.sbgenomics.com/david.roberson/gdc-utils:latest \
  /app/upload2gdc --ur /data/upload-report.tsv --md /data/metadata.json \
  --files /data --token /data/token.txt --sim
```

## Important Notes

- **Upload Report Required**: Most modes require a TSV upload report from GDC except `--filesonly` mode
- **File Organization**: Files must be organized in expected directory structure (fastq/, uBam/)
- **Token Security**: Never commit GDC tokens to version control
- **Test First**: Always test with `--filesonly` or `--simulator` before production uploads

For detailed command reference and workflow diagrams, see **usage-diagram.md**.