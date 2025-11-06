# Outputs

output "instance_id" {
  description = "EC2 instance ID (existing or newly created)"
  value       = local.existing_instance_id != null ? local.existing_instance_id : (
    var.use_spot_instance ? (
      length(aws_spot_instance_request.trading_bot) > 0 ? aws_spot_instance_request.trading_bot[0].spot_instance_id : null
    ) : (
      length(aws_instance.trading_bot) > 0 ? aws_instance.trading_bot[0].id : null
    )
  )
}

output "instance_public_ip" {
  description = "EC2 instance public IP (or Elastic IP if enabled)"
  value       = local.existing_instance_id != null ? (
    length(data.aws_instance.existing) > 0 ? data.aws_instance.existing[0].public_ip : null
  ) : (
    var.use_elastic_ip && !var.use_spot_instance ? (
      length(aws_eip.trading_bot) > 0 ? aws_eip.trading_bot[0].public_ip : null
    ) : (
      var.use_spot_instance ? (
        length(aws_spot_instance_request.trading_bot) > 0 ? aws_spot_instance_request.trading_bot[0].public_ip : null
      ) : (
        length(aws_instance.trading_bot) > 0 ? aws_instance.trading_bot[0].public_ip : null
      )
    )
  )
}

output "instance_private_ip" {
  description = "EC2 instance private IP"
  value       = local.existing_instance_id != null ? (
    length(data.aws_instance.existing) > 0 ? data.aws_instance.existing[0].private_ip : null
  ) : (
    var.use_spot_instance ? (
      length(aws_spot_instance_request.trading_bot) > 0 ? aws_spot_instance_request.trading_bot[0].private_ip : null
    ) : (
      length(aws_instance.trading_bot) > 0 ? aws_instance.trading_bot[0].private_ip : null
    )
  )
}

output "instance_public_dns" {
  description = "EC2 instance public DNS"
  value       = local.existing_instance_id != null ? (
    length(data.aws_instance.existing) > 0 ? data.aws_instance.existing[0].public_dns : null
  ) : (
    var.use_spot_instance ? (
      length(aws_spot_instance_request.trading_bot) > 0 ? aws_spot_instance_request.trading_bot[0].public_dns : null
    ) : (
      length(aws_instance.trading_bot) > 0 ? aws_instance.trading_bot[0].public_dns : null
    )
  )
}

output "ssh_command" {
  description = "SSH command to connect to instance"
  value       = local.existing_instance_id != null ? (
    length(data.aws_instance.existing) > 0 ? "ssh -i ~/.ssh/${var.ssh_key_name}.pem ec2-user@${data.aws_instance.existing[0].public_ip}" : null
  ) : (
    "ssh -i ~/.ssh/${var.ssh_key_name}.pem ec2-user@${var.use_elastic_ip && !var.use_spot_instance ? (length(aws_eip.trading_bot) > 0 ? aws_eip.trading_bot[0].public_ip : "") : (var.use_spot_instance ? (length(aws_spot_instance_request.trading_bot) > 0 ? aws_spot_instance_request.trading_bot[0].public_ip : "") : (length(aws_instance.trading_bot) > 0 ? aws_instance.trading_bot[0].public_ip : ""))}"
  )
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
