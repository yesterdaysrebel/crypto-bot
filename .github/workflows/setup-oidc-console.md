# Quick Guide: OIDC Setup via AWS Console

This is a simplified, visual guide for setting up OIDC using the AWS Console.

## Prerequisites

- AWS Console access
- IAM permissions to create identity providers and roles
- Your GitHub username or organization name

## Step 1: Create OIDC Identity Provider

1. **Go to AWS Console** → Search for "IAM" → Click "IAM"

2. **Left sidebar** → Click **"Identity providers"** (under "Access management")

3. **Click "Add provider"** button

4. **Configure:**
   ```
   Provider type: OpenID Connect
   Provider URL: https://token.actions.githubusercontent.com
   Audience: sts.amazonaws.com
   ```

5. **Click "Add provider"**

6. **Verify** - You should see the provider listed with the URL above

## Step 2: Create IAM Role

1. **In IAM** → Click **"Roles"** (left sidebar) → **"Create role"**

2. **Select trusted entity type:**
   - Select **"Web identity"**
   - **Identity provider**: Choose `token.actions.githubusercontent.com`
   - **Audience**: Should show `sts.amazonaws.com`
   - Click **"Next"**

3. **Add conditions** (IMPORTANT - Restrict access):
   - Click **"Add condition"**
   - **Condition key**: Select `token.actions.githubusercontent.com:sub`
   - **Operator**: Select `StringLike`
   - **Value**: Enter `repo:YOUR_GITHUB_USERNAME/crypto-bot:*`
     - Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username
     - Example: `repo:john-doe/crypto-bot:*`
     - For specific branch: `repo:john-doe/crypto-bot:ref:refs/heads/main`
   - Click **"Next"**

4. **Attach permissions policy:**
   - **Option A (Quick)**: Search and select:
     - `AmazonEC2FullAccess`
     - `IAMFullAccess` (for passing roles to EC2)
   - **Option B (Recommended)**: Create custom policy:
     - Click **"Create policy"** (opens new tab)
     - Go to **"JSON"** tab
     - Paste this policy:
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
             "logs:PutLogEvents"
           ],
           "Resource": "*"
         }
       ]
     }
     ```
     - Click **"Next"** → Name: `GitHubActions-TradingBotDeploy`
     - Click **"Create policy"**
     - Go back to role creation tab, refresh, search for your policy
     - Select your custom policy

5. **Name and description:**
   - **Role name**: `GitHubActions-DeployRole`
   - **Description**: `Role for GitHub Actions to deploy trading bot`
   - Click **"Create role"**

## Step 3: Get Role ARN

1. **Click on the role** you just created (`GitHubActions-DeployRole`)

2. **Copy the Role ARN** from the top of the page
   - Format: `arn:aws:iam::123456789012:role/GitHubActions-DeployRole`
   - You'll need this for GitHub Secrets

## Step 4: Add to GitHub Secrets

1. **Go to your GitHub repository**
   - Settings → Secrets and variables → Actions

2. **Click "New repository secret"**

3. **Add:**
   - **Name**: `AWS_ROLE_ARN`
   - **Value**: Paste the Role ARN from Step 3
   - Click **"Add secret"**

## Step 5: Test It

1. **Push a commit** to trigger the workflow, or
2. **Go to Actions tab** → Select "Deploy to AWS" → "Run workflow"

3. **Check the workflow logs** - It should successfully assume the role

## Common Issues

### "Not authorized to perform sts:AssumeRoleWithWebIdentity"

**Fix:**
- Check the condition value matches your GitHub username exactly
- Verify the OIDC provider URL is correct
- Ensure the role ARN includes the full ARN (not just the role name)

### "The requested identity provider token does not match"

**Fix:**
- Verify the OIDC provider is created correctly
- Check the provider URL is exactly: `https://token.actions.githubusercontent.com`
- Check the audience is exactly: `sts.amazonaws.com`

### Role exists but can't assume it

**Fix:**
- Check the trust policy conditions
- Verify the repository name matches exactly (case-sensitive)
- Check IAM permissions are attached to the role

## Verification

After setup, you can verify in CloudTrail:

1. **AWS Console** → Search "CloudTrail" → Click "Event history"

2. **Filter by:**
   - Event name: `AssumeRoleWithWebIdentity`
   - Time range: Last 24 hours

3. **Check** the events show successful assumptions from GitHub Actions

## Security Tips

1. **Restrict by branch:**
   - Use `repo:USERNAME/crypto-bot:ref:refs/heads/main` for main branch only

2. **Use separate roles:**
   - Create `GitHubActions-DeployRole-Prod` for production
   - Create `GitHubActions-DeployRole-Staging` for staging

3. **Minimal permissions:**
   - Use custom policies instead of full access
   - Only grant what's needed for deployment

4. **Monitor access:**
   - Check CloudTrail regularly
   - Set up CloudWatch alarms for role assumptions

## Summary

✅ OIDC Provider created: `token.actions.githubusercontent.com`  
✅ IAM Role created: `GitHubActions-DeployRole`  
✅ Role ARN added to GitHub Secrets: `AWS_ROLE_ARN`  
✅ Ready to deploy! 🚀

