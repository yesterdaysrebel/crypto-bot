#!/bin/bash
# Deployment script for AWS

set -e

echo "Deploying trading bot to AWS..."

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "Terraform is not installed. Please install it first."
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Navigate to terraform directory
cd "$(dirname "$0")/terraform"

# Initialize Terraform
echo "Initializing Terraform..."
terraform init

# Plan deployment
echo "Planning deployment..."
terraform plan

# Apply deployment
read -p "Do you want to proceed with deployment? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Applying Terraform configuration..."
    terraform apply -auto-approve
    
    echo "Deployment completed!"
    echo "Instance ID: $(terraform output -raw instance_id)"
    echo "Public IP: $(terraform output -raw instance_public_ip)"
    echo ""
    echo "To connect via SSH:"
    echo "$(terraform output -raw ssh_command)"
else
    echo "Deployment cancelled."
fi

