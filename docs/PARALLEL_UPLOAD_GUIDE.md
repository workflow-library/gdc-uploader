# Parallel Upload Cost Optimization Guide

This guide explains how to reduce upload costs by running multiple uploads concurrently on a single larger instance.

## Cost Analysis

### Current Setup (c5.xlarge)
- **Instance**: c5.xlarge (4 vCPUs, 8 GB RAM)
- **Cost**: $0.17/hour
- **Concurrent uploads**: 2 (using ~30% CPU each = ~2 vCPUs)
- **Time per BAM**: ~41 hours
- **Cost per BAM**: ~$7.00

### Optimized Setup (m5a.8xlarge)
- **Instance**: m5a.8xlarge (32 vCPUs, 128 GB RAM)
- **Cost**: $1.376/hour
- **Concurrent uploads**: 16
- **Time for 16 BAMs**: ~41 hours
- **Cost per BAM**: ~$3.53 (50% savings)

## Instance Recommendations

| Instance Type | vCPUs | RAM | $/hour | Max Uploads | $/BAM | Savings |
|--------------|-------|-----|--------|-------------|-------|---------|
| c5.xlarge | 4 | 8 | $0.17 | 2 | $7.00 | - |
| m5.4xlarge | 16 | 64 | $0.768 | 8 | $3.93 | 44% |
| **m5a.8xlarge** | 32 | 128 | $1.376 | 16 | $3.53 | **50%** |
| m5.12xlarge | 48 | 192 | $2.304 | 24 | $3.93 | 44% |
| m6i.8xlarge | 32 | 128 | $1.536 | 16 | $3.94 | 44% |

**Recommendation**: m5a.8xlarge offers the best cost/performance ratio

## Usage

### Basic Command

```bash
# Upload 3 BAM files in parallel
gdc-uploader parallel-upload manifest.yaml token.txt \
  sample1.bam sample2.bam sample3.bam \
  --max-workers 3
```

### Optimal Usage on m5a.8xlarge

```bash
# Upload 16 BAM files in parallel
gdc-uploader parallel-upload manifest.yaml token.txt \
  *.bam \
  --max-workers 16
```

### Python Script for Batch Processing

```python
#!/usr/bin/env python3
import subprocess
from pathlib import Path

# Configuration
MANIFEST = "manifest.yaml"
TOKEN = "token.txt"
MAX_WORKERS = 16  # For m5a.8xlarge
BAM_DIR = Path("/data/bams")

# Get all BAM files
bam_files = list(BAM_DIR.glob("*.bam"))

# Process in batches
batch_size = MAX_WORKERS
for i in range(0, len(bam_files), batch_size):
    batch = bam_files[i:i+batch_size]
    
    print(f"Processing batch {i//batch_size + 1}: {len(batch)} files")
    
    cmd = [
        "gdc-uploader", "parallel-upload",
        MANIFEST, TOKEN
    ] + [str(f) for f in batch] + [
        "--max-workers", str(min(len(batch), MAX_WORKERS))
    ]
    
    subprocess.run(cmd)
```

## Network Considerations

### Bandwidth Requirements
- Each upload uses ~50-70 Mbps
- 16 concurrent uploads need ~800-1120 Mbps
- Most AWS instances have sufficient bandwidth

### GDC Rate Limiting
- GDC may have per-IP rate limits
- Monitor for 429 (Too Many Requests) errors
- If throttled, reduce max-workers

### Testing Throttling

```bash
# Start with 2 uploads
gdc-uploader parallel-upload manifest.yaml token.txt file1.bam file2.bam --max-workers 2

# If successful, gradually increase
gdc-uploader parallel-upload manifest.yaml token.txt *.bam --max-workers 4
gdc-uploader parallel-upload manifest.yaml token.txt *.bam --max-workers 8
gdc-uploader parallel-upload manifest.yaml token.txt *.bam --max-workers 16
```

## Monitoring

### Real-time Progress
The tool shows progress for each file:
```
[2025-01-17 14:32:05] [Thread-1] INFO: file1.bam: 45% (103.0/228.3 GB) Speed: 65.2 MB/s ETA: 32m 15s
[2025-01-17 14:32:05] [Thread-2] INFO: file2.bam: 23% (52.5/228.3 GB) Speed: 58.1 MB/s ETA: 50m 30s
[2025-01-17 14:32:05] [Thread-3] INFO: file3.bam: 67% (152.9/228.3 GB) Speed: 71.0 MB/s ETA: 17m 45s
```

### System Monitoring

```bash
# CPU usage
htop

# Network usage
iftop -i eth0

# Disk I/O
iotop

# Upload logs
tail -f parallel-api-upload.log
```

### Cost Tracking

The tool generates a report with cost estimates:
```
filename        success duration_hours  cost_estimate
sample1.bam     True    41.2           $7.00
sample2.bam     True    40.8           $6.94
sample3.bam     True    41.5           $7.06
```

## Best Practices

### 1. Instance Setup

```bash
# Launch m5a.8xlarge with sufficient storage
aws ec2 run-instances \
  --instance-type m5a.8xlarge \
  --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=100,VolumeType=gp3}" \
  --iam-instance-profile Name=S3ReadRole
```

### 2. Data Transfer

```bash
# Download BAMs from S3 in parallel
aws s3 sync s3://my-bucket/bams/ /data/bams/ \
  --exclude "*" --include "*.bam" \
  --concurrent 16
```

### 3. Optimal Scheduling

```python
# Group files by size for balanced processing
import os
from pathlib import Path

bam_files = list(Path("/data/bams").glob("*.bam"))
# Sort by size
bam_files.sort(key=lambda x: x.stat().st_size, reverse=True)

# Distribute large and small files evenly
batch1 = bam_files[::2]    # Even indices
batch2 = bam_files[1::2]   # Odd indices
```

### 4. Failure Handling

```bash
# Check report for failures
grep False parallel-upload-report.tsv

# Retry failed uploads
gdc-uploader parallel-upload manifest.yaml token.txt \
  failed1.bam failed2.bam \
  --max-workers 2
```

## Example: Full Workflow

```bash
#!/bin/bash
# upload-workflow.sh

# Configuration
INSTANCE_TYPE="m5a.8xlarge"
MAX_WORKERS=16
MANIFEST="manifest.yaml"
TOKEN="token.txt"

# Step 1: Prepare file list
find /data -name "*.bam" > bam_files.txt

# Step 2: Split into batches
split -l $MAX_WORKERS bam_files.txt batch_

# Step 3: Process each batch
for batch in batch_*; do
    echo "Processing $batch"
    
    # Read files from batch
    mapfile -t files < "$batch"
    
    # Upload batch
    gdc-uploader parallel-upload "$MANIFEST" "$TOKEN" \
        "${files[@]}" \
        --max-workers $MAX_WORKERS
    
    # Check success
    if [ $? -eq 0 ]; then
        echo "Batch $batch completed successfully"
    else
        echo "Batch $batch had failures - check logs"
    fi
    
    # Optional: Clean up uploaded files to save space
    # for f in "${files[@]}"; do
    #     rm -f "$f"
    # done
done

# Step 4: Generate summary
echo "Upload Summary:"
cat parallel-upload-report.tsv | awk -F'\t' '
    NR>1 {
        total++
        if ($2 == "True") success++
        total_cost += $4
    }
    END {
        print "Total files:", total
        print "Successful:", success
        print "Failed:", total - success
        print "Total cost: $" total_cost
        print "Average cost per file: $" total_cost/total
    }
'
```

## Troubleshooting

### High Memory Usage
```bash
# Reduce concurrent uploads
--max-workers 8
```

### Network Errors
```bash
# Add retry logic in script
for i in {1..3}; do
    gdc-uploader parallel-upload ... && break
    echo "Retry $i..."
    sleep 300
done
```

### Uneven Progress
- Large files may dominate bandwidth
- Consider grouping files by size
- Run large files separately with fewer workers

This parallel approach can reduce your per-BAM upload cost by 50% while maintaining reliability!