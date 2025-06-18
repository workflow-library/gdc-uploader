# M6i Instance Analysis for GDC Uploads

## M6i vs M6id Comparison

| Instance | vCPUs | RAM | Network | Storage | On-Demand $/hr | Spot $/hr | Interruption |
|----------|-------|-----|---------|---------|----------------|-----------|--------------|
| m6i.xlarge | 4 | 16 GB | 12.5 Gbps | EBS only | $0.192 | ~$0.06-0.08 | <5% ✅ |
| m6i.large | 2 | 8 GB | 12.5 Gbps | EBS only | $0.096 | ~$0.03-0.04 | <5% ✅ |
| m6id.xlarge | 4 | 16 GB | 12.5 Gbps | 237 GB NVMe | $0.2268 | ~$0.07-0.10 | 10-15% ⚠️ |
| m6id.large | 2 | 8 GB | 12.5 Gbps | 118 GB NVMe | $0.1134 | ~$0.04-0.05 | 10-15% ⚠️ |

## Key Advantages of M6i

1. **Low interruption rate** (<5%) - Much better than c6id/m6id
2. **More memory** - 16GB vs 8GB on c6i.xlarge
3. **Latest generation** - Better performance per dollar
4. **Stable spot pricing** - General purpose instances

## Cost Analysis

### Option 1: m6i.xlarge Spot + 250GB EBS (Recommended)
```yaml
hints:
  - class: 'sbg:SpotInstance'
    value: true
  - class: 'sbg:AWSInstanceType'
    value: 'm6i.xlarge'
  - class: 'sbg:DiskRequirement'
    value: 250
```

**Cost**:
- m6i.xlarge spot: $0.07/hr × 20h = $1.40
- 250GB EBS: $0.08/hr × 20h = $1.60
- **Total: $3.00/BAM (57% savings)**
- **Success rate: ~95%**

### Option 2: m6i.large Spot + 250GB EBS (Budget)
```yaml
hints:
  - class: 'sbg:SpotInstance'
    value: true
  - class: 'sbg:AWSInstanceType'
    value: 'm6i.large'
  - class: 'sbg:DiskRequirement'
    value: 250
```

**Cost**:
- m6i.large spot: $0.035/hr × 20h = $0.70
- 250GB EBS: $0.08/hr × 20h = $1.60
- **Total: $2.30/BAM (67% savings)**
- **Success rate: ~95%**

### Option 3: m6i.xlarge + Elastic Storage (Best if Streaming)
```yaml
hints:
  - class: 'sbg:SpotInstance'
    value: true
  - class: 'sbg:AWSInstanceType'
    value: 'm6i.xlarge'
  - class: 'sbg:useElasticStorage'
    value: true
  - class: 'sbg:DiskRequirement'
    value: 10  # Minimal
```

**Cost**:
- m6i.xlarge spot: $1.40
- Elastic Storage: $0-0.50 (depends on implementation)
- **Total: $1.40-1.90/BAM (73-80% savings)**
- **Success rate: ~95%**

## Why NOT m6id?

Despite having local NVMe:
1. **Higher interruption** (10-15%) vs m6i (<5%)
2. **More expensive** spot pricing
3. **Risk of restart** negates storage savings

For 20-hour uploads:
- m6id: 15% interruption = potential $4+ total cost with restarts
- m6i: 5% interruption = reliable $3 cost

## Performance Comparison

### Network Performance
All m6i/m6id have same 12.5 Gbps, but:
- m6i.xlarge: More consistent (not competing for NVMe)
- Upload speed should be identical

### Memory Advantage
- m6i.xlarge: 16GB RAM (plenty of headroom)
- c6i.xlarge: 8GB RAM (sufficient but tight)

## Decision Matrix

```
Budget Priority?
├─ Yes → m6i.large spot + 250GB EBS ($2.30/BAM)
└─ No → Elastic Storage Available?
    ├─ Yes → m6i.xlarge spot + Elastic ($1.40-1.90/BAM)
    └─ No → m6i.xlarge spot + 250GB EBS ($3.00/BAM)
```

## Monitoring Commands

```bash
# Check current m6i spot prices
aws ec2 describe-spot-price-history \
  --instance-types m6i.xlarge m6i.large \
  --product-descriptions "Linux/UNIX" \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --query 'SpotPriceHistory[*].[InstanceType,SpotPrice,AvailabilityZone]' \
  --output table

# Compare interruption rates (use Spot Instance Advisor)
# m6i typically shows <5% interruption frequency
```

## Final Recommendation

**For highest reliability with good savings:**

1. **m6i.xlarge spot + 250GB EBS**
   - $3.00/BAM (57% savings)
   - 95% success rate
   - 16GB RAM for comfort
   
2. **m6i.large spot + 250GB EBS** 
   - $2.30/BAM (67% savings)
   - 95% success rate
   - If 2 vCPUs is sufficient

3. **Test Elastic Storage** with m6i.xlarge
   - Could achieve $1.40/BAM (80% savings)
   - Same reliability

**Avoid m6id** for spot - the interruption rate is too high for 20-hour uploads. The local NVMe isn't worth the risk of restarts.