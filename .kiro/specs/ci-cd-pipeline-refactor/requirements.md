# Requirements Document

## Introduction

This document specifies requirements for refactoring the CI/CD pipeline architecture into a two-tier structure that separates infrastructure provisioning from application deployment. The current monolithic deployment pipeline mixes infrastructure changes with application updates, making it difficult to deploy changes independently and understand pipeline responsibilities.

## Glossary

- **Infra_Pipeline**: GitHub Actions workflow that provisions and manages AWS infrastructure resources using Terraform
- **App_Pipeline**: GitHub Actions workflow that builds and deploys application code to existing infrastructure
- **Core_Infrastructure**: AWS resources defined in `.github/terraform/core/` including VPC, networking, security groups, S3, CloudFront, Route53, ECR, IAM, KMS, SSM, Cognito, and CloudWatch
- **Service_Infrastructure**: AWS resources defined in `.github/terraform/service/` including ALB, ASG, and compute resources
- **Backend_Build_Job**: Parallel job that builds backend Docker image, pushes to ECR, and deploys to ASG
- **Frontend_Build_Job**: Parallel job that builds frontend static assets, uploads to S3, and invalidates CloudFront cache
- **AMI_Build_Job**: Optional job that builds base AMI using Packer
- **CI_Pipeline**: Existing validation pipeline that runs pre-commit checks, tests, and terraform validation

## Requirements

### Requirement 1: Infrastructure Pipeline Separation

**User Story:** As a DevOps engineer, I want infrastructure provisioning separated from application deployment, so that I can manage infrastructure changes independently without triggering application builds.

#### Acceptance Criteria

1. THE Infra_Pipeline SHALL provision Core_Infrastructure resources using Terraform
2. THE Infra_Pipeline SHALL provision Service_Infrastructure resources using Terraform
3. WHEN triggered, THE Infra_Pipeline SHALL execute only via manual workflow_dispatch trigger
4. THE Infra_Pipeline SHALL NOT build or deploy application code
5. THE Infra_Pipeline SHALL output infrastructure values required by App_Pipeline

### Requirement 2: Application Pipeline Automation

**User Story:** As a developer, I want application deployments to trigger automatically on code push, so that changes are deployed without manual intervention.

#### Acceptance Criteria

1. WHEN code is pushed to main branch, THE App_Pipeline SHALL trigger automatically
2. WHEN code is pushed to feature branches, THE App_Pipeline SHALL trigger automatically
3. THE App_Pipeline SHALL NOT provision infrastructure resources
4. THE App_Pipeline SHALL execute Backend_Build_Job and Frontend_Build_Job in parallel
5. WHEN CI_Pipeline completes successfully, THE App_Pipeline SHALL trigger automatically

### Requirement 3: Backend Build and Deployment

**User Story:** As a developer, I want backend code built and deployed to ASG, so that API changes are available to users.

#### Acceptance Criteria

1. THE Backend_Build_Job SHALL build Docker image from backend source code
2. THE Backend_Build_Job SHALL push Docker image to ECR with content-based tag
3. WHEN Docker image exists in ECR with matching tag, THE Backend_Build_Job SHALL skip build and push
4. THE Backend_Build_Job SHALL update ASG launch template with new image tag
5. THE Backend_Build_Job SHALL trigger ASG instance refresh to deploy new image
6. THE Backend_Build_Job SHALL update SSM parameter store with backend environment variables

### Requirement 4: Frontend Build and Deployment

**User Story:** As a developer, I want frontend code built and deployed to S3, so that UI changes are available to users.

#### Acceptance Criteria

1. THE Frontend_Build_Job SHALL build static assets from frontend source code
2. THE Frontend_Build_Job SHALL upload static assets to S3 bucket
3. THE Frontend_Build_Job SHALL delete removed files from S3 bucket during sync
4. THE Frontend_Build_Job SHALL invalidate CloudFront cache after S3 upload completes

### Requirement 5: Parallel Build Execution

**User Story:** As a DevOps engineer, I want backend and frontend builds to run in parallel, so that deployment time is minimized.

#### Acceptance Criteria

1. THE App_Pipeline SHALL execute Backend_Build_Job and Frontend_Build_Job concurrently
2. THE Backend_Build_Job SHALL NOT depend on Frontend_Build_Job completion
3. THE Frontend_Build_Job SHALL NOT depend on Backend_Build_Job completion
4. WHEN either build job fails, THE App_Pipeline SHALL continue executing the other job

### Requirement 6: AMI Build Separation

**User Story:** As a DevOps engineer, I want AMI builds separated from application deployments, so that base image updates do not block application releases.

#### Acceptance Criteria

1. THE AMI_Build_Job SHALL build base AMI using Packer
2. THE AMI_Build_Job SHALL execute only when manually triggered via workflow_dispatch
3. THE AMI_Build_Job SHALL compute hash of Packer configuration
4. WHEN AMI with matching configuration hash exists, THE AMI_Build_Job SHALL skip build
5. THE AMI_Build_Job SHALL NOT block App_Pipeline execution

### Requirement 7: CI Pipeline Integration

**User Story:** As a developer, I want validation checks to run before deployment, so that broken code is not deployed to production.

#### Acceptance Criteria

1. THE CI_Pipeline SHALL run pre-commit checks on code changes
2. THE CI_Pipeline SHALL run backend tests with coverage reporting
3. THE CI_Pipeline SHALL validate Terraform configuration syntax
4. THE CI_Pipeline SHALL run security scans on Terraform code
5. WHEN CI_Pipeline fails, THE App_Pipeline SHALL NOT trigger

### Requirement 8: Pipeline Dependency Management

**User Story:** As a DevOps engineer, I want clear dependencies between pipelines, so that deployments execute in the correct order.

#### Acceptance Criteria

1. THE App_Pipeline SHALL depend on CI_Pipeline successful completion
2. THE Backend_Build_Job SHALL depend on infrastructure outputs from Infra_Pipeline
3. THE Frontend_Build_Job SHALL depend on infrastructure outputs from Infra_Pipeline
4. WHEN Infra_Pipeline has not executed, THE App_Pipeline SHALL use existing infrastructure values
5. THE Infra_Pipeline SHALL NOT depend on any other pipeline

### Requirement 9: Infrastructure State Management

**User Story:** As a DevOps engineer, I want infrastructure state managed independently, so that application deployments do not modify infrastructure configuration.

#### Acceptance Criteria

1. THE Infra_Pipeline SHALL store Terraform state in S3 backend
2. THE App_Pipeline SHALL read infrastructure outputs without modifying Terraform state
3. WHEN Core_Infrastructure changes are detected, THE Infra_Pipeline SHALL apply only core changes
4. WHEN Service_Infrastructure changes are detected, THE Infra_Pipeline SHALL apply only service changes
5. THE App_Pipeline SHALL NOT execute terraform apply commands

### Requirement 10: Deployment Rollback Safety

**User Story:** As a DevOps engineer, I want safe deployment rollback mechanisms, so that failed deployments can be reverted quickly.

#### Acceptance Criteria

1. THE Backend_Build_Job SHALL tag Docker images with content-based hash
2. THE Backend_Build_Job SHALL preserve previous Docker images in ECR
3. THE ASG instance refresh SHALL maintain minimum 50 percent healthy instances during deployment
4. WHEN ASG instance refresh fails, THE Backend_Build_Job SHALL report failure status
5. THE Frontend_Build_Job SHALL support CloudFront cache invalidation for immediate rollback visibility

