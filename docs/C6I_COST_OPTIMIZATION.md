# C6i Instance Cost Optimization for Seven Bridges

## C6i Series Advantages

The c6i instances are Intel's latest generation with better network performance than c5:
- **c6i**: Up to 12.5 Gbps network (xlarge), up to 50 Gbps (larger sizes)
- **c6id**: Same as c6i but includes local NVMe SSD storage

## Updated Cost Analysis

### Current Setup
- **c5.xlarge**: $0.17/hr, Up to 10 Gbps
- **1TB EBS**: $0.08/hr
- **Total**: $7.02 per BAM (22.5 hours)

### C6i Options with Right-Sized EBS (250GB)

| Instance | vCPUs | Network | $/hr | Est. Time* | Instance $ | 250GB EBS $ | Total $ | Savings |
|----------|-------|---------|------|------------|------------|-------------|---------|---------|
| c5.xlarge | 4 | 10 Gbps | $0.17 | 22.5h | $3.82 | $1.80 | $5.62 | 20% |
| **c6i.xlarge** | 4 | 12.5 Gbps | $0.17 | 20h | $3.40 | $1.60 | **$5.00** | **29%** |
| c6i.2xlarge | 8 | 12.5 Gbps | $0.34 | 20h | $6.80 | $1.60 | $8.40 | -20% |
| c6i.4xlarge | 16 | 25 Gbps | $0.68 | 15h | $10.20 | $1.20 | $11.40 | -62% |

*Upload time estimates based on network performance increase

### C6id Option (with Local NVMe)

The c6id includes local NVMe storage, potentially eliminating EBS costs:

| Instance | vCPUs | Local Storage | $/hr | Est. Time | Instance $ | EBS $ | Total $ | Savings |
|----------|-------|---------------|------|-----------|------------|-------|---------|---------|
| c6id.xlarge | 4 | 237 GB NVMe | $0.2016 | 20h | $4.03 | $0 | **$4.03** | **43%** |
| c6id.2xlarge | 8 | 474 GB NVMe | $0.4032 | 20h | $8.06 | $0 | $8.06 | -15% |

## Recommendations

### Option 1: c6i.xlarge with 250GB EBS (Best Balance)
```yaml
hints:
  - class: 'sbg:AWSInstanceType'
    value: 'c6i.xlarge'
  
  - class: 'sbg:DiskRequirement'
    value: 250  # Right-sized for 228GB BAM
```
- **Cost**: $5.00 per BAM
- **Savings**: 29%
- **Pros**: Simple, reliable, good network
- **Cons**: Still needs EBS

### Option 2: c6id.xlarge with Local NVMe (Best Savings)
```yaml
hints:
  - class: 'sbg:AWSInstanceType'
    value: 'c6id.xlarge'
  
  # No EBS needed - use local NVMe
  - class: 'sbg:DiskRequirement'
    value: 10  # Minimal for logs only
```
- **Cost**: $4.03 per BAM
- **Savings**: 43%
- **Pros**: No EBS cost, fast local storage
- **Cons**: Must ensure Seven Bridges supports local instance storage

## Implementation Notes

### For c6id with Local Storage

1. **Check Seven Bridges Support**: 
   ```bash
   # Verify if Seven Bridges mounts instance storage
   # In your task, check for /mnt/nvme or similar
   ```

2. **Modify CWL if Needed**:
   ```yaml
   requirements:
     ShellCommandRequirement: {}
   
   baseCommand: 
     - bash
     - -c
   arguments:
     - |
       # Check if local storage is available
       if [ -d /mnt/nvme ]; then
         echo "Using local NVMe storage"
         export TMPDIR=/mnt/nvme
       fi
       gdc_upload_single.sh "$@"
   ```

### Network Performance Optimization

The c6i series has better network performance, but to maximize it:

1. **Enable Enhanced Networking** (if not automatic):
   ```yaml
   hints:
     - class: 'sbg:AWSFeatures'
       value: 
         enhancedNetworking: true
   ```

2. **Monitor Actual Transfer Speed**:
   ```bash
   # In your upload logs, look for speed metrics
   grep "Speed:" upload-*.log
   ```

## Cost Projection for Multiple BAMs

### Using c6i.xlarge (Sequential)
- 10 BAMs: $50.00 total
- 100 BAMs: $500.00 total

### Using c6id.xlarge (Sequential)
- 10 BAMs: $40.30 total
- 100 BAMs: $403.00 total

### Parallel Processing on Larger Instance
If you can run multiple uploads in parallel:

**c6i.8xlarge** (32 vCPUs, 25 Gbps):
- Can run 4 uploads in parallel
- Time for 4 BAMs: ~20 hours
- Cost: $27.20 instance + $6.40 EBS = $33.60
- Per BAM: $8.40 (higher due to instance overhead)

## Summary

**Best Option: c6id.xlarge**
- 43% cost savings
- No EBS management
- Fast local NVMe storage
- Same network performance as c6i.xlarge

**Second Best: c6i.xlarge with 250GB EBS**
- 29% cost savings
- More predictable if Seven Bridges doesn't support local storage
- Still significant improvement over current setup

The key is to:
1. Use c6i series for better network
2. Right-size storage (250GB EBS or use local NVMe)
3. Keep single uploads for now (parallel doesn't save money with staging overhead)