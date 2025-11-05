# Outputs

output "instance_id" {
  description = "EC2 instance ID"
  value       = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].spot_instance_id : aws_instance.trading_bot[0].id
}

output "instance_public_ip" {
  description = "EC2 instance public IP"
  value       = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].public_ip : aws_instance.trading_bot[0].public_ip
}

output "instance_public_dns" {
  description = "EC2 instance public DNS"
  value       = var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].public_dns : aws_instance.trading_bot[0].public_dns
}

output "ssh_command" {
  description = "SSH command to connect to instance"
  value       = "ssh -i ~/.ssh/your-key.pem ec2-user@${var.use_spot_instance ? aws_spot_instance_request.trading_bot[0].public_ip : aws_instance.trading_bot[0].public_ip}"
}

