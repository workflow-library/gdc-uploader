# Migration Notes

## Current Status

The GDC Uploader has been refactored from shell scripts to a Python package, but both implementations are available for compatibility.

### Active Implementations

1. **Shell Scripts** (Currently used by CWL):
   - `gdc_upload.sh` - Main upload with file discovery
   - `gdc_direct-upload.sh` - Direct upload
   - `gdc_upload_single.sh` - Single file upload (used for large BAM files)

2. **Python Package** (New implementation):
   - `gdc-uploader upload` - Main upload with progress bars
   - `gdc-uploader direct-upload` - Direct upload
   - `gdc-uploader upload-single` - Single file upload

### Why Both Exist

- The shell scripts are battle-tested and working in production
- The Python implementation provides better error handling and progress tracking
- CWL pipelines currently use the shell scripts
- Gradual migration allows testing without breaking existing workflows

### Upload Progress Monitoring

The shell script (`gdc_upload_single.sh`) provides detailed progress monitoring for large files:

```
Files being created:
  - curl-progress-{uuid}.txt (curl progress output)
  - .upload-active-{uuid} (upload active marker)
  - progress-monitor-{uuid}.log (debug log)
  - upload-{uuid}.log (curl response)
```

Progress updates are shown every 30 seconds or when progress changes by 5%.

### Switching Implementations

To use the Python implementation in CWL:

1. Set environment variable:
   ```bash
   export USE_PYTHON_IMPLEMENTATION=true
   ```

2. Or update the CWL baseCommand:
   ```yaml
   baseCommand: ["gdc-uploader", "upload-single"]
   ```

### Feature Comparison

| Feature | Shell Script | Python Package |
|---------|--------------|----------------|
| Progress monitoring | Text updates | Visual progress bars |
| Error handling | Exit codes | Exceptions with context |
| Parallel uploads | GNU parallel | ThreadPoolExecutor |
| File discovery | bash find | Python Path.rglob |
| API integration | curl | requests library |
| Logging | Multiple log files | Unified logging |

### Recommended Usage

- **For CWL/Seven Bridges**: Continue using shell scripts (current default)
- **For local development**: Use Python package for better experience
- **For new integrations**: Use Python package API

### Future Plans

1. Validate Python implementation with production workloads
2. Add feature parity for all progress monitoring
3. Gradually migrate CWL definitions
4. Deprecate shell scripts after thorough testing

### Testing Both Implementations

```bash
# Shell script version
./cwl/gdc_upload_single.sh -m metadata.json -t token.txt file.bam

# Python version  
gdc-uploader upload-single -m metadata.json -t token.txt file.bam

# Compare outputs
diff upload-report.tsv upload-report-python.tsv
```