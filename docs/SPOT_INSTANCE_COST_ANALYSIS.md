# Spot Instance Cost Analysis for GDC Uploads

## Spot Instance Pricing

Spot instances typically offer 60-90% discount from on-demand prices. Based on historical AWS spot pricing:

### On-Demand vs Spot Pricing

| Instance | On-Demand $/hr | Typical Spot $/hr | Spot Savings |
|----------|----------------|-------------------|--------------|
| c6i.xlarge | $0.17 | $0.05-0.07 | 60-70% |
| c6id.xlarge | $0.2016 | $0.06-0.08 | 60-70% |
| c6i.2xlarge | $0.34 | $0.10-0.14 | 60-70% |
| m5a.8xlarge | $1.376 | $0.40-0.55 | 60-70% |

## Updated Cost Analysis with Spot

### Single Upload Scenarios

#### Current Setup (On-Demand)
- c5.xlarge: $3.82
- 1TB EBS: $3.20
- **Total: $7.02**

#### c6id.xlarge with Spot (Best Single Upload)
- c6id.xlarge spot: $0.07/hr × 20h = **$1.40**
- No EBS (uses local NVMe)
- **Total: $1.40 (80% savings!)**

#### c6i.xlarge with Spot + Elastic Storage
- c6i.xlarge spot: $0.06/hr × 20h = **$1.20**
- Elastic Storage: ~$0-0.50
- **Total: $1.20-1.70 (76-83% savings)**

### Parallel Upload on Spot (m5a.8xlarge)

For multiple BAMs:
- m5a.8xlarge spot: $0.48/hr
- 16 concurrent uploads
- Time for 16 BAMs: ~41 hours
- Total cost: $19.68
- **Per BAM: $1.23 (82.5% savings)**

## Spot Instance Interruption Handling

### For c6id.xlarge (Single Upload)

Since uploads take ~20 hours, interruption is likely. Use the spot-resilient uploader:

```bash
# Using the spot-upload command we created
gdc-uploader spot-upload manifest.yaml token.txt file.bam \
  --state-file /persistent/upload_state.json
```

### Seven Bridges Spot Configuration

```yaml
hints:
  # Enable spot instances
  - class: 'sbg:SpotInstance'
    value: true
  
  # Set maximum spot price (optional)
  - class: 'sbg:maxSpotPrice'
    value: 0.10  # Max $0.10/hr for c6id.xlarge
  
  # Use c6id for local storage
  - class: 'sbg:AWSInstanceType'
    value: 'c6id.xlarge'
  
  # Minimal EBS (logs only)
  - class: 'sbg:DiskRequirement'
    value: 10
```

## Spot Availability by Instance Type

Based on AWS spot advisor data:

| Instance | Interruption Rate | Availability | Recommendation |
|----------|------------------|--------------|----------------|
| c6i.xlarge | <5% | High | ✅ Excellent |
| c6id.xlarge | <5% | High | ✅ Excellent |
| c6i.2xlarge | <5% | High | ✅ Excellent |
| m5a.8xlarge | 5-10% | Medium | ⚠️ Good with retries |

## Cost Optimization Decision Tree

```
1. Single BAM upload?
   └─ Yes → Use c6id.xlarge spot ($1.40/BAM)
   └─ No → Continue to #2

2. Have 8+ BAMs to upload?
   └─ Yes → Use m5a.8xlarge spot parallel ($1.23/BAM)
   └─ No → Use c6id.xlarge spot sequentially

3. Elastic Storage available?
   └─ Yes → Use c6i.xlarge spot + Elastic ($1.20/BAM)
   └─ No → Use c6id.xlarge spot ($1.40/BAM)
```

## Implementation Strategy

### 1. Test Spot Interruption Handling

```bash
#!/bin/bash
# Test script for spot resilience

# Launch spot instance
INSTANCE_ID=$(aws ec2 run-instances \
  --instance-type c6id.xlarge \
  --instance-market-options "MarketType=spot" \
  --user-data file://spot-upload-userdata.sh \
  --query 'Instances[0].InstanceId' \
  --output text)

# Monitor upload
while true; do
  STATUS=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text)
  
  if [ "$STATUS" != "running" ]; then
    echo "Instance terminated, checking upload state..."
    # Check S3 for state file
    aws s3 cp s3://my-bucket/upload_state.json - | jq .
    break
  fi
  
  sleep 300  # Check every 5 minutes
done
```

### 2. Seven Bridges Spot Task

```json
{
  "name": "GDC Upload with Spot",
  "app": "gdc-upload-single",
  "inputs": {
    "metadata_file": {"class": "File", "path": "metadata.json"},
    "token_file": {"class": "File", "path": "token.txt"},
    "target_file": {"class": "File", "path": "sample.bam"}
  },
  "hints": {
    "sbg:SpotInstance": true,
    "sbg:AWSInstanceType": "c6id.xlarge",
    "sbg:maxSpotPrice": 0.10
  }
}
```

## Risk Mitigation

### Interruption Probability

For a 20-hour upload on c6id.xlarge:
- Interruption rate: <5%
- Probability of completion: ~95%
- With retry: >99% success rate

### Backup Strategy

If spot is interrupted frequently:
1. Use Spot Fleet with multiple instance types
2. Set higher max price ($0.12 vs $0.07 typical)
3. Use on-demand for critical time-sensitive uploads

## Final Cost Comparison

| Method | Instance Cost | Storage Cost | Total/BAM | Savings |
|--------|--------------|--------------|-----------|---------|
| Current (On-Demand) | $3.82 | $3.20 | $7.02 | - |
| c6id.xlarge (On-Demand) | $4.03 | $0 | $4.03 | 43% |
| **c6id.xlarge (Spot)** | **$1.40** | **$0** | **$1.40** | **80%** |
| c6i.xlarge + Elastic (Spot) | $1.20 | $0-0.50 | $1.20-1.70 | 76-83% |
| m5a.8xlarge parallel (Spot) | - | - | $1.23/BAM | 82.5% |

## Recommendation

**Use c6id.xlarge spot instances** for incredible 80% cost savings:
- $1.40 per BAM (vs $7.02 current)
- Local NVMe eliminates EBS costs
- Low interruption rate (<5%)
- Built-in retry logic handles interruptions

This is the most cost-effective solution for your uploads!