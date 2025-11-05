# Network Configuration Guide

This guide explains the network configuration options for the trading bot EC2 instance.

## Network Options

### Option 1: Default VPC (Recommended for Cost Optimization)

**Default Configuration:**
```hcl
create_vpc = false
```

**Pros:**
- ✅ No additional costs
- ✅ Simple setup
- ✅ Works out of the box
- ✅ Good for single instance deployments

**Cons:**
- ⚠️ Less network isolation
- ⚠️ Uses AWS default VPC settings

**Use Case:** Development, testing, or single-instance production deployments

### Option 2: Custom VPC (Recommended for Production)

**Configuration:**
```hcl
create_vpc = true
vpc_cidr   = "10.0.0.0/16"
```

**Pros:**
- ✅ Better network isolation
- ✅ More control over network configuration
- ✅ Better security posture
- ✅ Can add private subnets later

**Cons:**
- 💰 Additional costs (minimal, but not zero)
- ⚠️ More complex setup

**Use Case:** Production deployments requiring better network isolation

## Security Configuration

### SSH Access Control

**Important:** Restrict SSH access to your IP for security.

```hcl
# Find your IP: https://whatismyipaddress.com/
allowed_ssh_cidr = [
  "123.45.67.89/32"  # Your IP address
]
```

**Or allow from office/home:**
```hcl
allowed_ssh_cidr = [
  "123.45.67.89/32",  # Home IP
  "98.76.54.32/32"    # Office IP
]
```

**⚠️ WARNING:** Using `0.0.0.0/0` allows SSH from anywhere - not recommended for production!

### Public IP Configuration

```hcl
enable_public_ip = true  # Required for internet access
```

**When to disable:**
- Instance in private subnet
- Using NAT Gateway
- Using VPN or Direct Connect

### Elastic IP (Static IP)

```hcl
use_elastic_ip = true  # Allocates static IP
```

**Pros:**
- ✅ IP address doesn't change
- ✅ Easier to whitelist in firewalls
- ✅ Better for DNS records

**Cons:**
- 💰 Costs ~$0.005/hour when allocated but not attached
- ⚠️ Can't use with spot instances

**Use Case:** When you need a static IP address

## Storage Configuration

### EBS Volume Settings

```hcl
ebs_volume_size  = 8      # Minimum 8 GB for Amazon Linux
ebs_volume_type  = "gp3"  # gp3 is cheapest and fastest
ebs_encrypted     = true   # Enable encryption
```

**Volume Types:**
- `gp3`: General Purpose SSD (recommended, cheapest)
- `gp2`: General Purpose SSD (legacy)
- `io1`: Provisioned IOPS SSD (expensive, for high I/O)

**Encryption:**
- Always enable encryption for production
- AWS managed encryption keys (default)
- No performance impact

## Monitoring Configuration

### Detailed Monitoring

```hcl
enable_detailed_monitoring = false  # Costs extra
```

**Basic Monitoring:**
- Free: 5-minute intervals
- Included in CloudWatch

**Detailed Monitoring:**
- Costs extra: ~$2-3/month
- 1-minute intervals
- Better for troubleshooting

**CloudWatch Alarms:**
- ✅ Instance status check (free)
- ✅ CPU utilization (free)
- ✅ Memory utilization (requires detailed monitoring)

## Cost Optimization Features

### Spot Instances

```hcl
use_spot_instance = true  # Up to 90% cheaper
```

**Best Practices:**
- Use for non-critical workloads
- Enable termination protection = false
- Use gp3 EBS volumes (faster snapshot/restore)
- Implement graceful shutdown in application

### Log Retention

```hcl
backup_retention_days = 7  # Keep logs for 7 days
```

**Cost Impact:**
- 7 days: ~$0.50/month
- 30 days: ~$2/month
- 90 days: ~$6/month

### Network Costs

**Default VPC:**
- No additional costs

**Custom VPC:**
- Internet Gateway: Free
- NAT Gateway: ~$32/month + data transfer (if used)
- VPC Endpoints: ~$7/month per endpoint (if used)

## Recommended Configurations

### Development/Testing

```hcl
create_vpc = false
use_spot_instance = true
enable_public_ip = true
allowed_ssh_cidr = ["0.0.0.0/0"]  # For testing
ebs_encrypted = false  # Optional for dev
backup_retention_days = 3
```

**Estimated Cost:** ~$2-3/month

### Production (Cost-Optimized)

```hcl
create_vpc = false
use_spot_instance = true
enable_public_ip = true
allowed_ssh_cidr = ["YOUR_IP/32"]  # Your IP only
ebs_encrypted = true
backup_retention_days = 7
enable_detailed_monitoring = false
```

**Estimated Cost:** ~$3-5/month

### Production (Security-Focused)

```hcl
create_vpc = true
vpc_cidr = "10.0.0.0/16"
use_spot_instance = false  # Use on-demand for reliability
enable_public_ip = true
use_elastic_ip = true
allowed_ssh_cidr = ["YOUR_IP/32"]
ebs_encrypted = true
backup_retention_days = 14
enable_detailed_monitoring = true
```

**Estimated Cost:** ~$10-15/month

## Network Architecture

### Default VPC Architecture

```
Internet
   |
   v
Default VPC (10.0.0.0/16)
   |
   v
Default Subnet (10.0.1.0/24)
   |
   v
EC2 Instance
   |
   v
Internet Gateway (implicit)
```

### Custom VPC Architecture

```
Internet
   |
   v
Internet Gateway
   |
   v
Custom VPC (10.0.0.0/16)
   |
   v
Public Subnet (10.0.0.0/24)
   |
   v
EC2 Instance
   |
   v
Route Table -> Internet Gateway
```

## Security Best Practices

### 1. Restrict SSH Access

```hcl
# Use your IP only
allowed_ssh_cidr = ["YOUR_IP/32"]
```

### 2. Enable IMDSv2

Already configured in the Terraform:
```hcl
metadata_options {
  http_tokens = "required"  # IMDSv2 required
}
```

### 3. Encrypt EBS Volumes

```hcl
ebs_encrypted = true
```

### 4. Use Security Groups

- Only allow necessary ports
- Restrict source IPs
- Review regularly

### 5. Enable CloudWatch Logs

- Monitor access attempts
- Track resource usage
- Set up alarms

## Troubleshooting

### Instance Can't Access Internet

**Check:**
1. `enable_public_ip = true`
2. Security group allows outbound traffic
3. Internet Gateway exists (if custom VPC)
4. Route table has default route (0.0.0.0/0)

### Can't SSH to Instance

**Check:**
1. Security group allows your IP
2. SSH key is correct
3. Instance has public IP
4. Instance is running

### High Network Costs

**Check:**
1. NAT Gateway usage (if using private subnet)
2. Data transfer out
3. VPC Endpoints usage
4. Cross-AZ data transfer

## Cost Breakdown

### Monthly Costs (ap-south-1)

**Default VPC + Spot Instance:**
- EC2 Spot (t3.micro): ~$2-3
- EBS (8GB gp3): ~$0.64
- CloudWatch Logs (7 days): ~$0.50
- **Total: ~$3-4/month**

**Custom VPC + On-Demand:**
- EC2 On-Demand (t3.micro): ~$8-10
- EBS (8GB gp3): ~$0.64
- CloudWatch Logs (7 days): ~$0.50
- Internet Gateway: Free
- **Total: ~$9-11/month**

## Additional Resources

- [AWS VPC Documentation](https://docs.aws.amazon.com/vpc/)
- [EC2 Instance Types](https://aws.amazon.com/ec2/instance-types/)
- [EBS Volume Types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html)
- [Security Groups Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)

