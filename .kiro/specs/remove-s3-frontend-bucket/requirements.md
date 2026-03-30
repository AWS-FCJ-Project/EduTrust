# Requirements Document

## Introduction

This document specifies requirements for removing S3 frontend bucket infrastructure after migrating frontend hosting to AWS Amplify. The infrastructure currently uses an S3 bucket with CloudFront for frontend asset delivery, but this is no longer needed since Amplify now handles frontend hosting independently. The CloudFront distribution must be updated to only handle API traffic routing to the backend ALB.

## Glossary

- **S3_Frontend_Bucket**: The AWS S3 bucket (aws_s3_bucket.frontend) that previously stored frontend static assets
- **CloudFront_Distribution**: The AWS CloudFront distribution that routes traffic to origins
- **OAC**: Origin Access Control - AWS resource that allows CloudFront to access private S3 buckets
- **ALB_Backend**: Application Load Balancer origin that serves backend API traffic
- **Terraform_Core**: The Terraform configuration in .github/terraform/core/ that manages core infrastructure
- **CI_CD_Workflows**: GitHub Actions workflows in .github/workflows/ that deploy infrastructure and applications

## Requirements

### Requirement 1: Remove S3 Frontend Bucket Resources

**User Story:** As a DevOps engineer, I want to remove the S3 frontend bucket and related resources from Terraform, so that we eliminate unused infrastructure after migrating to Amplify.

#### Acceptance Criteria

1. THE Terraform_Core SHALL NOT include the aws_s3_bucket.frontend resource
2. THE Terraform_Core SHALL NOT include the aws_s3_bucket_lifecycle_configuration.frontend resource
3. THE Terraform_Core SHALL NOT include the aws_s3_bucket_public_access_block.frontend resource
4. THE Terraform_Core SHALL NOT include the aws_cloudfront_origin_access_control.frontend resource
5. THE Terraform_Core SHALL NOT include the data.aws_iam_policy_document.frontend_s3_policy resource
6. THE Terraform_Core SHALL NOT include the aws_s3_bucket_policy.frontend resource

### Requirement 2: Remove Frontend Bucket Variable

**User Story:** As a DevOps engineer, I want to remove the frontend_bucket_name variable from Terraform configuration, so that the configuration reflects that frontend hosting is no longer managed by this infrastructure.

#### Acceptance Criteria

1. THE Terraform_Core SHALL NOT declare a frontend_bucket_name variable in variables.tf
2. THE Terraform_Core SHALL NOT reference var.frontend_bucket_name in any resource configuration

### Requirement 3: Update CloudFront Distribution Configuration

**User Story:** As a DevOps engineer, I want to update the CloudFront distribution to remove the S3 frontend origin, so that CloudFront only handles API traffic routing.

#### Acceptance Criteria

1. THE CloudFront_Distribution SHALL NOT include an origin with origin_id "S3-Frontend"
2. THE CloudFront_Distribution SHALL NOT include an origin_access_control_id reference
3. THE CloudFront_Distribution SHALL NOT include a default_root_object attribute
4. THE CloudFront_Distribution SHALL maintain the origin with origin_id "ALB-Backend"
5. THE CloudFront_Distribution SHALL maintain the ordered_cache_behavior for path_pattern "/api/*"
6. THE CloudFront_Distribution SHALL update the default_cache_behavior to target_origin_id "ALB-Backend"
7. THE CloudFront_Distribution SHALL NOT include a custom_error_response for 404 errors

### Requirement 4: Remove Frontend Bucket Environment Variables from CI/CD

**User Story:** As a DevOps engineer, I want to remove TF_VAR_frontend_bucket_name from CI/CD workflows, so that the workflows no longer reference the removed infrastructure variable.

#### Acceptance Criteria

1. THE CI_CD_Workflows SHALL NOT include TF_VAR_frontend_bucket_name in .github/workflows/app.yml
2. THE CI_CD_Workflows SHALL NOT include TF_VAR_frontend_bucket_name in .github/workflows/infra.yml

### Requirement 5: Preserve Backend Infrastructure

**User Story:** As a DevOps engineer, I want to ensure all backend infrastructure remains functional, so that API services continue operating without disruption.

#### Acceptance Criteria

1. THE Terraform_Core SHALL maintain all ALB-related resources unchanged
2. THE Terraform_Core SHALL maintain all Route53 resources unchanged
3. THE Terraform_Core SHALL maintain all ACM certificate resources unchanged
4. THE Terraform_Core SHALL maintain all ECR resources unchanged
5. THE Terraform_Core SHALL maintain all Cognito resources unchanged
6. THE Terraform_Core SHALL maintain the aws_s3_bucket.alb_logs resource unchanged
7. THE Terraform_Core SHALL maintain all VPC and networking resources unchanged

### Requirement 6: Maintain CloudFront API Routing

**User Story:** As a backend developer, I want CloudFront to continue routing /api/* requests to the ALB, so that API endpoints remain accessible through the CloudFront domain.

#### Acceptance Criteria

1. WHEN a request matches path_pattern "/api/*", THE CloudFront_Distribution SHALL forward the request to origin_id "ALB-Backend"
2. THE CloudFront_Distribution SHALL forward all HTTP methods (DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT) for /api/* paths
3. THE CloudFront_Distribution SHALL forward all headers for /api/* paths
4. THE CloudFront_Distribution SHALL forward all cookies for /api/* paths
5. THE CloudFront_Distribution SHALL forward query strings for /api/* paths
6. THE CloudFront_Distribution SHALL set cache TTL to 0 for /api/* paths

### Requirement 7: Update Default Behavior for Non-API Traffic

**User Story:** As a DevOps engineer, I want the CloudFront default behavior to route to the ALB backend, so that any non-API traffic is handled by the backend application.

#### Acceptance Criteria

1. WHEN a request does NOT match path_pattern "/api/*", THE CloudFront_Distribution SHALL forward the request to origin_id "ALB-Backend"
2. THE CloudFront_Distribution SHALL allow GET, HEAD, and OPTIONS methods for the default behavior
3. THE CloudFront_Distribution SHALL redirect HTTP to HTTPS for the default behavior
4. THE CloudFront_Distribution SHALL maintain caching configuration for the default behavior

