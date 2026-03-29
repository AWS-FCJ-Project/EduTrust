output "aws_region" { value = var.aws_region }
output "vpc_id" { value = aws_vpc.main.id }
output "private_subnet_ids" { value = [aws_subnet.private_1a.id, aws_subnet.private_1c.id] }
output "public_subnet_ids" { value = [aws_subnet.public_1a.id, aws_subnet.public_1c.id] }
output "route53_zone_id" { value = aws_route53_zone.main.zone_id }
output "route53_name_servers" { value = aws_route53_zone.main.name_servers }

output "alb_certificate_arn" { value = aws_acm_certificate_validation.alb.certificate_arn }
output "alb_logs_bucket_id" { value = aws_s3_bucket.alb_logs.id }

output "cognito_user_pool_id" { value = aws_cognito_user_pool.main.id }
output "cognito_user_pool_arn" { value = aws_cognito_user_pool.main.arn }
output "cognito_user_pool_client_id" { value = aws_cognito_user_pool_client.main.id }
output "cognito_user_pool_domain" { value = aws_cognito_user_pool_domain.main.domain }

output "backend_instance_profile_name" { value = aws_iam_instance_profile.backend.name }
output "backend_role_name" { value = aws_iam_role.backend.name }
output "backend_role_arn" { value = aws_iam_role.backend.arn }
output "container_logs_group_name" { value = aws_cloudwatch_log_group.container_logs.name }

output "secrets_kms_key_arn" { value = aws_kms_key.secrets.arn }
output "ecr_repository_url" { value = aws_ecr_repository.backend.repository_url }
output "cloudfront_url" { value = aws_cloudfront_distribution.main.domain_name }
