# AWS Deployment Guide

This directory contains infrastructure as code for deploying the trading bot to AWS with minimal costs.

## Cost Optimization Features

1. **Spot Instances**: Uses EC2 Spot instances (up to 90% cheaper than on-demand)
2. **Small Instance Type**: Defaults to t3.micro (free tier eligible)
3. **Minimal Monitoring**: Disabled detailed monitoring to save costs
4. **Log Retention**: CloudWatch logs retained for only 7 days
5. **Single Instance**: Runs all strategies on one EC2 instance

## Estimated Monthly Costs

- **t3.micro Spot Instance**: ~$2-3/month (ap-south-1 region)
- **CloudWatch Logs**: ~$0.50/month (7-day retention)
- **Data Transfer**: Minimal (~$1-2/month)
- **Total**: ~$3-6/month

## Prerequisites

1. AWS CLI configured with credentials
2. Terraform installed (>= 1.0)
3. SSH key pair in AWS
4. Environment variables set (see main README)

## Deployment Steps

### 1. Configure Variables

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 2. Deploy Infrastructure

```bash
# Using the deployment script
cd infra
chmod +x deploy.sh
./deploy.sh

# Or manually
cd terraform
terraform init
terraform plan
terraform apply
```

### 3. Deploy Application Code

After the EC2 instance is running, you need to deploy the application code:

```bash
# Option 1: Using S3 (recommended)
aws s3 mb s3://your-trading-bot-bucket
tar -czf trading-bot.tar.gz ../..
aws s3 cp trading-bot.tar.gz s3://your-trading-bot-bucket/

# On EC2 instance, update user_data.sh to download from S3
```

```bash
# Option 2: Using Git (update user_data.sh)
# Set up SSH keys or use HTTPS with token
```

```bash
# Option 3: Manual deployment via SSH
scp -r -i ~/.ssh/your-key.pem ../.. ec2-user@<instance-ip>:/opt/trading-bot/
ssh -i ~/.ssh/your-key.pem ec2-user@<instance-ip>
# Then follow setup steps in user_data.sh
```

### 4. Set Environment Variables on EC2

```bash
ssh -i ~/.ssh/your-key.pem ec2-user@<instance-ip>
sudo nano /etc/systemd/system/trading-bot.service
# Add EnvironmentFile=-/opt/trading-bot/.env
sudo systemctl daemon-reload
sudo systemctl restart trading-bot
```

### 5. Monitor Logs

```bash
# On EC2
sudo journalctl -u trading-bot -f

# Or via CloudWatch
aws logs tail /aws/ec2/trading-bot --follow
```

## Alternative: Using AWS Systems Manager Session Manager

For better security, you can use SSM Session Manager instead of SSH:

```bash
aws ssm start-session --target <instance-id>
```

## Cost Monitoring

Set up AWS Cost Explorer to monitor spending:
- Go to AWS Cost Management > Cost Explorer
- Set up budgets and alerts

## Spot Instance Handling

If using spot instances, the bot should handle interruptions gracefully:
- The bot saves state periodically
- Use AWS Systems Manager to automatically restart on new instance
- Consider using ECS Fargate Spot for better reliability

## Scaling

To run multiple strategies more efficiently:
- Consider using AWS Lambda for scheduled tasks (cheaper for low-frequency)
- Use ECS Fargate Spot for better cost/performance
- Consider AWS Batch for periodic retraining

## Troubleshooting

1. **Instance not starting**: Check CloudWatch logs
2. **Service not running**: `sudo systemctl status trading-bot`
3. **API errors**: Check environment variables
4. **High costs**: Monitor CloudWatch metrics and adjust log retention

## Cleanup

To destroy infrastructure:

```bash
cd infra/terraform
terraform destroy
```

