# Troubleshooting GitHub Actions Deployment

## Common Errors and Solutions

### Error: "Credentials could not be loaded"

```
Error: Credentials could not be loaded, please check your action inputs: 
Could not load credentials from any providers
```

**Causes and Solutions:**

#### 1. Missing AWS_ROLE_ARN Secret

**Problem:** The `AWS_ROLE_ARN` secret is not set in GitHub Secrets.

**Solution:**
1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Check if `AWS_ROLE_ARN` exists
4. If not, add it:
   - Click "New repository secret"
   - Name: `AWS_ROLE_ARN`
   - Value: Your IAM Role ARN (e.g., `arn:aws:iam::123456789012:role/GitHubActions-DeployRole`)
   - Click "Add secret"

#### 2. OIDC Provider Not Created

**Problem:** The OIDC identity provider doesn't exist in AWS IAM.

**Solution:**
1. Go to AWS Console → IAM → Identity providers
2. Check if `token.actions.githubusercontent.com` exists
3. If not, create it (see [setup-oidc.md](setup-oidc.md))
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`

#### 3. IAM Role Trust Policy Issues

**Problem:** The IAM role's trust policy doesn't allow GitHub Actions to assume it.

**Solution:**
1. Go to AWS Console → IAM → Roles
2. Click on `GitHubActions-DeployRole`
3. Go to "Trust relationships" tab
4. Verify the trust policy includes:
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
             "token.actions.githubusercontent.com:sub": "repo:YOUR_USERNAME/crypto-bot:*"
           }
         }
       }
     ]
   }
   ```
5. Update the condition to match your GitHub username/repository

#### 4. Repository Name Mismatch

**Problem:** The trust policy condition doesn't match your repository name exactly.

**Solution:**
- Check your GitHub repository name (case-sensitive)
- Update the trust policy condition:
  ```json
  "token.actions.githubusercontent.com:sub": "repo:YOUR_ACTUAL_USERNAME/YOUR_ACTUAL_REPO_NAME:*"
  ```
- For specific branch: `repo:USERNAME/REPO:ref:refs/heads/main`

#### 5. Missing Permissions in Workflow

**Problem:** The workflow doesn't have `id-token: write` permission.

**Solution:**
Check that your workflow has:
```yaml
permissions:
  id-token: write  # Required for OIDC
  contents: read   # Required for checkout
```

### Error: "User is not authorized to perform: sts:AssumeRoleWithWebIdentity"

**Problem:** The IAM role trust policy doesn't allow the GitHub Actions workflow to assume the role.

**Solutions:**

1. **Check Trust Policy Condition:**
   - Verify the condition matches your repository exactly
   - Repository name is case-sensitive
   - Format: `repo:USERNAME/REPO_NAME:*`

2. **Check OIDC Provider:**
   - Verify the OIDC provider exists
   - Check the provider ARN matches the trust policy

3. **Check IAM Role:**
   - Verify the role exists
   - Check the role ARN in GitHub secrets matches

### Error: "The requested identity provider token does not match"

**Problem:** The OIDC provider configuration is incorrect.

**Solution:**
1. Go to IAM → Identity providers
2. Click on `token.actions.githubusercontent.com`
3. Verify:
   - **Provider URL**: Exactly `https://token.actions.githubusercontent.com`
   - **Audience**: Exactly `sts.amazonaws.com`
   - **Thumbprint**: Should be `6938fd4d98bab03faadb97b34396831e3780aea1`

### Error: "Access Denied" when deploying

**Problem:** The IAM role doesn't have necessary permissions.

**Solution:**
1. Go to IAM → Roles → `GitHubActions-DeployRole`
2. Check "Permissions" tab
3. Ensure the role has:
   - `AmazonEC2FullAccess` (or custom policy with EC2 permissions)
   - `IAMFullAccess` (for passing roles to EC2 instances)
   - Or create a custom policy with minimal required permissions

### Debugging Steps

1. **Check GitHub Secrets:**
   ```bash
   # In workflow, add debug step:
   - name: Debug Secrets
     run: |
       echo "Role ARN exists: ${{ secrets.AWS_ROLE_ARN != '' }}"
       echo "Role ARN: ${{ secrets.AWS_ROLE_ARN }}"
   ```

2. **Check AWS CloudTrail:**
   - Go to AWS Console → CloudTrail → Event history
   - Filter by: `AssumeRoleWithWebIdentity`
   - Check for errors or denied attempts

3. **Check Workflow Logs:**
   - Go to GitHub Actions → Select workflow run
   - Expand "Configure AWS credentials" step
   - Look for detailed error messages

4. **Verify OIDC Setup:**
   ```bash
   # Check if OIDC provider exists
   aws iam list-open-id-connect-providers
   
   # Check role trust policy
   aws iam get-role --role-name GitHubActions-DeployRole --query Role.AssumeRolePolicyDocument
   ```

### Quick Fix Checklist

- [ ] `AWS_ROLE_ARN` secret is set in GitHub
- [ ] OIDC provider exists in AWS IAM
- [ ] IAM role exists and has correct trust policy
- [ ] Trust policy condition matches repository name exactly
- [ ] IAM role has necessary permissions attached
- [ ] Workflow has `id-token: write` permission
- [ ] Repository name in trust policy is case-sensitive and correct

### Testing OIDC Setup

Add this test step to your workflow:

```yaml
- name: Test AWS Connection
  run: |
    aws sts get-caller-identity
    aws ec2 describe-instances --max-items 1
```

If this works, OIDC is configured correctly!

### Getting Help

If you're still having issues:

1. Check CloudTrail logs for specific error messages
2. Verify all steps in [setup-oidc.md](setup-oidc.md)
3. Check GitHub Actions logs for detailed error messages
4. Verify the IAM role ARN format is correct

### Common Mistakes

1. **Incorrect Role ARN format:**
   - ❌ Wrong: `GitHubActions-DeployRole`
   - ✅ Correct: `arn:aws:iam::123456789012:role/GitHubActions-DeployRole`

2. **Repository name mismatch:**
   - ❌ Wrong: `repo:username/Crypto-Bot:*` (if repo is `crypto-bot`)
   - ✅ Correct: `repo:username/crypto-bot:*` (case-sensitive)

3. **Missing OIDC provider:**
   - Must create OIDC provider before creating IAM role

4. **Wrong audience:**
   - Must be exactly `sts.amazonaws.com`

