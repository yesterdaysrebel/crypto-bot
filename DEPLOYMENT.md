# AWS Deployment Guide

Complete step-by-step guide to deploy the crypto trading bot to AWS EC2.

## Automated Deployment with GitHub Actions

**🚀 Recommended Method**: Use GitHub Actions for automated deployment!

See [`.github/workflows/README.md`](.github/workflows/README.md) for complete setup instructions.

### Quick Setup for GitHub Actions

1. **Set up OIDC Authentication with AWS** (See [`.github/workflows/setup-oidc.md`](.github/workflows/setup-oidc.md)):
   - Create OIDC provider in AWS IAM
   - Create IAM role for GitHub Actions
   - Add `AWS_ROLE_ARN` to GitHub Secrets

2. **Set up GitHub Secrets** (Settings → Secrets and variables → Actions):
   - `AWS_ROLE_ARN` - IAM Role ARN (from OIDC setup)
   - `AWS_SSH_KEY_NAME` - AWS EC2 key pair name
   - `AWS_SSH_PRIVATE_KEY` - Private key content (for SSH access)
   - `DELTA_API_KEY` - Delta Exchange API key
   - `DELTA_API_SECRET` - Delta Exchange API secret

2. **Push to main branch** - Deployment happens automatically!

3. **Or trigger manually** - Go to Actions tab → Deploy to AWS → Run workflow

### Benefits of GitHub Actions

- ✅ **Secure OIDC authentication** - No long-lived AWS credentials
- ✅ Automated testing before deployment
- ✅ Automatic deployment on push to main
- ✅ Manual deployment option
- ✅ Environment variable management
- ✅ Deployment verification
- ✅ No manual SSH required

---

## Manual Deployment

### Prerequisites

Before deploying manually, ensure you have:

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
   ```bash
   aws --version
   aws configure
   ```
3. **Terraform** installed (>= 1.0)
   ```bash
   terraform --version
   # Install from: https://www.terraform.io/downloads
   ```
4. **SSH Key Pair** in AWS (or create one)
   ```bash
   # Create key pair in AWS Console or via CLI:
   aws ec2 create-key-pair --key-name trading-bot-key --query 'KeyMaterial' --output text > ~/.ssh/trading-bot-key.pem
   chmod 400 ~/.ssh/trading-bot-key.pem
   ```

## Step-by-Step Deployment

### Step 1: Configure Terraform Variables

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
aws_region        = "ap-south-1"  # Mumbai region (adjust as needed)
instance_type    = "t3.micro"     # Free tier eligible
use_spot_instance = true           # Use spot instances for cost savings
spot_price        = ""              # Leave empty for on-demand price
ssh_key_name      = "trading-bot-key"  # Your AWS SSH key pair name
```

**Important:** Replace `ssh_key_name` with your actual AWS key pair name.

### Step 2: Review Terraform Configuration

Review the main configuration in `infra/terraform/main.tf`:

- **Instance Type**: `t3.micro` (free tier eligible, lowest cost)
- **Spot Instances**: Enabled by default (up to 90% cheaper)
- **Security Group**: Allows SSH (port 22) from anywhere (restrict in production)
- **IAM Role**: Grants CloudWatch access for logging

### Step 3: Deploy Infrastructure

**Option A: Using Deployment Script (Recommended)**

```bash
cd infra
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Check for Terraform and AWS CLI
2. Initialize Terraform
3. Plan the deployment
4. Ask for confirmation
5. Apply the configuration

**Option B: Manual Deployment**

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan

# Apply the configuration
terraform apply
```

When prompted, type `yes` to confirm.

### Step 4: Get Instance Information

After deployment completes, get the instance details:

```bash
cd infra/terraform

# Get instance ID
terraform output instance_id

# Get public IP
terraform output instance_public_ip

# Get SSH command
terraform output ssh_command
```

Or view all outputs:
```bash
terraform output
```

### Step 5: Deploy Application Code

You have several options to deploy the code:

#### Option A: Using Git (Recommended for Updates)

1. **Set up CodeCommit or use GitHub with token:**

Update `infra/terraform/user_data.sh` to clone from your repository:

```bash
# In user_data.sh, replace the placeholder:
git clone https://github.com/yourusername/crypto-bot.git /opt/trading-bot
# Or use CodeCommit:
# git clone https://git-codecommit.ap-south-1.amazonaws.com/v1/repos/crypto-bot /opt/trading-bot
```

2. **SSH into the instance:**

```bash
ssh -i ~/.ssh/trading-bot-key.pem ec2-user@<instance-public-ip>
```

3. **Clone and set up:**

```bash
cd /opt/trading-bot
git clone https://github.com/yourusername/crypto-bot.git .
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Option B: Using S3 (Recommended for Initial Deployment)

1. **Create S3 bucket and upload code:**

```bash
# Create bucket
aws s3 mb s3://your-trading-bot-bucket --region ap-south-1

# Create tarball (from project root)
cd ../..
tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='data' --exclude='models' --exclude='trade_logs' \
    --exclude='backtest_reports' --exclude='htmlcov' \
    -czf trading-bot.tar.gz .

# Upload to S3
aws s3 cp trading-bot.tar.gz s3://your-trading-bot-bucket/

# Update user_data.sh to download from S3
# Add this line in user_data.sh before pip install:
# aws s3 cp s3://your-trading-bot-bucket/trading-bot.tar.gz /opt/trading-bot/
# cd /opt/trading-bot && tar -xzf trading-bot.tar.gz
```

2. **SSH into instance and download:**

```bash
ssh -i ~/.ssh/trading-bot-key.pem ec2-user@<instance-public-ip>
cd /opt/trading-bot
aws s3 cp s3://your-trading-bot-bucket/trading-bot.tar.gz .
tar -xzf trading-bot.tar.gz
```

#### Option C: Using SCP (Quick Manual Deployment)

```bash
# From project root
cd ../..
scp -i ~/.ssh/trading-bot-key.pem -r \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='data' \
    --exclude='models' \
    --exclude='trade_logs' \
    --exclude='backtest_reports' \
    . ec2-user@<instance-public-ip>:/opt/trading-bot/
```

### Step 6: Configure Environment Variables

SSH into the instance and set up environment variables:

```bash
ssh -i ~/.ssh/trading-bot-key.pem ec2-user@<instance-public-ip>
cd /opt/trading-bot

# Create .env file
nano .env
```

Add your Delta Exchange API credentials:

```bash
DELTA_API_KEY=your_api_key_here
DELTA_API_SECRET=your_api_secret_here
DELTA_BASE_URL=https://api.delta.exchange
DELTA_TESTNET=false

TRADING_PRODUCTS=BTCUSD,ETHUSD
MAX_POSITION_SIZE=1000.0
MAX_LEVERAGE=10
RISK_PER_TRADE=0.02
DEFAULT_TIMEFRAME=1h

ML_MODEL_PATH=models
ML_RETRAIN_INTERVAL_HOURS=24
ML_FEATURE_WINDOW=100
ML_PREDICTION_THRESHOLD=0.6

DATA_DIR=data
LOG_LEVEL=INFO
```

Save and exit (Ctrl+X, Y, Enter).

**Alternative: Use AWS Systems Manager Parameter Store (More Secure)**

```bash
# Store secrets in Parameter Store
aws ssm put-parameter --name "/trading-bot/delta-api-key" --value "your-key" --type "SecureString"
aws ssm put-parameter --name "/trading-bot/delta-api-secret" --value "your-secret" --type "SecureString"

# Update user_data.sh or systemd service to read from Parameter Store
```

### Step 7: Set Up Systemd Service

The `user_data.sh` script should have created the systemd service. Verify and update if needed:

```bash
# Check service file
sudo cat /etc/systemd/system/trading-bot.service

# Update service to load .env file
sudo nano /etc/systemd/system/trading-bot.service
```

Add this line in the `[Service]` section:

```ini
EnvironmentFile=-/opt/trading-bot/.env
```

Or use Parameter Store values:

```ini
Environment="DELTA_API_KEY=$(aws ssm get-parameter --name /trading-bot/delta-api-key --with-decryption --query Parameter.Value --output text)"
Environment="DELTA_API_SECRET=$(aws ssm get-parameter --name /trading-bot/delta-api-secret --with-decryption --query Parameter.Value --output text)"
```

Reload and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

### Step 8: Verify Deployment

Check if the service is running:

```bash
# Check service status
sudo systemctl status trading-bot

# View logs
sudo journalctl -u trading-bot -f

# Or check application logs
tail -f /opt/trading-bot/trading_bot.log
```

### Step 9: Monitor and Maintain

#### View Logs

```bash
# Systemd logs
sudo journalctl -u trading-bot -f

# Application logs
tail -f /opt/trading-bot/trading_bot.log

# CloudWatch logs (if configured)
aws logs tail /aws/ec2/trading-bot --follow
```

#### Update Code

If using Git:

```bash
ssh -i ~/.ssh/trading-bot-key.pem ec2-user@<instance-public-ip>
cd /opt/trading-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart trading-bot
```

#### Monitor Costs

- Check AWS Cost Explorer
- Set up billing alerts
- Monitor CloudWatch metrics

## Cost Estimation

**Monthly Costs (ap-south-1 region):**

- **t3.micro Spot Instance**: ~$2-3/month
- **CloudWatch Logs** (7-day retention): ~$0.50/month
- **Data Transfer**: ~$1-2/month
- **Total**: **~$3-6/month**

**Cost Optimization Tips:**

1. Use Spot Instances (already enabled)
2. Monitor and stop instance when not trading
3. Reduce CloudWatch log retention if needed
4. Use AWS Free Tier if eligible

## Security Best Practices

1. **Restrict SSH Access:**
   - Update security group to allow SSH only from your IP
   - Use AWS Systems Manager Session Manager instead of SSH

2. **Secure API Credentials:**
   - Use AWS Systems Manager Parameter Store
   - Never commit credentials to Git
   - Rotate credentials regularly

3. **Network Security:**
   - Use private subnets if possible
   - Restrict outbound traffic if needed

4. **IAM Permissions:**
   - Follow principle of least privilege
   - Use IAM roles instead of access keys on EC2

## Troubleshooting

### Instance Not Starting

```bash
# Check CloudWatch logs
aws logs tail /aws/ec2/trading-bot --follow

# Check systemd service
sudo systemctl status trading-bot
sudo journalctl -u trading-bot -n 50
```

### Service Not Running

```bash
# Check service status
sudo systemctl status trading-bot

# Check for errors
sudo journalctl -u trading-bot --no-pager

# Restart service
sudo systemctl restart trading-bot
```

### API Connection Issues

```bash
# Verify environment variables
cat /opt/trading-bot/.env

# Test API connection
python3 -c "from config.config import Config; from collectors.delta_client import DeltaExchangeClient; c = Config(); client = DeltaExchangeClient(c.delta.api_key, c.delta.api_secret); print(client.get_products()[:1])"
```

### High Costs

```bash
# Check instance usage
aws ec2 describe-instances --instance-ids <instance-id>

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization
```

## Cleanup

To destroy the infrastructure:

```bash
cd infra/terraform
terraform destroy
```

**Note:** This will delete all resources including the EC2 instance. Make sure to backup any important data first.

## Next Steps

1. **Set up monitoring alerts** for instance status
2. **Configure automated backups** for models and data
3. **Set up cost alerts** to monitor spending
4. **Implement graceful shutdown** for spot instance interruptions
5. **Set up CI/CD** for automated deployments

## Additional Resources

- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [Delta Exchange API Documentation](https://docs.delta.exchange/)

## Support

For issues or questions:
1. Check the logs first
2. Review the troubleshooting section
3. Check AWS CloudWatch logs
4. Review the main README.md for configuration details

