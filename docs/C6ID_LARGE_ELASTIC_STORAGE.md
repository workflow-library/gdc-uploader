# c6id.large + Elastic Storage Analysis

## The Combination

**c6id.large** provides:
- 2 vCPUs (sufficient for upload)
- 4 GB RAM (sufficient)
- 118 GB local NVMe (for temp files/cache)
- $0.035/hr spot pricing

**Elastic Storage** provides:
- Access to the 228GB BAM file
- Pay only for what you use
- Potential S3 passthrough

## Cost Scenarios

### Scenario 1: Elastic Storage with S3 Passthrough (Best Case)
If Elastic Storage doesn't copy the file:
- c6id.large spot: $0.035/hr × 20h = **$0.70**
- Elastic Storage: ~$0 (just metadata)
- **Total: $0.70 per BAM (90% savings!)**

### Scenario 2: Elastic Storage with Smart Caching
If Elastic Storage caches chunks during upload:
- c6id.large spot: $0.035/hr × 20h = $0.70
- Elastic Storage: ~$0.20 (transient cache)
- **Total: $0.90 per BAM (87% savings)**

### Scenario 3: Elastic Storage with Full Copy
If Elastic Storage copies the entire file:
- c6id.large spot: $0.035/hr × 20h = $0.70
- Elastic Storage: ~$2.00 (228GB for 20h)
- **Total: $2.70 per BAM (61% savings)**

## Configuration

```yaml
hints:
  # Use spot instance
  - class: 'sbg:SpotInstance'
    value: true
  
  # Small instance
  - class: 'sbg:AWSInstanceType'
    value: 'c6id.large'
  
  # Enable Elastic Storage for BAM access
  - class: 'sbg:useElasticStorage'
    value: true
  
  # Local NVMe for temp files only
  - class: 'sbg:DiskRequirement'
    value: 10  # Minimal EBS, use local NVMe
```

## Optimization Strategy

### Use Local NVMe for Performance

```bash
#!/bin/bash
# Optimized upload script for c6id.large + Elastic

# Use local NVMe for temp files
export TMPDIR=/mnt/nvme
export CURL_PROGRESS_DIR=/mnt/nvme

# BAM file is on Elastic Storage
BAM_PATH="$1"  # e.g., /elastic/sample.bam

# Create progress tracking on fast local storage
PROGRESS_FILE="/mnt/nvme/curl-progress-$$.txt"

# Upload from Elastic Storage
curl --upload-file "$BAM_PATH" \
     --output "/mnt/nvme/upload.log" \
     ... \
     2>"$PROGRESS_FILE"
```

### Potential Bandwidth Optimization

If Elastic Storage has better S3 connectivity than instance:
- Data flow: S3 → Elastic Storage → Instance → GDC
- Might actually be faster than direct instance access

## Comparison Matrix

| Setup | Instance $/BAM | Storage $/BAM | Total $/BAM | Savings |
|-------|----------------|----------------|-------------|---------|
| Current (c5.xlarge + 1TB EBS) | $3.82 | $3.20 | $7.02 | - |
| c6id.xlarge spot (local) | $1.40 | $0 | $1.40 | 80% |
| c6id.large spot + 250GB EBS | $0.70 | $1.60 | $2.30 | 67% |
| **c6id.large spot + Elastic (best)** | $0.70 | ~$0 | **$0.70** | **90%** |
| **c6id.large spot + Elastic (worst)** | $0.70 | $2.00 | $2.70 | 61% |

## Key Questions for Seven Bridges

1. **Does Elastic Storage support streaming** from S3 without full copy?
2. **Can curl read directly** from Elastic Storage paths?
3. **What's the actual cost model** for Elastic Storage?

## Test Script

```bash
#!/bin/bash
# Test elastic storage behavior with c6id.large

echo "Testing Elastic Storage on c6id.large..."

# Check local storage
echo "=== Local NVMe Storage ==="
df -h /mnt/nvme
echo

# Check elastic storage mount
echo "=== Elastic Storage Mount ==="
mount | grep elastic
df -h /elastic
echo

# Test streaming capability
echo "=== Streaming Test ==="
BAM_FILE="/elastic/test.bam"

# Read 1GB without filling local disk
dd if="$BAM_FILE" bs=1M count=1024 | md5sum &
DD_PID=$!

# Monitor local disk usage
while kill -0 $DD_PID 2>/dev/null; do
    df -h /mnt/nvme | grep nvme
    sleep 1
done

echo "If disk usage didn't increase by 1GB, streaming works!"
```

## Recommendations

1. **Try c6id.large + Elastic Storage first**
   - Potential for 90% savings ($0.70/BAM)
   - Minimal risk - just run one test

2. **Monitor actual Elastic Storage costs**
   - Check Seven Bridges billing after test
   - Compare scenarios

3. **Fallback options**:
   - If Elastic copies fully: Use c6id.xlarge spot ($1.40)
   - If Elastic streams: Use c6id.large spot ($0.70)

## Decision Tree

```
Is Elastic Storage streaming from S3?
├─ Yes → Use c6id.large + Elastic ($0.70/BAM) ✅
├─ Partial (caching) → Still use c6id.large + Elastic ($0.90/BAM) ✅
└─ No (full copy) → Depends on Elastic cost
    ├─ Elastic < $0.70 → Use c6id.large + Elastic
    └─ Elastic > $0.70 → Use c6id.xlarge local ($1.40/BAM)
```

**Bottom line**: c6id.large + Elastic Storage could be your cheapest option at $0.70-0.90 per BAM, but you need to test how Elastic Storage actually behaves!