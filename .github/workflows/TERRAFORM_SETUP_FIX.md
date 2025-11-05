# Terraform Setup Fix for AggregateError

If you're encountering `AggregateError` with `hashicorp/setup-terraform@v3`, try these solutions:

## Solution 1: Update to v4 (Recommended)

The latest version of the action has better error handling:

```yaml
- name: Set up Terraform
  uses: hashicorp/setup-terraform@v4
  with:
    terraform_version: ${{ env.TF_VERSION }}
    terraform_wrapper: false
```

## Solution 2: Explicitly Disable Terraform Cloud

If you're not using Terraform Cloud, explicitly disable it:

```yaml
- name: Set up Terraform
  uses: hashicorp/setup-terraform@v3
  with:
    terraform_version: ${{ env.TF_VERSION }}
    terraform_wrapper: false
  env:
    TF_TOKEN_app_terraform_io: ""
```

## Solution 3: Use Specific Version Format

Ensure the version format is correct (without 'v' prefix):

```yaml
env:
  TF_VERSION: "1.5.0"  # Not "v1.5.0"
```

## Solution 4: Add Error Handling

Add continue-on-error temporarily to debug:

```yaml
- name: Set up Terraform
  uses: hashicorp/setup-terraform@v3
  continue-on-error: true
  with:
    terraform_version: ${{ env.TF_VERSION }}
    terraform_wrapper: false

- name: Check Terraform installation
  run: terraform version
```

## Common Causes

1. **Terraform Cloud credentials** - If `TF_TOKEN_app_terraform_io` is set but invalid
2. **Network issues** - GitHub Actions unable to download Terraform
3. **Version format** - Invalid version string format
4. **Action version** - Bug in specific action version

## Current Configuration

The workflow currently uses:
- `terraform_version: ${{ env.TF_VERSION }}` (1.5.0)
- `terraform_wrapper: false`
- No Terraform Cloud configuration

This should work. If errors persist, try updating to `@v4` or check GitHub Actions logs for more details.

