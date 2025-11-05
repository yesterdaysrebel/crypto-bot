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

# Note: Additional variables are defined in variables.tf
# Variables defined here for backward compatibility
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

variable "ssh_key_name" {
  description = "AWS SSH key pair name (required)"
  type        = string
}

variable "create_vpc" {
  description = "Create a new VPC or use default VPC"
  type        = bool
  default     = false
}

variable "vpc_cidr" {
  description = "CIDR block for VPC (if creating new VPC)"
  type        = string
  default     = "10.0.0.0/16"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_public_ip" {
  description = "Assign public IP to instance"
  type        = bool
  default     = true
}

variable "use_elastic_ip" {
  description = "Allocate and assign Elastic IP"
  type        = bool
  default     = false
}

variable "ebs_volume_size" {
  description = "Size of EBS root volume in GB"
  type        = number
  default     = 8
}

variable "ebs_volume_type" {
  description = "EBS volume type"
  type        = string
  default     = "gp3"
}

variable "ebs_encrypted" {
  description = "Enable encryption for EBS volumes"
  type        = bool
  default     = true
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = false
}

variable "enable_termination_protection" {
  description = "Enable termination protection"
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 7
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

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC and networking configuration
# Option 1: Create new VPC (more secure, more cost)
# Option 2: Use default VPC (simpler, less cost)

# Custom VPC (if create_vpc = true)
resource "aws_vpc" "trading_bot" {
  count = var.create_vpc ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
    Environment = var.environment
    Project = var.project_name
  }
}

# Internet Gateway (if creating VPC)
resource "aws_internet_gateway" "trading_bot" {
  count = var.create_vpc ? 1 : 0

  vpc_id = aws_vpc.trading_bot[0].id

  tags = {
    Name = "${var.project_name}-igw"
    Environment = var.environment
    Project = var.project_name
  }
}

# Public Subnet (if creating VPC)
resource "aws_subnet" "public" {
  count = var.create_vpc ? 1 : 0

  vpc_id                  = aws_vpc.trading_bot[0].id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 0)  # 10.0.0.0/24
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = var.enable_public_ip

  tags = {
    Name = "${var.project_name}-public-subnet"
    Type = "public"
    Environment = var.environment
    Project = var.project_name
  }
}

# Route Table for public subnet (if creating VPC)
resource "aws_route_table" "public" {
  count = var.create_vpc ? 1 : 0

  vpc_id = aws_vpc.trading_bot[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.trading_bot[0].id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
    Environment = var.environment
    Project = var.project_name
  }
}

# Route Table Association (if creating VPC)
resource "aws_route_table_association" "public" {
  count = var.create_vpc ? 1 : 0

  subnet_id      = aws_subnet.public[0].id
  route_table_id = aws_route_table.public[0].id
}

# Use default VPC (if not creating new VPC)
data "aws_vpc" "default" {
  count   = var.create_vpc ? 0 : 1
  default = true
}

# Get default subnets (if using default VPC)
data "aws_subnets" "default" {
  count = var.create_vpc ? 0 : 1
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
}

# Get first available subnet (if using default VPC)
data "aws_subnet" "selected" {
  count = var.create_vpc ? 0 : 1
  id    = tolist(data.aws_subnets.default[0].ids)[0]
}

# Security group with optimal configuration
resource "aws_security_group" "trading_bot" {
  name        = "${var.project_name}-sg"
  description = "Security group for trading bot EC2 instance"
  vpc_id      = var.create_vpc ? aws_vpc.trading_bot[0].id : data.aws_vpc.default[0].id

  # SSH access (restricted to specific CIDR blocks)
  ingress {
    description = "SSH from allowed IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr
  }

  # HTTPS outbound (for API calls)
  egress {
    description = "HTTPS outbound"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP outbound (for API calls if needed)
  egress {
    description = "HTTP outbound"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # DNS outbound
  egress {
    description = "DNS outbound"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # NTP outbound (for time synchronization)
  egress {
    description = "NTP outbound"
    from_port   = 123
    to_port     = 123
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
    Environment = var.environment
    Project = var.project_name
  }
}

# IAM role for EC2
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role"

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

  tags = {
    Name = "${var.project_name}-ec2-role"
    Environment = var.environment
    Project = var.project_name
  }
}

resource "aws_iam_role_policy" "ec2_policy" {
  name = "${var.project_name}-ec2-policy"
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
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/${var.project_name}/*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
  tags = {
    Name = "${var.project_name}-ec2-profile"
    Environment = var.environment
    Project = var.project_name
  }
}

# Elastic IP (if enabled)
resource "aws_eip" "trading_bot" {
  count = var.use_elastic_ip && !var.use_spot_instance ? 1 : 0

  domain = "vpc"
  tags = {
    Name = "${var.project_name}-eip"
    Environment = var.environment
    Project = var.project_name
  }

  depends_on = [aws_instance.trading_bot]
}

resource "aws_eip_association" "trading_bot" {
  count = var.use_elastic_ip && !var.use_spot_instance ? 1 : 0

  instance_id   = aws_instance.trading_bot[0].id
  allocation_id = aws_eip.trading_bot[0].id
}

# EC2 instance (using spot if enabled)
resource "aws_instance" "trading_bot" {
  count = var.use_spot_instance ? 0 : 1

  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type

  # Network configuration
  vpc_security_group_ids      = [aws_security_group.trading_bot.id]
  subnet_id                   = var.create_vpc ? aws_subnet.public[0].id : data.aws_subnet.selected[0].id
  associate_public_ip_address = var.enable_public_ip
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name

  # SSH key (required)
  key_name = var.ssh_key_name

  # User data script
  user_data = file("${path.module}/user_data.sh")

  # EBS root volume configuration
  root_block_device {
    volume_type           = var.ebs_volume_type
    volume_size           = var.ebs_volume_size
    encrypted             = var.ebs_encrypted
    delete_on_termination = true  # Don't keep volume after termination

    tags = {
      Name = "${var.project_name}-root-volume"
      Environment = var.environment
      Project = var.project_name
    }
  }

  # Enable detailed monitoring (optional, costs extra)
  monitoring = var.enable_detailed_monitoring

  # Termination protection (disable for spot instances)
  disable_api_termination = var.enable_termination_protection && !var.use_spot_instance

  # Metadata options (security best practices)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # Require IMDSv2 for security
    http_put_response_hop_limit = 1
  }

  tags = {
    Name = var.project_name
    Environment = var.environment
    Project = var.project_name
    ManagedBy = "Terraform"
    InstanceType = var.instance_type
  }
}

# Spot instance request (if using spot)
resource "aws_spot_instance_request" "trading_bot" {
  count = var.use_spot_instance ? 1 : 0

  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type
  spot_price           = var.spot_price != "" ? var.spot_price : null
  spot_type            = "one-time"
  wait_for_fulfillment = true

  # Network configuration
  vpc_security_group_ids      = [aws_security_group.trading_bot.id]
  subnet_id                   = var.create_vpc ? aws_subnet.public[0].id : data.aws_subnet.selected[0].id
  associate_public_ip_address = var.enable_public_ip
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name

  # SSH key (required)
  key_name = var.ssh_key_name

  # User data script
  user_data = file("${path.module}/user_data.sh")

  # EBS root volume configuration
  root_block_device {
    volume_type = var.ebs_volume_type
    volume_size = var.ebs_volume_size
    encrypted   = var.ebs_encrypted
    delete_on_termination = true
  }

  # Metadata options (security best practices)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # Require IMDSv2 for security
    http_put_response_hop_limit = 1
  }

  tags = {
    Name = "${var.project_name}-spot"
    Environment = var.environment
    Project = var.project_name
    ManagedBy = "Terraform"
    InstanceType = var.instance_type
    SpotInstance = "true"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "trading_bot" {
  name              = "/aws/ec2/${var.project_name}"
  retention_in_days = var.backup_retention_days

  tags = {
    Name = "${var.project_name}-logs"
    Environment = var.environment
    Project = var.project_name
  }
}

# CloudWatch Alarm for instance status
resource "aws_cloudwatch_metric_alarm" "instance_status" {
  alarm_name          = "${var.project_name}-instance-status"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "0"
  alarm_description   = "This metric monitors EC2 instance status check failures"
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].spot_instance_id : aws_instance.trading_bot[0].id
  }

  tags = {
    Name = "${var.project_name}-status-alarm"
    Environment = var.environment
    Project = var.project_name
  }
}

# CloudWatch Alarm for CPU utilization
resource "aws_cloudwatch_metric_alarm" "cpu_utilization" {
  alarm_name          = "${var.project_name}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors EC2 CPU utilization"
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].spot_instance_id : aws_instance.trading_bot[0].id
  }

  tags = {
    Name = "${var.project_name}-cpu-alarm"
    Environment = var.environment
    Project = var.project_name
  }
}

# CloudWatch Alarm for memory (if detailed monitoring enabled)
resource "aws_cloudwatch_metric_alarm" "memory_utilization" {
  count = var.enable_detailed_monitoring ? 1 : 0

  alarm_name          = "${var.project_name}-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "mem_used_percent"
  namespace           = "CWAgent"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors EC2 memory utilization"

  dimensions = {
    InstanceId = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].spot_instance_id : aws_instance.trading_bot[0].id
  }

  tags = {
    Name = "${var.project_name}-memory-alarm"
    Environment = var.environment
    Project = var.project_name
  }
}
