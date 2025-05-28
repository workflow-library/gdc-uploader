# Test Data for GDC Uploader

This directory contains test data for running the GDC uploader on Seven Bridges or locally.

## Files

### Sequence Files
Located in `sequence-files/`:
- `test_sample_001_R1.fastq.gz` - Mock FASTQ file (248 bytes)
- `test_sample_002_R2.fastq.gz` - Mock FASTQ file (248 bytes)
- `test_sample_003_R1.fastq.gz` - Mock FASTQ file (372 bytes)

Note: These are not real gzipped files, just mock FASTQ data for testing.

### Metadata
- `gdc-metadata.json` - GDC metadata describing the sequence files

### Authentication
- `gdc-token.txt` - Dummy token for testing (not a real GDC token)

## Usage on Seven Bridges

1. Upload this entire `test-data` directory to your Seven Bridges project
2. Run the CWL workflow with these files as inputs
3. Use `--simulator true` to test without real uploads

## File Naming

The test files use a simplified naming convention (e.g., `test_sample_001_R1.fastq.gz`) that should work with the uploader. If you encounter filename parsing errors, the files may need to be renamed to match the TracSeq format with 4+ underscores.