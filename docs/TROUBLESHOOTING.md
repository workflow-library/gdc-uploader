# GDC Uploader Troubleshooting Guide

This guide helps you resolve common issues when using the GDC Uploader.

## Common Error Messages

### Authentication Errors

#### "401 Unauthorized"
**Problem**: Invalid or expired GDC token

**Solution**:
1. Get a new token from [GDC Data Portal](https://portal.gdc.cancer.gov/)
2. Ensure token file contains only the token string (no extra whitespace)
3. Check token permissions for your project

```bash
# Verify token format
cat token.txt | wc -c  # Should be exactly token length + 1 (newline)

# Remove any whitespace
echo -n "your-token-here" > token.txt
```

#### "403 Forbidden"
**Problem**: Token lacks permission for the project

**Solution**:
- Verify you have upload permissions for the project
- Check project_id in metadata matches your authorized projects
- Contact GDC support if permissions should be granted

### File Not Found Errors

#### "File not found: sample.fastq.gz"
**Problem**: Uploader cannot locate the file

**Solution**:
1. Check file exists in one of the search directories:
   ```bash
   find /data -name "sample.fastq.gz"
   ```

2. Verify file name matches exactly (case-sensitive):
   ```python
   # In metadata.json
   "file_name": "Sample.fastq.gz"  # Wrong case
   "file_name": "sample.fastq.gz"  # Correct
   ```

3. Use standard directory structure:
   ```
   /data/
   ├── fastq/
   │   └── sample.fastq.gz
   ├── uBam/
   └── sequence-files/
   ```

### Upload Failures

#### "Upload failed after 3 attempts"
**Problem**: Network issues or large file problems

**Solution**:
1. Increase retry count:
   ```bash
   gdc-upload -m metadata.json -t token.txt -r 5 /data/
   ```

2. Check network connectivity:
   ```bash
   curl -I https://api.gdc.cancer.gov/status
   ```

3. For large files, ensure stable connection and sufficient disk space

#### "gdc-client: command not found"
**Problem**: gdc-client not installed or not in PATH

**Solution**:
1. Install gdc-client:
   ```bash
   wget https://gdc.cancer.gov/files/public/file/gdc-client_v1.6.1_Ubuntu_x64.zip
   unzip gdc-client_v1.6.1_Ubuntu_x64.zip
   sudo mv gdc-client /usr/local/bin/
   ```

2. Or use Docker image which includes gdc-client

### Metadata Issues

#### "Invalid JSON in metadata file"
**Problem**: Malformed JSON syntax

**Solution**:
1. Validate JSON syntax:
   ```bash
   python -m json.tool metadata.json
   ```

2. Common JSON errors:
   ```json
   // Wrong - trailing comma
   {
     "id": "uuid",
     "file_name": "file.bam",  // <- Remove this comma
   }
   
   // Wrong - single quotes
   {'id': 'uuid'}  // Use double quotes
   
   // Correct
   {
     "id": "uuid",
     "file_name": "file.bam"
   }
   ```

#### "No UUID found for file"
**Problem**: Metadata doesn't contain entry for the file

**Solution**:
1. Check metadata contains all files:
   ```python
   import json
   with open('metadata.json') as f:
       data = json.load(f)
   for item in data:
       print(item['file_name'])
   ```

2. Ensure file names match exactly

### Performance Issues

#### Slow Upload Speeds
**Problem**: Suboptimal configuration or network

**Solution**:
1. Increase thread count:
   ```bash
   gdc-upload -j 8 -m metadata.json -t token.txt /data/
   ```

2. Check network bandwidth:
   ```bash
   speedtest-cli
   ```

3. Upload during off-peak hours

#### High Memory Usage
**Problem**: Too many concurrent uploads

**Solution**:
1. Reduce thread count:
   ```bash
   gdc-upload -j 2 -m metadata.json -t token.txt /data/
   ```

2. Process files in batches

## Debugging Techniques

### Enable Debug Logging

```python
# In Python script
import logging
logging.basicConfig(level=logging.DEBUG)

from gdc_uploader import GDCUploader
uploader = GDCUploader(metadata_file, token_file)
uploader.run(files_dir)
```

### Check Log Files

```bash
# View upload logs
tail -f gdc-upload-stdout.log
tail -f gdc-upload-stderr.log

# Check individual file logs
ls upload-*.log
```

### Verify File Permissions

```bash
# Check read permissions
ls -la /data/files/

# Check write permissions for logs
touch test.log && rm test.log
```

### Test Single File Upload

```bash
# Test with one file first
gdc-uploader upload-single -m metadata.json -t token.txt sample.fastq.gz
```

## Platform-Specific Issues

### Docker Issues

#### "Permission denied" in container
**Solution**:
```bash
# Run with user permissions
docker run --user $(id -u):$(id -g) -v /data:/data gdc-uploader:latest ...

# Or fix permissions
sudo chown -R $(id -u):$(id -g) /data
```

#### Cannot find files in container
**Solution**:
```bash
# Ensure volumes are mounted correctly
docker run -v /absolute/path/to/files:/data ...
# Not: -v ./files:/data (relative path)
```

### Seven Bridges Platform

#### Files not found on platform
**Solution**:
- Use file objects provided by platform
- Don't assume local file paths
- Files are mounted read-only

### CWL Issues

#### "Invalid CWL"
**Solution**:
```bash
# Validate CWL
cwltool --validate cwl/gdc_upload.cwl

# Use specific CWL version
cwltool --cwl-version v1.2 cwl/gdc_upload.cwl
```

## Recovery Procedures

### Resume Failed Uploads

1. Check upload report:
   ```bash
   cat upload-report.tsv | grep FAILED
   ```

2. Create new metadata for failed files only:
   ```python
   import pandas as pd
   df = pd.read_csv('upload-report.tsv', sep='\t')
   failed = df[df['STATUS'] == 'FAILED']
   # Create new metadata.json with failed files
   ```

3. Retry failed uploads:
   ```bash
   gdc-upload -m failed_metadata.json -t token.txt /data/
   ```

### Cleanup After Errors

```bash
# Remove old log files
rm upload-*.log
rm gdc-upload-*.log

# Clean upload markers (if using shell script version)
rm .upload-active-*
```

## Getting Help

### Collect Diagnostic Information

```bash
# System info
uname -a
python --version
gdc-client --version

# Package version
pip show gdc-uploader

# Recent errors
tail -n 50 gdc-upload-stderr.log
```

### Contact Support

1. **GDC Support**: https://gdc.cancer.gov/support
2. **GitHub Issues**: https://github.com/open-workflow-library/gdc-uploader/issues

When reporting issues, include:
- Error messages
- Log files
- Metadata format (sanitized)
- System information
- Steps to reproduce

## Prevention Tips

1. **Validate Before Upload**:
   ```bash
   gdc-yaml2json --validate metadata.yaml
   ```

2. **Test Small First**:
   - Start with 1-2 files
   - Verify process works
   - Then scale up

3. **Monitor Resources**:
   ```bash
   # During upload
   htop  # CPU and memory
   iotop  # Disk I/O
   iftop  # Network
   ```

4. **Keep Backups**:
   - Save metadata files
   - Keep upload reports
   - Document successful uploads