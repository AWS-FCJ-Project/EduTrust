output "aws_region" { value = var.aws_region }
output "backend_port" { value = var.backend_port }
output "backend_asg_name" { value = aws_autoscaling_group.backend.name }
output "backend_launch_template_id" { value = aws_launch_template.backend.id }
output "alb_dns_name" { value = aws_lb.main.dns_name }

output "backend_url" {
  description = "The primarily routed domain for the Backend API"
  value       = "https://api.${var.domain_name}"
}

output "ecr_repository_url" { value = data.terraform_remote_state.core.outputs.ecr_repository_url }
output "secrets_kms_key_arn" { value = data.terraform_remote_state.core.outputs.secrets_kms_key_arn }
output "domain_name" { value = var.domain_name }
