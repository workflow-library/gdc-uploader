# Spot Instance Upload Guide

This guide explains how to use the GDC Uploader on AWS/cloud spot instances that may be interrupted.

## Overview

The `spot-upload` command is specifically designed for uploading large files on spot instances:

- **Automatic Resume**: Uses `gdc-client --resume` to continue interrupted uploads
- **State Persistence**: Saves upload state to disk for recovery
- **Signal Handling**: Gracefully handles SIGTERM from spot termination
- **Single File Focus**: Uploads one file at a time for better control
- **Manifest Filtering**: Automatically extracts metadata for the target file

## Key Features

1. **GDC-Client Resume**: Unlike the curl-based approach, this uses gdc-client which properly supports chunked uploads with resume
2. **State File**: Tracks upload progress and can resume even after complete instance termination
3. **Spot Termination Detection**: Checks AWS metadata for termination notices
4. **Automatic Retries**: Configurable retry attempts with exponential backoff

## Usage

### Command Line

```bash
# Basic usage
gdc-uploader spot-upload manifest.yaml token.txt /path/to/file.bam

# With custom state file
gdc-uploader spot-upload manifest.yaml token.txt /path/to/file.bam \
  --state-file /persistent/upload_state.json

# With more retries
gdc-uploader spot-upload manifest.yaml token.txt /path/to/file.bam \
  --retries 5
```

### Python API

```python
from gdc_uploader.spot_upload import upload_with_resume

upload_with_resume(
    manifest_file="manifest.yaml",
    token_file="token.txt",
    target_file="/data/sample.bam",
    state_file="/persistent/upload_state.json"
)
```

### CWL Usage

```bash
cwltool cwl/gdc_spot_upload.cwl \
  --manifest_file manifest.yaml \
  --token_file token.txt \
  --target_file /data/sample.bam
```

## Manifest Format

The manifest can be YAML or JSON and should contain all files. The tool will filter for your specific file:

```yaml
# manifest.yaml
- id: 550e8400-e29b-41d4-a716-446655440000
  file_name: sample1.bam
  project_id: TCGA-LUAD

- id: 550e8400-e29b-41d4-a716-446655440001
  file_name: sample2.bam  # <- This will be selected if uploading sample2.bam
  project_id: TCGA-LUAD
```

## How Resume Works

1. **Initial Upload**:
   - gdc-client splits file into 1GB chunks
   - Uploads chunks in parallel (8 threads)
   - Tracks completed chunks

2. **On Interruption**:
   - Signal handler saves current state
   - gdc-client saves its own progress

3. **On Resume**:
   - Reads state file
   - gdc-client checks which chunks are complete
   - Resumes from incomplete chunks only

## Best Practices for Spot Instances

### 1. Use Persistent Storage for State

```bash
# Mount EBS volume
sudo mkdir -p /persistent
sudo mount /dev/xvdf /persistent

# Use for state file
gdc-uploader spot-upload manifest.yaml token.txt file.bam \
  --state-file /persistent/upload_state.json
```

### 2. Set Up Auto-Resume Script

Create a startup script that checks for interrupted uploads:

```bash
#!/bin/bash
# /etc/rc.local or user-data script

STATE_FILE="/persistent/upload_state.json"

if [ -f "$STATE_FILE" ]; then
    echo "Found previous upload state, resuming..."
    
    # Extract file paths from state
    MANIFEST=$(jq -r '.manifest_file // empty' "$STATE_FILE")
    TOKEN=$(jq -r '.token_file // empty' "$STATE_FILE")
    TARGET=$(jq -r '.file // empty' "$STATE_FILE")
    
    if [ -n "$MANIFEST" ] && [ -n "$TOKEN" ] && [ -n "$TARGET" ]; then
        gdc-uploader spot-upload "$MANIFEST" "$TOKEN" "$TARGET" \
          --state-file "$STATE_FILE"
    fi
fi
```

### 3. Monitor Spot Termination

The uploader checks for AWS spot termination notices:

```bash
# Manual check
curl -s http://169.254.169.254/latest/meta-data/spot/instance-action
```

### 4. Use Spot Fleet with Persistence

```yaml
# spot-fleet-config.yaml
SpotFleetRequestConfig:
  AllocationStrategy: lowestPrice
  IamFleetRole: arn:aws:iam::123456789012:role/fleet-role
  LaunchSpecifications:
    - ImageId: ami-12345678
      InstanceType: m5.large
      BlockDeviceMappings:
        - DeviceName: /dev/sdf
          Ebs:
            VolumeSize: 100
            VolumeType: gp3
            DeleteOnTermination: false  # Persist for resume
      UserData: |
        #!/bin/bash
        # Mount persistent volume and check for resume
        ...
```

## Handling Different Scenarios

### Scenario 1: Clean Interruption (SIGTERM)

```
[2025-01-17 10:30:45] INFO: Starting upload: sample.bam (UUID: 550e8400...)
[2025-01-17 10:45:23] WARNING: Received signal 15. Saving state and exiting...
[2025-01-17 10:45:23] INFO: State saved to upload_state.json

# On next run:
[2025-01-17 11:00:01] INFO: Resuming previous upload: {'status': 'interrupted'...}
[2025-01-17 11:00:02] INFO: Upload resumed from chunk 45/228
```

### Scenario 2: Spot Price Termination

The tool detects AWS termination notice and saves state before shutdown.

### Scenario 3: Network Failure

gdc-client handles transient failures. The wrapper adds additional retry logic.

## Comparison with Other Methods

| Feature | spot-upload | gdc_upload_single.sh | gdc-upload |
|---------|-------------|---------------------|------------|
| Resume Support | ✅ Full | ❌ Limited | ✅ Full |
| Spot Awareness | ✅ Yes | ❌ No | ❌ No |
| State Persistence | ✅ Yes | ❌ No | ❌ No |
| Single File | ✅ Yes | ✅ Yes | ❌ Batch |
| Method | gdc-client | curl/API | gdc-client |

## Troubleshooting

### Upload Not Resuming

1. Check state file exists and is readable:
   ```bash
   cat upload_state.json
   ```

2. Verify gdc-client can see previous chunks:
   ```bash
   ls -la ~/.gdc/
   ```

### Slow Upload Speed

Adjust gdc-client parameters:
```python
# In spot_upload.py, modify:
"-n", "16",  # Increase parallel threads
"--upload-part-size", "2147483648",  # 2GB chunks
```

### State File Corruption

Delete and restart:
```bash
rm upload_state.json
gdc-uploader spot-upload manifest.yaml token.txt file.bam
```

## Example: Complete Spot Instance Setup

```bash
#!/bin/bash
# EC2 user-data script for spot instance

# Install dependencies
apt-get update
apt-get install -y python3-pip jq

# Install gdc-uploader
pip3 install gdc-uploader

# Mount persistent EBS
mkdir -p /persistent
mount /dev/xvdf /persistent

# Check for previous upload
STATE_FILE="/persistent/upload_state.json"
if [ -f "$STATE_FILE" ]; then
    status=$(jq -r '.status' "$STATE_FILE")
    if [ "$status" != "completed" ]; then
        # Resume upload
        gdc-uploader spot-upload \
            /persistent/manifest.yaml \
            /persistent/token.txt \
            /data/large_file.bam \
            --state-file "$STATE_FILE"
    fi
else
    # Start new upload
    gdc-uploader spot-upload \
        /persistent/manifest.yaml \
        /persistent/token.txt \
        /data/large_file.bam \
        --state-file "$STATE_FILE"
fi
```

This approach ensures your large file uploads complete successfully even with spot instance interruptions!