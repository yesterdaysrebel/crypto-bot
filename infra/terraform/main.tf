# Terraform configuration for AWS deployment
# Optimized for minimal cost

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"  # Mumbai for India
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"  # Free tier eligible, lowest cost
}

variable "use_spot_instance" {
  description = "Use spot instances for cost savings"
  type        = bool
  default     = true
}

variable "spot_price" {
  description = "Maximum spot price (empty for on-demand price)"
  type        = string
  default     = ""
}

# Data sources
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# VPC and networking (using default VPC to save costs)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security group
resource "aws_security_group" "trading_bot" {
  name        = "trading-bot-sg"
  description = "Security group for trading bot EC2 instance"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Restrict this in production
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "trading-bot-sg"
  }
}

# IAM role for EC2
resource "aws_iam_role" "ec2_role" {
  name = "trading-bot-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ec2_policy" {
  name = "trading-bot-ec2-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "trading-bot-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# EC2 instance (using spot if enabled)
resource "aws_instance" "trading_bot" {
  count = var.use_spot_instance ? 0 : 1

  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type

  vpc_security_group_ids = [aws_security_group.trading_bot.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  user_data = file("${path.module}/user_data.sh")

  tags = {
    Name = "trading-bot"
  }

  # Cost optimization: disable detailed monitoring
  monitoring = false
}

# Spot instance request (if using spot)
resource "aws_spot_instance_request" "trading_bot" {
  count = var.use_spot_instance ? 1 : 0

  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type
  spot_price    = var.spot_price != "" ? var.spot_price : null
  spot_type     = "one-time"
  wait_for_fulfillment = true

  vpc_security_group_ids = [aws_security_group.trading_bot.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  user_data = file("${path.module}/user_data.sh")

  tags = {
    Name = "trading-bot-spot"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "trading_bot" {
  name              = "/aws/ec2/trading-bot"
  retention_in_days = 7  # Keep logs for 7 days to save costs
}

# CloudWatch Alarm for instance status
resource "aws_cloudwatch_metric_alarm" "instance_status" {
  count = var.use_spot_instance ? 1 : 1

  alarm_name          = "trading-bot-instance-status"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "0"
  alarm_description   = "This metric monitors ec2 instance status"
  
  dimensions = {
    InstanceId = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].spot_instance_id : aws_instance.trading_bot[0].id
  }

  tags = {
    Name = "trading-bot-alarm"
  }
}

# Outputs
output "instance_id" {
  value = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].spot_instance_id : aws_instance.trading_bot[0].id
}

output "instance_public_ip" {
  value = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].public_ip : aws_instance.trading_bot[0].public_ip
}

