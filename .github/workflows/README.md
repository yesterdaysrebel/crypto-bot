# GitHub Actions Workflows

This directory contains GitHub Actions workflows for CI/CD automation.

## Workflows

### 1. CI Workflow (`ci.yml`)

Runs on every pull request and push to non-main branches:
- ✅ Runs tests with pytest
- ✅ Generates coverage reports
- ✅ Lints code with flake8, black, isort
- ✅ Uploads coverage to Codecov

### 2. Deploy Workflow (`deploy.yml`)

Automatically deploys to AWS when:
- ✅ Push to `main` or `master` branch
- ✅ Manual trigger via GitHub Actions UI

**Features:**
- Runs tests before deployment
- Lints code before deployment
- Deploys infrastructure with Terraform
- Deploys application code to EC2
- Configures environment variables
- Restarts service automatically
- Verifies deployment

## Required Secrets

Set these secrets in your GitHub repository settings:

### AWS Credentials
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_SSH_KEY_NAME` - AWS EC2 key pair name
- `AWS_SSH_PRIVATE_KEY` - Private key content (for SSH access)
- `AWS_INSTANCE_TYPE` - (Optional) EC2 instance type (default: t3.micro)

### Delta Exchange API
- `DELTA_API_KEY` - Delta Exchange API key
- `DELTA_API_SECRET` - Delta Exchange API secret

### Trading Configuration (Optional)
- `TRADING_PRODUCTS` - Comma-separated list (default: BTCUSD,ETHUSD)
- `MAX_POSITION_SIZE` - Maximum position size (default: 1000.0)
- `MAX_LEVERAGE` - Maximum leverage (default: 10)
- `RISK_PER_TRADE` - Risk per trade (default: 0.02)
- `DEFAULT_TIMEFRAME` - Default timeframe (default: 1h)

## Setting Up Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret listed above

## Manual Deployment

To trigger deployment manually:

1. Go to **Actions** tab in your repository
2. Select **Deploy to AWS** workflow
3. Click **Run workflow**
4. Choose environment (production or staging)
5. Click **Run workflow**

## Workflow Steps

### CI Workflow
1. Checkout code
2. Set up Python 3.9
3. Install dependencies
4. Run tests
5. Upload coverage
6. Lint code

### Deploy Workflow
1. Run tests and linting
2. Configure AWS credentials
3. Set up Terraform
4. Initialize Terraform
5. Validate Terraform configuration
6. Create terraform.tfvars
7. Plan Terraform changes
8. Apply Terraform changes
9. Get instance information
10. Wait for instance to be ready
11. Deploy application code
12. Configure environment variables
13. Restart service
14. Verify deployment

## Troubleshooting

### Deployment Fails

1. **Check AWS credentials:**
   - Verify secrets are set correctly
   - Check IAM permissions

2. **Check SSH key:**
   - Verify `AWS_SSH_KEY_NAME` matches your AWS key pair
   - Verify `AWS_SSH_PRIVATE_KEY` is the correct private key

3. **Check Terraform:**
   - Review Terraform logs in Actions output
   - Verify terraform.tfvars is created correctly

4. **Check instance:**
   - Verify instance is running
   - Check CloudWatch logs

### Tests Fail

1. Check test output in Actions
2. Run tests locally: `pytest tests/`
3. Check Python version compatibility

### Linting Fails

1. Run formatting: `black .`
2. Sort imports: `isort .`
3. Fix linting issues: `flake8 .`

## Security Best Practices

1. **Never commit secrets:**
   - Use GitHub Secrets for all sensitive data
   - Use `.env` files locally (already in .gitignore)

2. **Use least privilege:**
   - Create IAM user with minimal permissions
   - Use separate IAM roles for different environments

3. **Rotate credentials:**
   - Regularly rotate AWS access keys
   - Update GitHub secrets when rotating

4. **Review deployments:**
   - Use manual approval for production
   - Review Terraform plans before applying

## Customization

### Change AWS Region

Edit `.github/workflows/deploy.yml`:
```yaml
env:
  AWS_REGION: us-east-1  # Change to your region
```

### Change Instance Type

Set secret `AWS_INSTANCE_TYPE` or edit workflow default.

### Add Pre-deployment Steps

Add steps before deployment job:
```yaml
- name: Your Custom Step
  run: |
    # Your commands here
```

## Monitoring

After deployment, monitor:
- GitHub Actions logs
- AWS CloudWatch logs
- EC2 instance status
- Application logs via SSH

## Cost Optimization

The workflow uses:
- Spot instances (configured in Terraform)
- t3.micro (free tier eligible)
- Minimal CloudWatch logging

Estimated cost: ~$3-6/month

