# Implementation Plan: CI/CD Pipeline Refactor

## Overview

This plan breaks down the refactoring of the monolithic `deploy-ec2.yml` workflow into three independent pipelines: Infrastructure Pipeline, Application Pipeline, and AMI Build Pipeline. The implementation follows an incremental approach where each new workflow is created and tested before removing the old workflow.

## Tasks

- [x] 1. Create AMI Build Pipeline workflow
  - [x] 1.1 Create `.github/workflows/ami.yml` with manual workflow_dispatch trigger
    - Extract Packer build job from `deploy-ec2.yml`
    - Add input parameter `force_build` (boolean, default: false)
    - Implement Packer configuration hash computation using sha256sum
    - Add conditional check to skip build if AMI with matching PackerHash exists
    - Include temporary VPC/subnet creation for Packer build
    - Add cleanup step for temporary networking resources (with `if: always()`)
    - Deregister old AMI versions before building new one
    - Tag new AMI with PackerHash for idempotent builds
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 1.2 Write unit tests for AMI Pipeline structure
    - Test workflow contains only workflow_dispatch trigger
    - Test Packer hash computation step exists
    - Test conditional AMI check logic is present
    - Test cleanup step has `if: always()` condition
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 2. Create Infrastructure Pipeline workflow
  - [x] 2.1 Create `.github/workflows/infra.yml` with manual trigger
    - Add workflow_dispatch trigger only (no automatic triggers)
    - Create `terraform-core` job for core infrastructure
    - Create `terraform-service` job for service infrastructure
    - Add job dependency: terraform-service needs terraform-core
    - Copy AWS credentials configuration from deploy-ec2.yml
    - Copy all TF_VAR environment variables from deploy-ec2.yml
    - _Requirements: 1.1, 1.2, 1.3, 8.5, 9.1_

  - [x] 2.2 Implement terraform-core job
    - Add checkout step
    - Add Terraform setup step (version 1.14.6)
    - Add step to write terraform.tfvars from secrets
    - Add path filter step to detect changes in `.github/terraform/core/**`
    - Add conditional terraform init and apply for core directory
    - Use condition: `if: steps.filter.outputs.core == 'true' || github.event_name == 'workflow_dispatch'`
    - _Requirements: 1.1, 9.3_

  - [x] 2.3 Implement terraform-service job
    - Add checkout step
    - Add Terraform setup step
    - Add step to write terraform.tfvars from secrets
    - Add terraform init and apply for service directory (always runs)
    - Add step to capture terraform outputs: asg_name, aws_region, ecr_repository_url, backend_port, secrets_kms_key_arn
    - Define job-level outputs for all captured values
    - _Requirements: 1.2, 1.5, 9.4_

  - [x] 2.4 Add ECR repository creation/import logic
    - Extract ECR repository creation step from deploy-ec2.yml
    - Add to terraform-core job before terraform apply
    - Include logic to import existing repository if it exists
    - _Requirements: 1.1_

  - [x] 2.5 Write unit tests for Infrastructure Pipeline structure
    - Test workflow contains only workflow_dispatch trigger
    - Test terraform-core job applies core infrastructure
    - Test terraform-service job applies service infrastructure
    - Test terraform-service job defines required outputs
    - Test no Docker build or npm build steps exist
    - _Requirements: 1.3, 1.4, 1.5_

- [x] 3. Checkpoint - Review Infrastructure and AMI workflows
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Create Application Pipeline workflow
  - [x] 4.1 Create `.github/workflows/app.yml` with automatic triggers
    - Add workflow_run trigger listening for CI pipeline completion
    - Configure trigger for branches: main and feat/**
    - Add workflow_dispatch trigger for manual execution
    - Add condition to check CI pipeline success: `github.event.workflow_run.conclusion == 'success'`
    - Set concurrency group to prevent parallel deployments
    - _Requirements: 2.1, 2.2, 2.5, 7.5, 8.1_

  - [x] 4.2 Implement build-backend job
    - Add checkout step with ref: `${{ github.event.workflow_run.head_sha || github.ref }}`
    - Add step to read infrastructure outputs using terraform output commands
    - Set working directory to `.github/terraform/service`
    - Read outputs: ecr_repository_url, asg_name, secrets_kms_key_arn, aws_region
    - Store outputs in environment variables for subsequent steps
    - _Requirements: 2.3, 8.2, 9.2_

  - [x] 4.3 Add Docker build and push logic to build-backend job
    - Add step to compute content hash of backend source code
    - Use find command: `find backend -type f \( -name "Dockerfile" -o -path "*/backend/src/*" -o -path "*/backend/requirements.txt" -o -path "*/backend/uv.lock" \) | sort | xargs sha256sum | sha256sum`
    - Add step to set image variables (image URL and tag)
    - Add AWS credentials configuration
    - Add ECR login step
    - Add step to check if image with matching tag exists in ECR
    - Add conditional Docker build and push (skip if image exists)
    - Use docker/build-push-action with tags from computed hash
    - Define job outputs: image and image_tag
    - _Requirements: 3.1, 3.2, 3.3, 10.1, 10.2_

  - [x] 4.4 Add ASG deployment logic to build-backend job
    - Add step to update SSM parameter `/edutrust/backend/env` with BACKEND_ENV_FILE secret
    - Use KMS key ARN from infrastructure outputs for encryption
    - Add Terraform setup step
    - Add step to write terraform.tfvars from secrets
    - Add step to update launch template: `terraform apply -auto-approve -var="backend_image_tag=$IMAGE_TAG"`
    - Add step to start ASG instance refresh with MinHealthyPercentage: 50 and InstanceWarmup: 60
    - Add polling loop to monitor refresh status (check every 30 seconds)
    - Add failure handling for Failed/Cancelled/TimedOut status
    - _Requirements: 3.4, 3.5, 3.6, 10.3, 10.4_

  - [x] 4.5 Write unit tests for build-backend job
    - Test content hash computation step exists
    - Test ECR image check logic is present
    - Test Docker build is conditional on image existence
    - Test SSM parameter update step exists
    - Test ASG instance refresh includes safety configuration
    - Test failure handling for refresh status
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 10.1, 10.3, 10.4_

- [x] 5. Implement frontend build job in Application Pipeline
  - [x] 5.1 Create build-frontend job with parallel execution
    - Add job definition without needs dependency on build-backend
    - Add checkout step with ref: `${{ github.event.workflow_run.head_sha || github.ref }}`
    - Add Node.js setup step (version 20) with npm cache
    - Add AWS credentials configuration
    - _Requirements: 2.4, 5.1, 5.2, 5.3_

  - [x] 5.2 Add frontend build and deployment logic
    - Add step to run `npm install` in frontend directory
    - Add step to run `npm run build` in frontend directory
    - Add step to sync build output to S3: `aws s3 sync out/ s3://$S3_BUCKET --delete`
    - Add step to invalidate CloudFront cache: `aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_DIST_ID --paths "/*"`
    - Use S3_BUCKET and CLOUDFRONT_DIST_ID from GitHub secrets
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 10.5_

  - [x] 5.3 Write unit tests for build-frontend job
    - Test job does not depend on build-backend
    - Test npm install and build steps exist
    - Test S3 sync includes --delete flag
    - Test CloudFront invalidation step exists after S3 sync
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.2, 5.3_

- [x] 6. Checkpoint - Review Application Pipeline workflow
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Write property-based tests for workflow validation
  - [x] 7.1 Write property test for Infrastructure Pipeline manual trigger
    - **Property 1: Infrastructure Pipeline Manual Trigger Only**
    - **Validates: Requirements 1.3**

  - [x] 7.2 Write property test for Infrastructure Pipeline Terraform jobs
    - **Property 2: Infrastructure Pipeline Provisions Both Tiers**
    - **Validates: Requirements 1.1, 1.2**

  - [x] 7.3 Write property test for Infrastructure Pipeline excludes application code
    - **Property 3: Infrastructure Pipeline Excludes Application Code**
    - **Validates: Requirements 1.4**

  - [x] 7.4 Write property test for Infrastructure Pipeline outputs
    - **Property 4: Infrastructure Pipeline Exports Required Outputs**
    - **Validates: Requirements 1.5**

  - [x] 7.5 Write property test for Application Pipeline automatic trigger
    - **Property 5: Application Pipeline Automatic Trigger**
    - **Validates: Requirements 2.1, 2.2, 2.5, 8.1**

  - [x] 7.6 Write property test for Application Pipeline read-only access
    - **Property 6: Application Pipeline Read-Only Infrastructure Access**
    - **Validates: Requirements 2.3, 9.2, 9.5**

  - [x] 7.7 Write property test for parallel build execution
    - **Property 7: Parallel Build Job Execution**
    - **Validates: Requirements 2.4, 5.1, 5.2, 5.3, 5.4**

  - [x] 7.8 Write property test for backend build workflow completeness
    - **Property 8: Backend Build Job Complete Workflow**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

  - [x] 7.9 Write property test for frontend build workflow completeness
    - **Property 9: Frontend Build Job Complete Workflow**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

  - [x] 7.10 Write property test for AMI Pipeline trigger and caching
    - **Property 10: AMI Pipeline Manual Trigger and Hash-Based Caching**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

  - [x] 7.11 Write property test for AMI Pipeline independence
    - **Property 11: AMI Pipeline Independence**
    - **Validates: Requirements 6.5**

  - [x] 7.12 Write property test for CI Pipeline dependency
    - **Property 12: CI Pipeline Dependency Check**
    - **Validates: Requirements 7.5**

  - [x] 7.13 Write property test for backend infrastructure dependency
    - **Property 13: Backend Job Infrastructure Dependency**
    - **Validates: Requirements 8.2**

  - [x] 7.14 Write property test for frontend infrastructure dependency
    - **Property 14: Frontend Job Infrastructure Dependency**
    - **Validates: Requirements 8.3**

  - [x] 7.15 Write property test for application state persistence
    - **Property 15: Application Pipeline State Persistence**
    - **Validates: Requirements 8.4**

  - [x] 7.16 Write property test for infrastructure independence
    - **Property 16: Infrastructure Pipeline Independence**
    - **Validates: Requirements 8.5**

  - [x] 7.17 Write property test for Terraform S3 backend
    - **Property 17: Terraform S3 Backend Configuration**
    - **Validates: Requirements 9.1**

  - [x] 7.18 Write property test for conditional core infrastructure
    - **Property 18: Conditional Core Infrastructure Application**
    - **Validates: Requirements 9.3**

  - [x] 7.19 Write property test for service infrastructure always applied
    - **Property 19: Service Infrastructure Always Applied**
    - **Validates: Requirements 9.4**

  - [x] 7.20 Write property test for content-based tagging
    - **Property 20: Content-Based Docker Image Tagging**
    - **Validates: Requirements 10.1**

  - [x] 7.21 Write property test for ECR image preservation
    - **Property 21: ECR Image Preservation**
    - **Validates: Requirements 10.2**

  - [x] 7.22 Write property test for ASG refresh safety
    - **Property 22: ASG Instance Refresh Safety Configuration**
    - **Validates: Requirements 10.3**

  - [x] 7.23 Write property test for ASG refresh failure handling
    - **Property 23: ASG Instance Refresh Failure Handling**
    - **Validates: Requirements 10.4**

  - [x] 7.24 Write property test for CloudFront invalidation
    - **Property 24: CloudFront Cache Invalidation**
    - **Validates: Requirements 10.5**

- [x] 8. Update CI Pipeline integration
  - [x] 8.1 Verify CI pipeline triggers Application Pipeline on success
    - Review `.github/workflows/ci.yml` to ensure it's named "CI"
    - Confirm Application Pipeline workflow_run trigger references "CI" workflow
    - No code changes needed if CI workflow name matches
    - _Requirements: 2.5, 7.5, 8.1_

- [x] 9. Test new workflows in staging environment
  - [x] 9.1 Test AMI Pipeline execution
    - Manually trigger AMI Pipeline via workflow_dispatch
    - Verify AMI is created with PackerHash tag
    - Verify temporary VPC resources are cleaned up
    - Verify second run skips build when hash matches
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 9.2 Test Infrastructure Pipeline execution
    - Manually trigger Infrastructure Pipeline via workflow_dispatch
    - Verify core infrastructure is provisioned
    - Verify service infrastructure is provisioned
    - Verify terraform outputs are captured correctly
    - Verify path filtering works for core infrastructure changes
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 9.3, 9.4_

  - [x] 9.3 Test Application Pipeline execution
    - Push code change to trigger CI pipeline
    - Verify Application Pipeline triggers after CI success
    - Verify backend and frontend jobs run in parallel
    - Verify Docker image is built and pushed to ECR
    - Verify ASG instance refresh completes successfully
    - Verify frontend assets are uploaded to S3
    - Verify CloudFront cache is invalidated
    - _Requirements: 2.1, 2.2, 2.4, 3.1, 3.2, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 5.1_

  - [x] 9.4 Test build caching behavior
    - Push code change that doesn't affect backend
    - Verify backend Docker build is skipped when image hash matches
    - Push code change that affects backend
    - Verify new Docker image is built and pushed
    - _Requirements: 3.3, 10.1_

- [x] 10. Checkpoint - Validate all workflows function correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Clean up old workflow file
  - [x] 11.1 Archive deploy-ec2.yml workflow
    - Rename `.github/workflows/deploy-ec2.yml` to `.github/workflows/deploy-ec2.yml.old`
    - Add comment at top of file indicating it's been replaced by infra.yml, app.yml, and ami.yml
    - Commit the archived file for reference
    - _Requirements: All (cleanup after migration)_

  - [x] 11.2 Update documentation references
    - Search for references to deploy-ec2.yml in README or documentation files
    - Update references to point to new workflow files
    - Document the new pipeline architecture and trigger mechanisms
    - _Requirements: All (documentation)_

- [x] 12. Final checkpoint - Verify production deployment
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster implementation
- Each task references specific requirements for traceability
- The implementation follows an additive approach: create new workflows first, test thoroughly, then remove old workflow
- All three new workflows can coexist with the old deploy-ec2.yml during testing phase
- Infrastructure Pipeline should be run manually at least once before relying on Application Pipeline
- Property tests validate workflow structure, not runtime behavior (workflows are declarative YAML)
- Integration testing (tasks 9.1-9.4) should be performed in a non-production environment first
