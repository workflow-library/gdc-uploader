# CWL Command Reference

This document shows how to run the GDC Uploader using cwltool with command-line arguments.

## GDC Uploader Commands

### 1. Upload files with simulator (test mode)
```bash
cwltool \
  --outdir ./output \
  ../cwl/gdc-uploader.cwl \
  --metadata_file /path/to/gdc-metadata.json \
  --files_directory /path/to/sequence-files \
  --token_file /path/to/gdc-token.txt \
  --thread_count 4 \
  --retry_count 3 \
  --simulator true \
  --multipart "yes"
```

### 2. Check files only (dry run)
```bash
cwltool \
  --outdir ./output \
  ../cwl/gdc-uploader.cwl \
  --metadata_file /path/to/gdc-metadata.json \
  --files_directory /path/to/sequence-files \
  --files_only true \
  --simulator true
```

### 3. Production upload (no simulator)
```bash
cwltool \
  --outdir ./output \
  ../cwl/gdc-uploader.cwl \
  --metadata_file /path/to/gdc-metadata.json \
  --files_directory /path/to/sequence-files \
  --token_file /path/to/gdc-token.txt \
  --thread_count 8 \
  --retry_count 3 \
  --multipart "yes"
```

### 4. Generate metadata
```bash
cwltool \
  --outdir ./output \
  ../cwl/metadata-generator.cwl \
  --upload_list /path/to/upload-list.txt \
  --experiment_type rnaseq \
  --use_dev_server false
```

## Important Notes

- All file paths must be absolute paths when using cwltool
- With `--sim` flag: Does NOT check if files exist, just simulates uploads
- With `--filesonly` flag: DOES check if files exist, but doesn't upload
- Without either flag: Checks files AND attempts real upload to GDC