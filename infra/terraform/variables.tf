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

variable "ssh_key_name" {
  description = "AWS SSH key pair name"
  type        = string
  default     = ""
}

