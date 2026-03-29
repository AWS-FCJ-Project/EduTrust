variable "aws_region" { type = string }
variable "ec2_instance_type" { type = string }
variable "ec2_instance_name" { type = string }
variable "ec2_key_name" { type = string }

variable "asg_min_size" { type = number }
variable "asg_max_size" { type = number }
variable "asg_desired_capacity" { type = number }

variable "backend_image_tag" { type = string }
variable "backend_port" { type = number }


variable "docdb_egress_cidr_blocks" { type = list(string) }
variable "redis_egress_cidr_blocks" { type = list(string) }
variable "dns_egress_cidr_blocks" { type = list(string) }

variable "domain_name" { type = string }
