# Seven Bridges Elastic Storage Optimization

## What is Elastic Storage?

Seven Bridges' Elastic Storage is a shared storage system (likely EFS or similar) that:
- Charges only for data stored, not provisioned capacity
- Can be shared across multiple tasks
- Eliminates the need to provision per-task EBS volumes

## Cost Comparison

### Current Setup (EBS)
- **1TB gp3 EBS**: $0.08/hr × 40 hours = $3.20
- **Actual usage**: 228GB for ~22.5 hours
- **Waste**: Paying for 772GB unused space

### With Elastic Storage
Assuming similar pricing to AWS EFS (~$0.30/GB/month):
- **228GB for 22.5 hours**: 228GB × (22.5/730) months × $0.30 = **$2.11**
- **Actual savings**: $1.09 per BAM (34% of storage cost)

But the real benefit is when NOT copying files...

## The Real Game Changer: No File Staging?

If Elastic Storage allows direct access to S3 objects without copying:

### Scenario 1: Elastic Storage with S3 Gateway (Best Case)
```yaml
hints:
  - class: 'sbg:useElasticStorage'
    value: true
  
  # Minimal local disk needed
  - class: 'sbg:DiskRequirement'
    value: 10  # Just for logs
```

**Cost Breakdown**:
- c6i.xlarge: $0.17/hr × 22.5h = $3.82
- Elastic Storage: ~$0 (if S3 gateway)
- **Total: $3.82 (46% savings)**

### Scenario 2: Elastic Storage with Smart Caching
If Elastic Storage caches only active chunks being uploaded:
- Only ~1-2GB in cache at any time
- Cost: negligible
- **Total: ~$3.85 (45% savings)**

## Implementation Strategies

### Strategy 1: Verify S3 Passthrough
Test if Elastic Storage provides direct S3 access:

```bash
#!/bin/bash
# Test script to check if file is actually copied

echo "Checking file access method..."

# Get file info
FILE_PATH="$1"
echo "File path: $FILE_PATH"

# Check if it's a symlink
if [ -L "$FILE_PATH" ]; then
    echo "File is a symbolic link to: $(readlink -f "$FILE_PATH")"
fi

# Check filesystem type
df -T "$FILE_PATH" | tail -1

# Check if it's a FUSE mount
mount | grep -i fuse

# Try to read without full download
echo "Testing partial read..."
time dd if="$FILE_PATH" of=/dev/null bs=1M count=1

# Monitor I/O during upload
iostat -x 1 10 &
IOSTAT_PID=$!

# Start upload
echo "Starting upload..."
# ... upload command ...

kill $IOSTAT_PID
```

### Strategy 2: Optimize for Elastic Storage

If Elastic Storage requires copying but charges by actual use:

```yaml
# CWL Configuration
hints:
  - class: 'sbg:useElasticStorage'
    value: true
  
  - class: 'sbg:AWSInstanceType'
    value: 'c6i.2xlarge'  # More vCPUs for faster processing
  
  - class: 'sbg:ElasticStorageSettings'
    value:
      mountPath: '/elastic'
      cacheMode: 'minimal'  # If available
```

### Strategy 3: Stream Through Elastic Storage

Create a modified upload script that leverages Elastic Storage:

```bash
#!/bin/bash
# Elastic Storage optimized upload

# Use named pipes on Elastic Storage to avoid full copy
PIPE_PATH="/elastic/upload-pipe-$$"
mkfifo "$PIPE_PATH"

# Stream from S3 through pipe
aws s3 cp "s3://bucket/file.bam" "$PIPE_PATH" &
S3_PID=$!

# Upload from pipe
curl --upload-file "$PIPE_PATH" ... &
CURL_PID=$!

# Wait for completion
wait $S3_PID $CURL_PID

# Cleanup
rm -f "$PIPE_PATH"
```

## Recommended Test Plan

### 1. Test Elastic Storage Behavior
```yaml
class: CommandLineTool
baseCommand: [bash, -c]
arguments:
  - |
    echo "Testing Elastic Storage..."
    # Check mount type
    mount | grep elastic
    # Check file operations
    time dd if=$(inputs.test_file.path) of=/dev/null bs=1M count=100
    # Check if full file is copied
    df -h
    
inputs:
  test_file:
    type: File
    
hints:
  - class: 'sbg:useElasticStorage'
    value: true
```

### 2. Compare Costs
Run identical uploads with:
- Current: EBS storage
- Test 1: Elastic Storage
- Test 2: Elastic Storage + c6id.xlarge

## Expected Outcomes

### Best Case (S3 Passthrough)
| Method | Instance $ | Storage $ | Total | Savings |
|--------|------------|-----------|-------|---------|
| Current | $3.82 | $3.20 | $7.02 | - |
| Elastic + c6i.xlarge | $3.82 | ~$0 | $3.82 | 46% |

### Likely Case (Smart Caching)
| Method | Instance $ | Storage $ | Total | Savings |
|--------|------------|-----------|-------|---------|
| Current | $3.82 | $3.20 | $7.02 | - |
| Elastic + c6i.xlarge | $3.82 | $0.50 | $4.32 | 38% |

### Worst Case (Full Copy but Pay-per-Use)
| Method | Instance $ | Storage $ | Total | Savings |
|--------|------------|-----------|-------|---------|
| Current | $3.82 | $3.20 | $7.02 | - |
| Elastic + c6i.xlarge | $3.82 | $2.11 | $5.93 | 16% |

## Action Items

1. **Contact Seven Bridges Support**:
   - How does Elastic Storage handle S3 files?
   - Is streaming/passthrough supported?
   - What's the actual pricing model?

2. **Run Test Upload**:
   - Enable Elastic Storage
   - Monitor actual disk usage
   - Compare costs

3. **Optimize Based on Results**:
   - If passthrough: Use minimal instances
   - If cached: Use c6id for speed
   - If full copy: At least save on overprovisioning

The Elastic Storage option could reduce your costs by 16-46% depending on implementation!