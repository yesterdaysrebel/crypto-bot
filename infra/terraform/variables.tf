# Variables file (can be merged with main.tf)

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "use_spot_instance" {
  description = "Use spot instances for cost savings (up to 90% cheaper)"
  type        = bool
  default     = true
}

variable "spot_price" {
  description = "Maximum spot price (leave empty for on-demand price)"
  type        = string
  default     = ""
}

variable "spot_type" {
  description = "Spot instance type: 'one-time' (terminated when interrupted) or 'persistent' (auto-restarts when interrupted)"
  type        = string
  default     = "one-time"
  
  validation {
    condition     = contains(["one-time", "persistent"], var.spot_type)
    error_message = "spot_type must be either 'one-time' or 'persistent'."
  }
}

variable "ssh_key_name" {
  description = "AWS SSH key pair name (required)"
  type        = string
  
  validation {
    condition     = length(var.ssh_key_name) > 0 && var.ssh_key_name != ""
    error_message = "SSH key name cannot be empty. Please provide a valid AWS key pair name."
  }
}

variable "create_vpc" {
  description = "Create a new VPC or use default VPC"
  type        = bool
  default     = false  # Use default VPC for cost savings
}

variable "vpc_cidr" {
  description = "CIDR block for VPC (if creating new VPC)"
  type        = string
  default     = "10.0.0.0/16"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed for SSH access (use your IP for security)"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict this in production!
}

variable "enable_public_ip" {
  description = "Assign public IP to instance"
  type        = bool
  default     = true
}

variable "use_elastic_ip" {
  description = "Allocate and assign Elastic IP for static IP address"
  type        = bool
  default     = false  # Costs extra, disable for cost optimization
}

variable "ebs_volume_size" {
  description = "Size of EBS root volume in GB"
  type        = number
  default     = 8  # Minimum for Amazon Linux
}

variable "ebs_volume_type" {
  description = "EBS volume type (gp3 is cheapest and fastest)"
  type        = string
  default     = "gp3"
}

variable "ebs_encrypted" {
  description = "Enable encryption for EBS volumes"
  type        = bool
  default     = true
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring (costs extra)"
  type        = bool
  default     = false
}

variable "enable_termination_protection" {
  description = "Enable termination protection for instance"
  type        = bool
  default     = false  # Disable for spot instances
}

variable "backup_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 7  # Cost optimization
}

variable "environment" {
  description = "Environment name (for tagging)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name (for tagging)"
  type        = string
  default     = "trading-bot"
}
