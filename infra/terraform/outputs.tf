# Outputs

output "instance_id" {
  description = "EC2 instance ID"
  value       = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].spot_instance_id : aws_instance.trading_bot[0].id
}

output "instance_public_ip" {
  description = "EC2 instance public IP (or Elastic IP if enabled)"
  value       = var.use_elastic_ip && !var.use_spot_instance ? aws_eip.trading_bot[0].public_ip : (var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].public_ip : aws_instance.trading_bot[0].public_ip)
}

output "instance_private_ip" {
  description = "EC2 instance private IP"
  value       = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].private_ip : aws_instance.trading_bot[0].private_ip
}

output "instance_public_dns" {
  description = "EC2 instance public DNS"
  value       = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].public_dns : aws_instance.trading_bot[0].public_dns
}

output "ssh_command" {
  description = "SSH command to connect to instance"
  value       = "ssh -i ~/.ssh/${var.ssh_key_name}.pem ec2-user@${var.use_elastic_ip && !var.use_spot_instance ? aws_eip.trading_bot[0].public_ip : (var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].public_ip : aws_instance.trading_bot[0].public_ip)}"
}

output "vpc_id" {
  description = "VPC ID where instance is deployed"
  value       = var.create_vpc ? aws_vpc.trading_bot[0].id : data.aws_vpc.default[0].id
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.trading_bot.id
}

output "elastic_ip" {
  description = "Elastic IP address (if enabled)"
  value       = var.use_elastic_ip && !var.use_spot_instance ? aws_eip.trading_bot[0].public_ip : null
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.trading_bot.name
}

