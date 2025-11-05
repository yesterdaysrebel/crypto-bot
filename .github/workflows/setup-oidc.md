# Setting Up OIDC Authentication for GitHub Actions

This guide explains how to set up OpenID Connect (OIDC) authentication between GitHub Actions and AWS, which is the **recommended and secure way** to authenticate without storing long-lived credentials.

## Why OIDC?

- ✅ **No long-lived credentials** - No access keys to manage or rotate
- ✅ **Short-lived tokens** - Automatic token expiration
- ✅ **Scoped permissions** - Can restrict to specific repositories/workflows
- ✅ **AWS best practice** - Recommended by AWS security guidelines
- ✅ **Audit trail** - Better visibility in CloudTrail

## Prerequisites

- AWS CLI installed and configured (for setup)
- AWS account with appropriate permissions
- GitHub repository with Actions enabled

## Step-by-Step Setup

You can set up OIDC using either the AWS Console (easier) or AWS CLI. Choose your preferred method:

### Option A: Using AWS Console (Recommended)

### Step 1: Create OIDC Identity Provider in AWS Console

1. **Sign in to AWS Console**
   - Go to https://console.aws.amazon.com/
   - Sign in with your AWS account

2. **Navigate to IAM**
   - Search for "IAM" in the top search bar
   - Click on "IAM" service

3. **Create Identity Provider**
   - In the left sidebar, click **"Identity providers"** (under "Access management")
   - Click **"Add provider"** button

4. **Configure Provider**
   - **Provider type**: Select **"OpenID Connect"**
   - **Provider URL**: Enter `https://token.actions.githubusercontent.com`
   - **Audience**: Enter `sts.amazonaws.com`
   - Click **"Add provider"**

5. **Verify Provider**
   - You should see the provider listed in "Identity providers"
   - Note the **Provider ARN** (you'll need this for the IAM role)

**Note**: The thumbprint should be automatically detected. If not, you may need to add it manually:
   - Thumbprint: `6938fd4d98bab03faadb97b34396831e3780aea1`

### Step 2: Create IAM Role for GitHub Actions (Console)

1. **Navigate to Roles**
   - In IAM, click **"Roles"** in the left sidebar
   - Click **"Create role"**

2. **Select Trusted Entity Type**
   - Select **"Web identity"**
   - **Identity provider**: Select `token.actions.githubusercontent.com` (the OIDC provider you just created)
   - **Audience**: Should be pre-filled as `sts.amazonaws.com`
   - Click **"Next"**

3. **Configure Permissions**
   - You can either:
     - **Option A**: Attach existing policies (e.g., `AmazonEC2FullAccess`, `IAMFullAccess`)
     - **Option B**: Create a custom policy (recommended for minimal permissions)
   
   **For Custom Policy (Recommended)**:
   - Click **"Create policy"** (opens in new tab)
   - Click **"JSON"** tab
   - Paste the policy JSON from "Step 3: Create Custom IAM Policy" below
   - Click **"Next"**
   - Name: `GitHubActions-TradingBotDeploy`
   - Description: `Policy for GitHub Actions to deploy trading bot`
   - Click **"Create policy"**
   - Go back to role creation tab, refresh, and select your new policy

4. **Add Conditions (Restrict Access)**
   - Click **"Add condition"** to restrict access
   - **Condition key**: Select `token.actions.githubusercontent.com:sub`
   - **Qualifier**: Leave empty
   - **Operator**: Select `StringLike`
   - **Value**: Enter `repo:YOUR_GITHUB_USERNAME/crypto-bot:*`
     - Replace `YOUR_GITHUB_USERNAME` with your GitHub username or organization
     - For specific branch only: `repo:YOUR_GITHUB_USERNAME/crypto-bot:ref:refs/heads/main`
   - Click **"Next"**

5. **Name and Review**
   - **Role name**: `GitHubActions-DeployRole`
   - **Description**: `Role for GitHub Actions to deploy trading bot`
   - Review the settings
   - Click **"Create role"**

6. **Get Role ARN**
   - Click on the role you just created
   - Copy the **Role ARN** (looks like: `arn:aws:iam::123456789012:role/GitHubActions-DeployRole`)
   - You'll need this for GitHub Secrets

---

### Option B: Using AWS CLI

### Step 1: Create OIDC Identity Provider in AWS

```bash
# Get your GitHub organization/repository info
GITHUB_ORG="your-github-username-or-org"
REPO_NAME="crypto-bot"

# Create OIDC provider
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  --tags Key=Name,Value=GitHubActions-OIDC
```

### Step 2: Create IAM Role for GitHub Actions

Create a trust policy file `trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/crypto-bot:*"
        }
      }
    }
  ]
}
```

**Replace:**
- `YOUR_ACCOUNT_ID` with your AWS account ID
- `YOUR_GITHUB_ORG` with your GitHub username or organization

**For more restrictive access (specific branch):**
```json
"token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/crypto-bot:ref:refs/heads/main"
```

Create the role:

```bash
# Create role with trust policy
aws iam create-role \
  --role-name GitHubActions-DeployRole \
  --assume-role-policy-document file://trust-policy.json \
  --description "Role for GitHub Actions to deploy trading bot"

# Attach policies (adjust as needed)
aws iam attach-role-policy \
  --role-name GitHubActions-DeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess

aws iam attach-role-policy \
  --role-name GitHubActions-DeployRole \
  --policy-arn arn:aws:iam::aws:policy/IAMFullAccess

# Or create a custom policy with minimal permissions (recommended)
```

### Step 3: Create Custom IAM Policy (Recommended)

Create a custom policy file `deploy-policy.json` with minimal required permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "iam:PassRole",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:TagLogGroup",
        "logs:PutRetentionPolicy"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/trading-bot/*"
    }
  ]
}
```

Create and attach:

```bash
aws iam create-policy \
  --policy-name GitHubActions-TradingBotDeploy \
  --policy-document file://deploy-policy.json

# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach to role
aws iam attach-role-policy \
  --role-name GitHubActions-DeployRole \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/GitHubActions-TradingBotDeploy
```

### Step 4: Get Role ARN

**If using Console:**
- The Role ARN is displayed on the role details page
- Format: `arn:aws:iam::YOUR_ACCOUNT_ID:role/GitHubActions-DeployRole`

**If using CLI:**
```bash
aws iam get-role --role-name GitHubActions-DeployRole --query Role.Arn --output text
```

This will output something like:
```
arn:aws:iam::123456789012:role/GitHubActions-DeployRole
```

### Step 5: Add Role ARN to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `AWS_ROLE_ARN`
5. Value: The ARN from Step 4 (e.g., `arn:aws:iam::123456789012:role/GitHubActions-DeployRole`)
6. Click **Add secret**

### Step 6: Update GitHub Actions Workflow

The workflow is already configured to use OIDC! Just ensure you have the `AWS_ROLE_ARN` secret set.

## Verification

### Test the Setup

1. Push a commit to trigger the workflow
2. Check GitHub Actions logs
3. Verify it can assume the role successfully

### View in CloudTrail

```bash
# Check recent AssumeRoleWithWebIdentity calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRoleWithWebIdentity \
  --max-results 10
```

## Security Best Practices

### 1. Restrict by Repository

Update the trust policy condition to only allow specific repositories:

```json
"Condition": {
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
  },
  "StringLike": {
    "token.actions.githubusercontent.com:sub": [
      "repo:YOUR_ORG/crypto-bot:ref:refs/heads/main",
      "repo:YOUR_ORG/crypto-bot:pull_request"
    ]
  }
}
```

### 2. Restrict by Environment

Use GitHub Environments with protection rules:

```yaml
# In workflow file
environment:
  name: production
  url: https://your-instance-url
```

### 3. Use Separate Roles for Different Environments

Create separate roles:
- `GitHubActions-DeployRole-Prod`
- `GitHubActions-DeployRole-Staging`

### 4. Minimal Permissions

Only grant the permissions needed for deployment:
- EC2 instance management
- IAM role passing (for EC2 instance profile)
- CloudWatch logs
- S3 (if using for deployment)

### 5. Enable MFA (Optional)

For additional security, require MFA in the trust policy:

```json
"Condition": {
  "Bool": {
    "aws:MultiFactorAuthPresent": "true"
  }
}
```

## Troubleshooting

### Error: "Not authorized to perform sts:AssumeRoleWithWebIdentity"

**Solution:**
1. Verify OIDC provider is created correctly
2. Check trust policy conditions match your repository
3. Verify role ARN in GitHub secrets is correct

### Error: "The requested identity provider token does not match"

**Solution:**
- Check OIDC provider thumbprint is correct
- Verify the OIDC provider URL matches exactly

### Error: "Access denied" when deploying

**Solution:**
1. Check IAM policies attached to the role
2. Verify policies have necessary permissions
3. Check CloudTrail logs for specific denied actions

## Cleanup

To remove OIDC setup:

```bash
# Detach policies
aws iam detach-role-policy \
  --role-name GitHubActions-DeployRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess

# Delete role
aws iam delete-role --role-name GitHubActions-DeployRole

# Delete OIDC provider (if not used elsewhere)
aws iam delete-open-id-connect-provider \
  --open-id-connect-provider-arn arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com
```

## Additional Resources

- [AWS Documentation: Creating OpenID Connect identity providers](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [GitHub Documentation: Security hardening with OpenID Connect](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [AWS Actions: Configure AWS Credentials](https://github.com/aws-actions/configure-aws-credentials)

