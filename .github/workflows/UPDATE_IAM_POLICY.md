# Update IAM Policy for CloudWatch Logs

The GitHub Actions IAM role needs CloudWatch Logs permissions. Follow these steps to add them.

## Quick Fix: Update IAM Policy

### Option 1: Using AWS Console (Recommended)

1. **Go to AWS IAM Console**
   - Navigate to: https://console.aws.amazon.com/iam/
   - Click **"Roles"** in the left sidebar
   - Search for and click on **`GitHubActions-TradingBotDeploy`** (or `GitHubActions-DeployRole`)

2. **Find the Policy**
   - Scroll down to **"Permissions policies"**
   - Click on the policy name (e.g., `GitHubActions-TradingBotDeploy`)

3. **Edit the Policy**
   - Click **"Edit"** button
   - Click **"JSON"** tab
   - Add CloudWatch Logs permissions to the policy:

   Find the statement with `logs:CreateLogGroup` (if it exists) or add a new statement:

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

4. **Save Changes**
   - Click **"Next"** → **"Save changes"**

5. **Re-run GitHub Actions**
   - Go to your GitHub repository
   - Navigate to **Actions** tab
   - Re-run the failed workflow or push a new commit

### Option 2: Using AWS CLI

1. **Get your account ID**
   ```bash
   ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   ```

2. **Create updated policy file** (`deploy-policy-updated.json`):
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

3. **Update the policy**
   ```bash
   # Get the policy ARN
   POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/GitHubActions-TradingBotDeploy"
   
   # Create new policy version (this updates the policy)
   aws iam create-policy-version \
     --policy-arn "${POLICY_ARN}" \
     --policy-document file://deploy-policy-updated.json \
     --set-as-default
   ```

4. **Re-run GitHub Actions workflow**

## Required CloudWatch Logs Permissions

The following permissions are needed for Terraform to create CloudWatch log groups:

- `logs:CreateLogGroup` - Create log groups
- `logs:DescribeLogGroups` - List/describe log groups (for checking if they exist)
- `logs:TagLogGroup` - Add tags to log groups
- `logs:PutRetentionPolicy` - Set retention policy
- `logs:CreateLogStream` - Create log streams (for EC2 instances)
- `logs:PutLogEvents` - Write log events (for EC2 instances)

## Verification

After updating the policy, verify it worked:

1. **Check policy in AWS Console**
   - Go to IAM → Policies → Find your policy
   - Verify it includes the CloudWatch Logs permissions

2. **Re-run GitHub Actions**
   - The Terraform deployment should now succeed
   - The `aws_cloudwatch_log_group.trading_bot` resource should be created

## Alternative: Use AWS Managed Policy

If you prefer using AWS managed policies, you can attach:

```bash
aws iam attach-role-policy \
  --role-name GitHubActions-TradingBotDeploy \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
```

**Note:** This grants full CloudWatch Logs access. For production, use the custom policy with minimal permissions above.

