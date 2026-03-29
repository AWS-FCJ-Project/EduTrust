variable "aws_region" { type = string }
variable "ec2_instance_name" { type = string }

variable "vpc_cidr_block" { type = string }
variable "private_subnet_1a_cidr" { type = string }
variable "private_subnet_1c_cidr" { type = string }
variable "public_subnet_1a_cidr" { type = string }
variable "public_subnet_1c_cidr" { type = string }
variable "vpc_name" { type = string }
variable "igw_name" { type = string }

variable "s3_endpoint_service_name" { type = string }
variable "ecr_dkr_endpoint_service_name" { type = string }
variable "ecr_api_endpoint_service_name" { type = string }
variable "ssm_endpoint_service_name" { type = string }
variable "sts_endpoint_service_name" { type = string }
variable "logs_endpoint_service_name" { type = string }

variable "ecr_repository_name" { type = string }
variable "ecr_tag_immutable" { type = bool }

variable "domain_name" { type = string }
variable "cognito_domain_prefix" { type = string }
variable "frontend_bucket_name" { type = string }
