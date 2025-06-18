# GCP vs AWS Cost Analysis for GDC Uploads

## Instance Pricing Comparison

### Equivalent Instances

| Instance Type | AWS $/hr | GCP $/hr | GCP Spot $/hr |
|--------------|----------|----------|---------------|
| c6id.xlarge (4 vCPU, 8GB, 237GB SSD) | $0.2016 | n2-standard-4 + SSD: ~$0.25 | ~$0.075 |
| c6id.large (2 vCPU, 4GB, 118GB SSD) | $0.1008 | n2-standard-2 + SSD: ~$0.13 | ~$0.04 |
| c6i.xlarge (4 vCPU, 8GB) | $0.17 | n2-standard-4: $0.19 | ~$0.057 |

GCP instances are slightly more expensive, but spot (preemptible) prices are comparable.

## The Egress Fee Problem

### GDC Upload Destination
- GDC (Genomic Data Commons) is hosted in AWS us-east-1
- Uploading from GCP = **cross-cloud egress**

### GCP Egress Pricing
- **To Internet/Other Clouds**: $0.12/GB (first 1TB)
- **228GB BAM**: 228 × $0.12 = **$27.36 per file**

## Total Cost Comparison

### From AWS (No Egress)
| Method | Instance $ | Storage $ | Egress $ | Total/BAM |
|--------|------------|-----------|----------|-----------|
| Current AWS | $3.82 | $3.20 | $0 | $7.02 |
| AWS c6id.xlarge spot | $1.40 | $0 | $0 | **$1.40** |

### From GCP (With Egress)
| Method | Instance $ | Storage $ | Egress $ | Total/BAM |
|--------|------------|-----------|----------|-----------|
| GCP n2-standard-4 | $3.80 | $3.00 | $27.36 | **$34.16** |
| GCP n2-standard-4 spot | $1.14 | $1.00 | $27.36 | **$29.50** |

**GCP is 4-5x more expensive due to egress fees!**

## When GCP Makes Sense

### 1. Data Already in GCP
If your BAM files are already in GCP and you need them there afterward:
- One-time egress cost
- Amortize over multiple uses

### 2. GCP Credits
If you have GCP credits that cover egress:
- Effectively removes the $27.36 cost
- Makes GCP competitive

### 3. Multi-Cloud Strategy
If you're processing in GCP and only uploading results:
- Process in GCP: 1TB → 100GB results
- Upload only results: $12 egress vs $120

## Optimizing GCP Uploads

### Option 1: Use GCP Transfer Service
```bash
# Transfer from GCS to S3 first (might be cheaper)
gsutil -m cp gs://your-bucket/*.bam s3://temp-bucket/

# Then upload from AWS
# Use EC2 instance in same region as GDC
```

### Option 2: GCP Private Network to AWS
If you have high volume:
- Set up Interconnect/Private peering
- Reduces egress to ~$0.02/GB
- Requires commitment and setup

### Option 3: Process in GCP, Upload from AWS
```python
# In GCP: Process and generate manifest
process_bam_files()  # CPU intensive work
generate_manifest()  # Create metadata

# Transfer only manifest to AWS (small file)
gsutil cp manifest.json s3://bucket/

# In AWS: Do actual upload
# Launch c6id.xlarge spot in AWS
gdc-upload --manifest manifest.json ...
```

## Cost Calculator

```python
def calculate_upload_cost(provider, file_size_gb, instance_hours):
    costs = {
        'aws': {
            'instance': 0.07,  # c6id.xlarge spot
            'storage': 0,      # local NVMe
            'egress': 0        # Same cloud
        },
        'gcp': {
            'instance': 0.075, # n2-standard-4 spot  
            'storage': 0.05,   # Local SSD
            'egress': 0.12     # Per GB to internet
        }
    }
    
    provider_costs = costs[provider]
    instance_cost = provider_costs['instance'] * instance_hours
    storage_cost = provider_costs['storage'] * instance_hours
    egress_cost = provider_costs['egress'] * file_size_gb
    
    return {
        'instance': instance_cost,
        'storage': storage_cost,
        'egress': egress_cost,
        'total': instance_cost + storage_cost + egress_cost
    }

# Example
aws_cost = calculate_upload_cost('aws', 228, 20)
gcp_cost = calculate_upload_cost('gcp', 228, 20)

print(f"AWS Total: ${aws_cost['total']:.2f}")
print(f"GCP Total: ${gcp_cost['total']:.2f}")
# AWS Total: $1.40
# GCP Total: $29.50
```

## Regional Considerations

### If GDC has Multiple Endpoints
Check if GDC has regional endpoints:
- us-east-1 (primary)
- us-west-2 (possible)
- eu-central-1 (unlikely)

If GDC is only in us-east-1, even AWS us-west-2 has no egress fees.

## Recommendations

### For GCP Users

1. **Don't upload from GCP** unless:
   - You have credits covering egress
   - Data is already there and needs to stay
   - You're uploading small processed results (<10GB)

2. **Best Practice**:
   - Process in GCP (if needed)
   - Sync RAW data to AWS S3
   - Upload from AWS EC2 spot instances
   - Total: $1.40 + one-time sync cost

3. **For Large Scale** (>100 BAMs):
   - Consider AWS Direct Connect or GCP Interconnect
   - Reduces egress to $0.02/GB
   - Break-even at ~40 BAMs/month

## Summary

| Upload From | Cost per 228GB BAM | Notes |
|-------------|-------------------|-------|
| AWS c6id.xlarge spot | **$1.40** | Best option |
| GCP n2-standard-4 spot | **$29.50** | Egress kills it |
| GCP → AWS → GDC | ~$3-5 | One-time transfer |

**Stick with AWS for uploads** - the egress fees make GCP 20x more expensive for this use case!