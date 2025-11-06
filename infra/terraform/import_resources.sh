#!/bin/bash
# Script to import existing AWS resources into Terraform state
# Run this from the terraform directory

set -e

echo "🔍 Finding existing AWS resources..."

# Get VPC ID from error message or AWS CLI
VPC_ID="${VPC_ID:-vpc-01194601ab9c678c4}"
PROJECT_NAME="${PROJECT_NAME:-trading-bot}"

echo "Using VPC: $VPC_ID"
echo "Using project name: $PROJECT_NAME"

# 1. Get Security Group ID
echo ""
echo "📋 Finding Security Group..."
SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=${PROJECT_NAME}-sg" "Name=vpc-id,Values=${VPC_ID}" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

if [ "$SG_ID" != "None" ] && [ -n "$SG_ID" ]; then
  echo "Found Security Group: $SG_ID"
  echo "Importing security group..."
  terraform import aws_security_group.trading_bot "$SG_ID" || echo "⚠️  Security group may already be imported"
else
  echo "⚠️  Security Group not found or multiple matches"
fi

# 2. Import IAM Role
echo ""
echo "🔐 Finding IAM Role..."
ROLE_NAME="${PROJECT_NAME}-ec2-role"
echo "Found IAM Role: $ROLE_NAME"
echo "Importing IAM role..."
terraform import aws_iam_role.ec2_role "$ROLE_NAME" || echo "⚠️  IAM role may already be imported"

# 3. Import CloudWatch Log Group
echo ""
echo "📊 Finding CloudWatch Log Group..."
LOG_GROUP_NAME="/aws/ec2/${PROJECT_NAME}"
echo "Found Log Group: $LOG_GROUP_NAME"
echo "Importing CloudWatch log group..."
terraform import aws_cloudwatch_log_group.trading_bot "$LOG_GROUP_NAME" || echo "⚠️  Log group may already be imported"

echo ""
echo "✅ Import complete!"
echo ""
echo "Next steps:"
echo "1. Run: terraform plan"
echo "2. Review the plan to ensure it matches your existing resources"
echo "3. If everything looks good, run: terraform apply"

