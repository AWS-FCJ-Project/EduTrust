# CI/CD Pipeline Architecture

## Overview

This directory contains the CI/CD workflows for the EduTrust project. The pipeline is organized into three independent workflows that separate infrastructure provisioning from application deployment.

## Workflows

### 1. Infrastructure Pipeline (`infra.yml`)

**Purpose**: Provision and manage AWS infrastructure resources using Terraform.

**Trigger**: Manual only (workflow_dispatch)

**What it does**:
- Provisions core infrastructure (VPC, networking, S3, CloudFront, ECR, IAM, KMS, SSM)
- Provisions service infrastructure (ALB, ASG, launch templates)
- Exports infrastructure outputs for use by Application Pipeline

**When to use**:
- Initial infrastructure setup
- Infrastructure configuration changes
- Scaling infrastructure resources
- Adding new AWS services

**How to trigger**:
1. Navigate to Actions tab in GitHub
2. Select "Infrastructure Pipeline"
3. Click "Run workflow"
4. Select branch and click "Run workflow"

### 2. Application Pipeline (`app.yml`)

**Purpose**: Build and deploy application code to existing infrastructure.

**Trigger**: Automatic after CI pipeline success (also supports manual trigger)

**What it does**:
- Builds backend Docker image and pushes to ECR
- Deploys backend to ASG via instance refresh
- Builds frontend static assets
- Uploads frontend to S3 and invalidates CloudFront cache
- Backend and frontend builds run in parallel

**When to use**:
- Automatically triggered on code push to main or feat/** branches
- Manual trigger for redeployment without code changes

**How it works**:
1. CI pipeline runs tests and validation
2. On CI success, Application Pipeline triggers automatically
3. Backend and frontend jobs execute in parallel
4. Application is deployed with zero downtime

### 3. AMI Build Pipeline (`ami.yml`)

**Purpose**: Build base AMI with pre-installed dependencies using Packer.

**Trigger**: Manual only (workflow_dispatch)

**What it does**:
- Builds Ubuntu 24.04 base AMI with Docker, AWS CLI, CloudWatch agent
- Uses hash-based caching to skip rebuild if configuration unchanged
- Creates temporary VPC for Packer build and cleans up after
- Tags AMI with configuration hash for idempotent builds

**When to use**:
- Initial AMI creation
- Updating base image dependencies
- OS security patches
- Docker version updates

**How to trigger**:
1. Navigate to Actions tab in GitHub
2. Select "AMI Build Pipeline"
3. Click "Run workflow"
4. Optionally check "force_build" to rebuild even if hash matches
5. Click "Run workflow"

### 4. CI Pipeline (`ci.yml`)

**Purpose**: Validate code quality before deployment.

**Trigger**: Automatic on push and pull requests

**What it does**:
- Runs pre-commit checks
- Executes backend tests with coverage
- Validates Terraform configuration
- Runs security scans on Terraform code

**When it runs**:
- On every push to any branch
- On every pull request

## Pipeline Dependencies

```
Code Push → CI Pipeline → Application Pipeline
                              ├─→ Backend Build (parallel)
                              └─→ Frontend Build (parallel)

Manual Trigger → Infrastructure Pipeline
                    ├─→ Core Infrastructure
                    └─→ Service Infrastructure

Manual Trigger → AMI Pipeline
```

## Workflow Comparison

| Feature | Infrastructure | Application | AMI | CI |
|---------|---------------|-------------|-----|-----|
| Trigger | Manual | Auto + Manual | Manual | Auto |
| Terraform | Apply | Read-only | No | Validate |
| Docker Build | No | Yes | No | No |
| Frontend Build | No | Yes | No | No |
| Packer Build | No | No | Yes | No |
| Duration | 10-20 min | 15-25 min | 10-15 min | 5-10 min |

## Key Features

### Content-Based Caching

Both Application Pipeline and AMI Pipeline use content-based hashing to skip unnecessary builds:

- **Backend**: Docker images tagged with SHA256 hash of source code
- **AMI**: AMIs tagged with SHA256 hash of Packer configuration

This provides:
- Faster deployments when code hasn't changed
- Automatic rollback capability (previous images preserved)
- Idempotent builds (same input = same output)

### Zero-Downtime Deployment

Application Pipeline uses ASG instance refresh with:
- MinHealthyPercentage: 50% (maintains half capacity during deployment)
- InstanceWarmup: 60 seconds (waits for health checks)
- Rolling update strategy

### Parallel Builds

Backend and frontend builds execute concurrently to minimize deployment time:
- No dependencies between jobs
- Independent failure handling
- Faster overall deployment

### Path Filtering

Infrastructure Pipeline uses path filtering to optimize Terraform applies:
- Core infrastructure only applies when `.github/terraform/core/**` changes
- Service infrastructure always applies (depends on core outputs)

## Required GitHub Secrets

### AWS Credentials
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key

### Terraform Variables
- `TERRAFORM_VARIABLES`: Complete terraform.tfvars content

### Application Configuration
- `BACKEND_ENV_FILE`: Backend environment variables
- `FRONTEND_S3_BUCKET`: S3 bucket name for frontend
- `CLOUDFRONT_DISTRIBUTION_ID`: CloudFront distribution ID

## Common Tasks

### Deploy Application Changes

1. Push code to main or feature branch
2. CI pipeline runs automatically
3. Application Pipeline triggers on CI success
4. Monitor deployment in Actions tab

### Update Infrastructure

1. Modify Terraform files in `.github/terraform/`
2. Commit and push changes
3. Manually trigger Infrastructure Pipeline
4. Verify changes in AWS Console

### Rebuild Base AMI

1. Modify Packer configuration in `.github/packer/`
2. Manually trigger AMI Pipeline
3. Wait for AMI build to complete
4. Update Terraform to use new AMI (if needed)

### Rollback Deployment

#### Backend Rollback:
1. Identify previous image tag from ECR
2. Manually trigger Infrastructure Pipeline
3. Update `backend_image_tag` variable to previous tag
4. ASG will refresh with old image

#### Frontend Rollback:
1. Identify previous commit with working frontend
2. Checkout that commit
3. Manually trigger Application Pipeline
4. Frontend will deploy from that commit

## Troubleshooting

### Application Pipeline Not Triggering

**Cause**: CI pipeline failed or workflow_run trigger not configured

**Solution**:
- Check CI pipeline status
- Verify CI workflow name is "CI"
- Check Application Pipeline workflow_run trigger configuration

### Terraform State Lock Error

**Cause**: Another Terraform operation in progress or previous run didn't release lock

**Solution**:
- Wait 5-10 minutes for lock to expire
- Check DynamoDB lock table
- Manually release lock if needed

### ASG Instance Refresh Fails

**Cause**: Health check failures or launch template errors

**Solution**:
- Check instance logs in CloudWatch
- Verify launch template configuration
- Check ALB target group health checks
- Review ASG instance refresh status reason

### Docker Build Fails

**Cause**: Syntax errors or missing dependencies

**Solution**:
- Test Docker build locally
- Check Dockerfile syntax
- Verify all dependencies in requirements.txt
- Review build logs for specific errors

## Migration from Old Workflow

The previous monolithic `deploy-ec2.yml` workflow has been replaced by the three new workflows. The old workflow is archived as `deploy-ec2.yml.old` for reference.

### Key Changes:

1. **Separation of Concerns**: Infrastructure and application deployments are now independent
2. **Manual Infrastructure**: Infrastructure changes require explicit approval
3. **Automatic Application**: Application deployments trigger automatically on code push
4. **Parallel Builds**: Backend and frontend build concurrently
5. **Build Caching**: Skips unnecessary Docker builds and AMI builds

### Benefits:

- Faster application deployments (no infrastructure provisioning)
- Safer infrastructure changes (manual trigger prevents accidents)
- Better visibility (clear separation of responsibilities)
- Improved rollback (previous images preserved)
- Reduced deployment time (parallel builds + caching)

## Additional Resources

- [Staging Test Guide](../../tests/workflows/STAGING_TEST_GUIDE.md)
- [Design Document](../../.kiro/specs/ci-cd-pipeline-refactor/design.md)
- [Requirements](../../.kiro/specs/ci-cd-pipeline-refactor/requirements.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
