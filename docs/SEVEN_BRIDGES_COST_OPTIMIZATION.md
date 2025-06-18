# Seven Bridges Cost Optimization Guide

## Understanding the True Costs

When using Seven Bridges CWL executor, files must be staged to local disk, adding significant EBS storage costs.

### Current Cost Breakdown (Per 228GB BAM)
- **c5.xlarge instance**: $3.82 (~22.5 hours @ $0.17/hr)
- **1TB gp3 EBS**: $3.20 (~40 hours @ $0.08/hr)
- **Total**: $7.02 per BAM

## Why Files Are Copied

1. **sbgFS Requirement**: Seven Bridges File System provides POSIX interface
2. **curl Limitation**: `curl --upload-file` needs a seekable file
3. **Result**: Entire BAM must be on EBS before upload starts

## Cost Optimization Strategies

### Strategy 1: Minimize EBS Size

Use exactly the storage needed:
```yaml
hints:
  - class: 'sbg:DiskRequirement'
    value: 250  # For 228GB BAM + overhead
```

**Savings**: 
- 250GB EBS: ~$0.80 vs 1TB: $3.20
- **Save $2.40 per BAM (34%)**

### Strategy 2: Use Faster Instance + Smaller EBS

Reduce upload time to reduce EBS hours:

| Instance | vCPUs | Network | $/hr | Upload Time | Instance $ | 250GB EBS $ | Total $ | Savings |
|----------|-------|---------|------|-------------|------------|-------------|---------|---------|
| c5.xlarge | 4 | Up to 10 Gbps | $0.17 | 22.5h | $3.82 | $1.80 | $5.62 | 20% |
| c5n.xlarge | 4 | Up to 25 Gbps | $0.216 | 15h* | $3.24 | $1.20 | $4.44 | 37% |
| c5n.2xlarge | 8 | Up to 25 Gbps | $0.432 | 12h* | $5.18 | $0.96 | $6.14 | 13% |

*Estimated based on network performance

**Recommendation**: c5n.xlarge for 37% savings

### Strategy 3: Batch Processing on Larger Instance

Process multiple files sequentially on one instance:

```yaml
# For 5 BAMs on c5n.2xlarge
# Total time: 60 hours
# Instance cost: $25.92
# 250GB EBS cost: $4.80
# Total: $30.72 / 5 = $6.14 per BAM
```

### Strategy 4: Request Seven Bridges Streaming Support

Contact Seven Bridges to request:
1. S3 streaming support without local staging
2. Direct S3-to-HTTPS streaming for uploads

## Recommended CWL Configuration

```yaml
hints:
  # Use enhanced networking instance
  - class: 'sbg:AWSInstanceType'
    value: 'c5n.xlarge'
  
  # Minimize disk to actual needs
  - class: 'sbg:DiskRequirement'
    value: 250  # Just enough for one BAM
  
  # Keep sbgFS enabled (required)
  - class: 'sbg:useSbgFS'
    value: 'true'
```

## Alternative: S3 Streaming Script

If Seven Bridges allows custom Docker images with AWS CLI:

```bash
# Use the streaming script
gdc_s3_stream_upload.sh \
  -m metadata.json \
  -t token.txt \
  s3://bucket/file.bam
```

This completely avoids EBS costs but requires:
- AWS CLI in Docker image
- IAM role with S3 read permissions
- Seven Bridges support for custom scripts

## Cost Comparison Summary

| Method | Instance | EBS | Total/BAM | Savings |
|--------|----------|-----|-----------|---------|
| Current (c5.xlarge + 1TB) | $3.82 | $3.20 | $7.02 | - |
| Optimized EBS (c5.xlarge + 250GB) | $3.82 | $0.80 | $4.62 | 34% |
| **Fast Network (c5n.xlarge + 250GB)** | $3.24 | $1.20 | **$4.44** | **37%** |
| Streaming (if supported) | $3.24 | $0.10 | $3.34 | 52% |

## Monitoring Costs

```bash
# Track actual usage in Seven Bridges
sbg tasks list --status completed --limit 10 | \
  jq -r '.[] | [.name, .price.amount, .execution_details.duration] | @tsv'
```

## Best Practices

1. **Right-size EBS**: Calculate `file_size * 1.1` for overhead
2. **Use Network-Optimized Instances**: c5n series for large transfers
3. **Monitor Transfer Speed**: Ensure you're getting expected throughput
4. **Consider Time-of-Day**: Network congestion affects upload speed

## Future Considerations

1. **Request Feature**: Ask Seven Bridges for S3 streaming support
2. **Custom Docker**: Build image with streaming capabilities
3. **Alternative Platforms**: Consider platforms that support streaming

The key insight is that EBS storage cost is significant when files must be staged locally. Minimizing both storage size and storage duration through faster uploads provides the best optimization within Seven Bridges' constraints.