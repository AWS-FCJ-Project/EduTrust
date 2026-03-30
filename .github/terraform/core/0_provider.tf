terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.34.0"
    }
  }

  backend "s3" {
    bucket       = "aws-fcj-terraform-673061300992"
    key          = "backend/core.tfstate"
    region       = "ap-southeast-1"
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region
}

# Provider for CloudFront WAF 
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
