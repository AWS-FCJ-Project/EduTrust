# Implementation Plan: Remove S3 Frontend Bucket Infrastructure

## Overview

This plan removes S3 frontend bucket infrastructure from Terraform configuration after migrating to AWS Amplify. The implementation involves removing 6 S3-related resources, updating CloudFront to route all traffic through ALB, and cleaning up variable references from Terraform and CI/CD workflows.

## Tasks

- [x] 1. Remove S3 frontend bucket resources from 3_storage_auth.tf
  - Remove aws_s3_bucket.frontend resource
  - Remove aws_s3_bucket_lifecycle_configuration.frontend resource
  - Remove aws_s3_bucket_public_access_block.frontend resource
  - Remove aws_cloudfront_origin_access_control.frontend resource
  - Remove data.aws_iam_policy_document.frontend_s3_policy resource
  - Remove aws_s3_bucket_policy.frontend resource
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 1.1 Write configuration validation test for S3 resource removal
  - **Property 2: S3 Frontend Resources Removed**
  - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
  - Parse 3_storage_auth.tf and verify none of the 6 S3 frontend resources are present
  - Use Python with python-hcl2 library or shell script with grep

- [x] 2. Remove frontend_bucket_name variable from variables.tf
  - Remove the variable "frontend_bucket_name" declaration
  - _Requirements: 2.1_

- [x] 2.1 Write configuration validation test for variable removal
  - **Property 1: No Variable References in Terraform Files**
  - **Property 3: Frontend Bucket Variable Removed**
  - **Validates: Requirements 2.1, 2.2**
  - Scan all .tf files in .github/terraform/core/ for var.frontend_bucket_name references
  - Verify variables.tf does not declare frontend_bucket_name
  - Use shell script with grep or Python with HCL parser

- [x] 3. Update CloudFront distribution in 4_edge.tf
  - [x] 3.1 Remove S3 origin and related attributes
    - Remove origin block with origin_id "S3-Frontend"
    - Remove default_root_object attribute
    - Remove custom_error_response block for 404 errors
    - _Requirements: 3.1, 3.2, 3.3, 3.7_

  - [x] 3.2 Update default_cache_behavior to route to ALB
    - Change target_origin_id from "S3-Frontend" to "ALB-Backend"
    - Preserve allowed_methods, cached_methods, viewer_protocol_policy
    - Preserve min_ttl, default_ttl, max_ttl settings
    - Preserve forwarded_values configuration
    - _Requirements: 3.6, 7.1, 7.2, 7.3, 7.4_

  - [x] 3.3 Write configuration validation test for CloudFront changes
    - **Property 4: CloudFront S3 Origin Removed**
    - **Property 5: CloudFront ALB Origin Preserved**
    - **Property 6: CloudFront Default Behavior Routes to ALB**
    - **Property 7: API Cache Behavior Configuration**
    - **Property 8: Default Cache Behavior Configuration**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3**
    - Parse 4_edge.tf and verify CloudFront configuration structure
    - Verify S3 origin removed, ALB origin preserved, default behavior routes to ALB
    - Verify API cache behavior maintains correct configuration
    - Use Python with python-hcl2 library

- [x] 4. Remove TF_VAR_frontend_bucket_name from CI/CD workflows
  - [x] 4.1 Remove from app.yml
    - Remove TF_VAR_frontend_bucket_name line from build-backend job env section
    - _Requirements: 4.1_

  - [x] 4.2 Remove from infra.yml
    - Remove TF_VAR_frontend_bucket_name line from terraform-core job env section
    - Remove TF_VAR_frontend_bucket_name line from terraform-service job env section
    - _Requirements: 4.2_

  - [x] 4.3 Write configuration validation test for workflow changes
    - **Property 9: CI/CD Workflows Environment Variables Removed**
    - **Validates: Requirements 4.1, 4.2**
    - Parse .github/workflows/app.yml and .github/workflows/infra.yml
    - Verify TF_VAR_frontend_bucket_name is not present in any env sections
    - Use Python with pyyaml library or shell script with grep

- [x] 5. Checkpoint - Validate Terraform configuration
  - Run terraform fmt -check on modified files
  - Run terraform validate in .github/terraform/core/ directory
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster implementation
- Each task references specific requirements for traceability
- Configuration validation tests use static analysis (no AWS resources created)
- Terraform changes should be tested with `terraform plan` before applying
- CloudFront distribution updates can take 15-30 minutes to propagate
- S3 bucket must be empty before Terraform can delete it
- All backend infrastructure (ALB, Route53, ACM, ECR, Cognito) remains unchanged
