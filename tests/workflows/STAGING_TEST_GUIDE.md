# Staging Environment Testing Guide

## Overview

This guide provides step-by-step instructions for testing the three new CI/CD workflows in a staging environment before production deployment:

1. **AMI Pipeline** (`.github/workflows/ami.yml`)
2. **Infrastructure Pipeline** (`.github/workflows/infra.yml`)
3. **Application Pipeline** (`.github/workflows/app.yml`)

## Prerequisites

Before starting the tests, ensure you have:

- [ ] Access to GitHub Actions workflows in the repository
- [ ] AWS Console access with permissions to view:
  - EC2 (AMIs, VPCs, Subnets, Security Groups)
  - ECR (Container Registry)
  - Auto Scaling Groups
  - S3 Buckets
  - CloudFront Distributions
  - Terraform State (S3 backend)
- [ ] AWS CLI configured locally for verification commands
- [ ] All required GitHub secrets configured:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `TERRAFORM_VARIABLES`
  - `BACKEND_ENV_FILE`
  - `S3_BUCKET`
  - `CLOUDFRONT_DIST_ID`

## Test Execution Order

Execute tests in this order to ensure proper infrastructure setup:

1. **Test 9.1**: AMI Pipeline execution
2. **Test 9.2**: Infrastructure Pipeline execution
3. **Test 9.3**: Application Pipeline execution
4. **Test 9.4**: Build caching behavior

---

## Test 9.1: AMI Pipeline Execution

**Objective**: Verify AMI is created with PackerHash tag, temporary VPC resources are cleaned up, and second run skips build when hash matches.

**Requirements Validated**: 6.1, 6.2, 6.3, 6.4

### Step 1: Trigger AMI Pipeline (First Run)

1. Navigate to **Actions** tab in GitHub repository
2. Select **AMI Build Pipeline** workflow
3. Click **Run workflow** dropdown
4. Leave `force_build` unchecked (default: false)
5. Click **Run workflow** button

### Step 2: Monitor Workflow Execution

Watch the workflow progress through these steps:

- [ ] Checkout code
- [ ] Setup Packer
- [ ] Configure AWS credentials
- [ ] Run Packer Init
- [ ] Compute Packer Configuration Hash
- [ ] Check for Existing AMI with Matching Hash
- [ ] Create Temporary VPC for Packer Build
- [ ] Deregister Old AMI Versions
- [ ] Build AMI with Packer
- [ ] Cleanup Temporary VPC Resources

**Expected Duration**: 10-15 minutes

### Step 3: Verify AMI Creation

#### Via AWS Console:

1. Navigate to **EC2 > AMIs** in AWS Console
2. Filter by **Owned by me**
3. Find AMI with name pattern: `edutrust-base-ami-*`
4. Verify AMI has these tags:
   - `Name`: `EduTrust-Base-AMI`
   - `PackerHash`: (SHA256 hash value)
   - `OS`: `Ubuntu-24.04`
   - `CreatedBy`: `Packer`

#### Via AWS CLI:

```bash
# List AMIs with PackerHash tag
aws ec2 describe-images \
  --owners self \
  --filters "Name=tag:Name,Values=EduTrust-Base-AMI" \
  --query 'Images[*].[ImageId,Name,Tags[?Key==`PackerHash`].Value|[0],CreationDate]' \
  --output table
```

**Expected Output**: One AMI with PackerHash tag matching the hash from workflow logs

### Step 4: Verify Temporary VPC Cleanup

#### Via AWS Console:

1. Navigate to **VPC > Your VPCs**
2. Search for VPCs with name `PackerTempVPC`
3. Verify **NO** temporary VPCs exist

#### Via AWS CLI:

```bash
# Check for temporary Packer VPCs
aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=PackerTempVPC" \
  --query 'Vpcs[*].[VpcId,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

**Expected Output**: Empty result (no temporary VPCs)

### Step 5: Verify Temporary Resources Cleanup

Check that all temporary networking resources were deleted:

```bash
# Check for temporary subnets
aws ec2 describe-subnets \
  --filters "Name=tag:Name,Values=PackerTempSubnet" \
  --query 'Subnets[*].SubnetId' \
  --output table

# Check for temporary internet gateways
aws ec2 describe-internet-gateways \
  --filters "Name=tag:Name,Values=PackerTempIGW" \
  --query 'InternetGateways[*].InternetGatewayId' \
  --output table
```

**Expected Output**: Empty results for both commands

### Step 6: Trigger AMI Pipeline (Second Run - Hash Match)

1. Navigate to **Actions** tab in GitHub repository
2. Select **AMI Build Pipeline** workflow
3. Click **Run workflow** dropdown
4. Leave `force_build` unchecked (default: false)
5. Click **Run workflow** button

### Step 7: Verify Build Skip Behavior

Watch the workflow logs for the **Check for Existing AMI with Matching Hash** step:

**Expected Log Output**:
```
AMI with matching hash <hash_value> exists (ami-xxxxx). Skipping build.
```

Verify these steps are **SKIPPED**:
- [ ] Create Temporary VPC for Packer Build
- [ ] Deregister Old AMI Versions
- [ ] Build AMI with Packer

**Expected Duration**: 1-2 minutes (much faster than first run)

### Step 8: Test Force Build Option

1. Trigger workflow again with `force_build` checked
2. Verify build proceeds even though AMI with matching hash exists
3. Verify new AMI is created (old one should be deregistered)

### Test 9.1 Success Criteria

- [x] First run creates AMI with PackerHash tag
- [x] Temporary VPC resources are cleaned up after build
- [x] Second run skips build when hash matches
- [x] Force build option rebuilds AMI even with matching hash
- [x] No temporary networking resources remain in AWS

---

## Test 9.2: Infrastructure Pipeline Execution

**Objective**: Verify core and service infrastructure are provisioned, terraform outputs are captured, and path filtering works.

**Requirements Validated**: 1.1, 1.2, 1.3, 1.5, 9.3, 9.4

### Step 1: Trigger Infrastructure Pipeline

1. Navigate to **Actions** tab in GitHub repository
2. Select **Infrastructure Pipeline** workflow
3. Click **Run workflow** dropdown
4. Select branch (main or staging)
5. Click **Run workflow** button

### Step 2: Monitor Terraform Core Job

Watch the `terraform-core` job progress:

- [ ] Checkout code
- [ ] Check for Core Infra changes
- [ ] Setup Terraform
- [ ] Write terraform.tfvars
- [ ] Configure AWS credentials
- [ ] Ensure ECR Repository exists
- [ ] Terraform Apply (Core)

**Expected Duration**: 5-10 minutes

### Step 3: Verify Core Infrastructure Resources

#### Via AWS Console:

Check these resources were created/updated:

1. **VPC**:
   - Navigate to **VPC > Your VPCs**
   - Verify VPC with name from `TF_VAR_vpc_name` exists
   - Verify CIDR block matches `TF_VAR_vpc_cidr_block`

2. **Subnets**:
   - Navigate to **VPC > Subnets**
   - Verify 4 subnets exist (2 public, 2 private in different AZs)

3. **Internet Gateway**:
   - Navigate to **VPC > Internet Gateways**
   - Verify IGW with name from `TF_VAR_igw_name` exists and is attached to VPC

4. **Security Groups**:
   - Navigate to **EC2 > Security Groups**
   - Verify security groups for ALB, backend, and VPC endpoints exist

5. **S3 Bucket**:
   - Navigate to **S3**
   - Verify frontend bucket with name from `TF_VAR_frontend_bucket_name` exists

6. **CloudFront Distribution**:
   - Navigate to **CloudFront > Distributions**
   - Verify distribution exists with S3 origin

7. **ECR Repository**:
   - Navigate to **ECR > Repositories**
   - Verify repository with name from `TF_VAR_ECR_REPOSITORY_NAME` exists

#### Via AWS CLI:

```bash
# Verify VPC
aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=<vpc_name>" \
  --query 'Vpcs[*].[VpcId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# Verify ECR repository
aws ecr describe-repositories \
  --repository-names <ecr_repo_name> \
  --query 'repositories[*].[repositoryName,repositoryUri]' \
  --output table

# Verify S3 bucket
aws s3 ls | grep <frontend_bucket_name>
```

### Step 4: Monitor Terraform Service Job

Watch the `terraform-service` job progress (runs after core job completes):

- [ ] Checkout code
- [ ] Setup Terraform
- [ ] Write terraform.tfvars
- [ ] Configure AWS credentials
- [ ] Terraform Apply (Service)
- [ ] Get Terraform Outputs

**Expected Duration**: 5-10 minutes

### Step 5: Verify Service Infrastructure Resources

#### Via AWS Console:

1. **Application Load Balancer**:
   - Navigate to **EC2 > Load Balancers**
   - Verify ALB exists with target groups configured

2. **Auto Scaling Group**:
   - Navigate to **EC2 > Auto Scaling Groups**
   - Verify ASG exists with correct min/max/desired capacity
   - Verify launch template is attached

3. **Launch Template**:
   - Navigate to **EC2 > Launch Templates**
   - Verify launch template exists with latest version

#### Via AWS CLI:

```bash
# Verify ASG
aws autoscaling describe-auto-scaling-groups \
  --query 'AutoScalingGroups[*].[AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity]' \
  --output table

# Verify ALB
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[*].[LoadBalancerName,DNSName,State.Code]' \
  --output table
```

### Step 6: Verify Terraform Outputs

Check the workflow logs for the **Get Terraform Outputs** step:

**Expected Outputs**:
```
asg_name=<asg_name>
aws_region=ap-southeast-1
ecr_repository_url=<account_id>.dkr.ecr.ap-southeast-1.amazonaws.com/<repo_name>
backend_port=<port>
secrets_kms_key_arn=arn:aws:kms:ap-southeast-1:<account_id>:key/<key_id>
```

Verify all outputs are non-empty and valid.

### Step 7: Test Path Filtering for Core Infrastructure

1. Make a small change to a file in `.github/terraform/core/` (e.g., add a comment)
2. Commit and push the change
3. Trigger Infrastructure Pipeline manually
4. Verify the **Check for Core Infra changes** step detects the change
5. Verify **Terraform Apply (Core)** step executes

**Expected Log Output**:
```
core: true
```

### Step 8: Test Path Filtering - No Core Changes

1. Make a change to a file outside `.github/terraform/core/` (e.g., README.md)
2. Commit and push the change
3. Trigger Infrastructure Pipeline manually
4. Verify the **Check for Core Infra changes** step shows no changes
5. Verify **Terraform Apply (Core)** step is skipped (but service still runs)

**Expected Log Output**:
```
core: false
```

### Test 9.2 Success Criteria

- [x] Core infrastructure resources are provisioned
- [x] Service infrastructure resources are provisioned
- [x] Terraform outputs are captured correctly
- [x] Path filtering detects core infrastructure changes
- [x] Path filtering skips core apply when no changes detected
- [x] Service infrastructure always applies (depends on core outputs)

---

## Test 9.3: Application Pipeline Execution

**Objective**: Verify Application Pipeline triggers after CI success, backend and frontend jobs run in parallel, and all deployment steps complete successfully.

**Requirements Validated**: 2.1, 2.2, 2.4, 3.1, 3.2, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 5.1

### Step 1: Trigger Application Pipeline via Code Push

1. Make a small code change in `backend/src/` or `frontend/src/`
2. Commit and push to main branch or feature branch
3. Wait for CI Pipeline to complete successfully
4. Verify Application Pipeline triggers automatically

**Expected Behavior**: Application Pipeline starts within 1-2 minutes after CI success

### Step 2: Verify Workflow Trigger Condition

Check the Application Pipeline workflow logs:

**Expected Condition Check**:
```
github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success'
```

Verify the workflow only runs when CI succeeds.

### Step 3: Monitor Backend Build Job

Watch the `build-backend` job progress:

- [ ] Checkout code
- [ ] Configure AWS credentials
- [ ] Setup Terraform
- [ ] Read Infrastructure Outputs
- [ ] Compute Docker Context Hash
- [ ] Set Image Variables
- [ ] Login to Amazon ECR
- [ ] Check if Image Exists in ECR
- [ ] Set up Docker Buildx (if image doesn't exist)
- [ ] Build and Push Docker Image (if image doesn't exist)
- [ ] Update SSM Parameter with Backend Environment Variables
- [ ] Write terraform.tfvars
- [ ] Update Launch Template with New Image Tag
- [ ] Start ASG Instance Refresh
- [ ] Monitor ASG Instance Refresh

**Expected Duration**: 10-20 minutes (depending on whether Docker build is needed)

### Step 4: Monitor Frontend Build Job (Parallel)

Watch the `build-frontend` job progress (should start at same time as backend):

- [ ] Checkout code
- [ ] Setup Node.js
- [ ] Configure AWS credentials
- [ ] Install dependencies
- [ ] Build frontend
- [ ] Sync to S3
- [ ] Invalidate CloudFront cache

**Expected Duration**: 5-10 minutes

### Step 5: Verify Parallel Execution

Check the workflow visualization in GitHub Actions:

**Expected Behavior**:
- Both jobs start at approximately the same time
- Neither job waits for the other to complete
- Jobs run independently and can finish in any order

### Step 6: Verify Docker Image Build and Push

#### Via AWS Console:

1. Navigate to **ECR > Repositories**
2. Select the backend repository
3. Verify new image exists with tag matching the computed hash
4. Check image push timestamp matches workflow execution time

#### Via AWS CLI:

```bash
# List recent images
aws ecr describe-images \
  --repository-name <ecr_repo_name> \
  --query 'sort_by(imageDetails,&imagePushedAt)[-5:].[imageTags[0],imagePushedAt,imageSizeInBytes]' \
  --output table
```

**Expected Output**: Image with hash tag from workflow logs

### Step 7: Verify ASG Instance Refresh

#### Via AWS Console:

1. Navigate to **EC2 > Auto Scaling Groups**
2. Select the backend ASG
3. Click **Instance refresh** tab
4. Verify instance refresh completed successfully
5. Check **Status**: `Successful`
6. Verify new instances are running with updated launch template

#### Via AWS CLI:

```bash
# Check instance refresh status
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name <asg_name> \
  --query 'InstanceRefreshes[0].[Status,StatusReason,PercentageComplete]' \
  --output table

# Verify instances are running new image
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names <asg_name> \
  --query 'AutoScalingGroups[0].Instances[*].[InstanceId,HealthStatus,LifecycleState]' \
  --output table
```

**Expected Output**: 
- Status: `Successful`
- PercentageComplete: `100`
- All instances: `Healthy` and `InService`

### Step 8: Verify SSM Parameter Update

#### Via AWS CLI:

```bash
# Check SSM parameter was updated
aws ssm get-parameter \
  --name "/edutrust/backend/env" \
  --with-decryption \
  --query 'Parameter.[Name,LastModifiedDate,Version]' \
  --output table
```

**Expected Output**: LastModifiedDate matches workflow execution time

### Step 9: Verify Frontend Deployment to S3

#### Via AWS Console:

1. Navigate to **S3**
2. Select the frontend bucket
3. Verify files were uploaded
4. Check **Last modified** timestamps match workflow execution time

#### Via AWS CLI:

```bash
# List recent S3 objects
aws s3 ls s3://<frontend_bucket_name>/ --recursive --human-readable | tail -20
```

**Expected Output**: Files with recent timestamps

### Step 10: Verify CloudFront Cache Invalidation

#### Via AWS Console:

1. Navigate to **CloudFront > Distributions**
2. Select the distribution
3. Click **Invalidations** tab
4. Verify invalidation exists with path `/*`
5. Check **Status**: `Completed`

#### Via AWS CLI:

```bash
# List recent invalidations
aws cloudfront list-invalidations \
  --distribution-id <cloudfront_dist_id> \
  --query 'InvalidationList.Items[0].[Id,Status,CreateTime]' \
  --output table
```

**Expected Output**: Recent invalidation with Status `Completed`

### Step 11: Verify Application Accessibility

Test the deployed application:

```bash
# Test backend health endpoint
curl https://<backend_url>/health

# Test frontend (should return HTML)
curl https://<frontend_url>/
```

**Expected Output**: 
- Backend: `{"status": "healthy"}` or similar
- Frontend: HTML content

### Test 9.3 Success Criteria

- [x] Application Pipeline triggers automatically after CI success
- [x] Backend and frontend jobs run in parallel
- [x] Docker image is built and pushed to ECR
- [x] ASG instance refresh completes successfully
- [x] SSM parameter is updated with backend environment variables
- [x] Frontend assets are uploaded to S3
- [x] CloudFront cache is invalidated
- [x] Application is accessible and functional

---

## Test 9.4: Build Caching Behavior

**Objective**: Verify backend Docker build is skipped when image hash matches, and new image is built when backend code changes.

**Requirements Validated**: 3.3, 10.1

### Step 1: Push Code Change That Doesn't Affect Backend

1. Make a change to a file that doesn't affect backend build:
   - Frontend code: `frontend/src/app/page.tsx`
   - Documentation: `README.md`
   - Tests: `tests/workflows/test_*.py`
2. Commit and push to main branch
3. Wait for CI Pipeline to complete
4. Wait for Application Pipeline to trigger

### Step 2: Monitor Backend Build Job - Cache Hit

Watch the `build-backend` job logs:

**Expected Behavior in "Check if Image Exists in ECR" step**:
```
Image already exists in ECR, skipping build
exists=true
```

Verify these steps are **SKIPPED**:
- [ ] Set up Docker Buildx
- [ ] Build and Push Docker Image

**Expected Duration**: 5-8 minutes (much faster without Docker build)

### Step 3: Verify No New Image in ECR

#### Via AWS CLI:

```bash
# Check image count and timestamps
aws ecr describe-images \
  --repository-name <ecr_repo_name> \
  --query 'length(imageDetails)' \
  --output text
```

**Expected Output**: Image count unchanged from previous test

### Step 4: Verify ASG Still Updates

Even though Docker build was skipped, verify:

- [ ] Launch template is still updated (with same image tag)
- [ ] ASG instance refresh still runs
- [ ] Instances are healthy

**Rationale**: Launch template may have other changes (environment variables, instance type, etc.)

### Step 5: Push Code Change That Affects Backend

1. Make a change to backend source code:
   - Modify `backend/src/main.py` (e.g., add a comment or log statement)
2. Commit and push to main branch
3. Wait for CI Pipeline to complete
4. Wait for Application Pipeline to trigger

### Step 6: Monitor Backend Build Job - Cache Miss

Watch the `build-backend` job logs:

**Expected Behavior in "Compute Docker Context Hash" step**:
```
Computed hash: <new_hash_value>
```

Verify the hash is **DIFFERENT** from previous run.

**Expected Behavior in "Check if Image Exists in ECR" step**:
```
Image does not exist, will build
exists=false
```

Verify these steps **EXECUTE**:
- [ ] Set up Docker Buildx
- [ ] Build and Push Docker Image

**Expected Duration**: 15-25 minutes (includes Docker build time)

### Step 7: Verify New Image in ECR

#### Via AWS CLI:

```bash
# List images sorted by push time
aws ecr describe-images \
  --repository-name <ecr_repo_name> \
  --query 'sort_by(imageDetails,&imagePushedAt)[-2:].[imageTags[0],imagePushedAt]' \
  --output table
```

**Expected Output**: Two images with different tags and timestamps

### Step 8: Verify Content-Based Tagging

Check that image tags are SHA256 hashes:

```bash
# Verify tag format (should be 64-character hex string)
aws ecr describe-images \
  --repository-name <ecr_repo_name> \
  --query 'imageDetails[*].imageTags[0]' \
  --output text | head -1 | wc -c
```

**Expected Output**: `65` (64 characters + newline)

### Step 9: Test Rollback Capability

Verify previous images are preserved for rollback:

1. Navigate to **ECR > Repositories** in AWS Console
2. Select the backend repository
3. Verify multiple images exist with different tags
4. Verify old images are **NOT** deleted

**Expected Behavior**: All previous images remain in ECR for rollback

### Test 9.4 Success Criteria

- [x] Backend Docker build is skipped when image hash matches
- [x] New Docker image is built when backend code changes
- [x] Image tags are content-based SHA256 hashes
- [x] Previous images are preserved in ECR for rollback
- [x] ASG updates correctly with both cached and new images

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: AMI Pipeline - Temporary VPC Not Cleaned Up

**Symptoms**: Temporary VPC resources remain after workflow completes

**Diagnosis**:
```bash
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=PackerTempVPC"
```

**Solution**:
1. Manually delete subnet: `aws ec2 delete-subnet --subnet-id <subnet_id>`
2. Detach IGW: `aws ec2 detach-internet-gateway --internet-gateway-id <igw_id> --vpc-id <vpc_id>`
3. Delete IGW: `aws ec2 delete-internet-gateway --internet-gateway-id <igw_id>`
4. Delete VPC: `aws ec2 delete-vpc --vpc-id <vpc_id>`

#### Issue: Infrastructure Pipeline - Terraform State Lock

**Symptoms**: Workflow fails with "Error acquiring the state lock"

**Diagnosis**: Another Terraform operation is in progress or previous run didn't release lock

**Solution**:
1. Wait 5-10 minutes for lock to expire
2. If lock persists, manually release via DynamoDB:
   ```bash
   aws dynamodb delete-item \
     --table-name <terraform_lock_table> \
     --key '{"LockID": {"S": "<state_file_path>-md5"}}'
   ```

#### Issue: Application Pipeline - ASG Instance Refresh Fails

**Symptoms**: Instance refresh status shows "Failed" or "Cancelled"

**Diagnosis**:
```bash
aws autoscaling describe-instance-refreshes \
  --auto-scaling-group-name <asg_name> \
  --query 'InstanceRefreshes[0].[Status,StatusReason]'
```

**Common Causes**:
- Health check failures (instances not passing ALB health checks)
- Launch template configuration errors
- Insufficient capacity in availability zones

**Solution**:
1. Check instance logs in CloudWatch
2. Verify launch template configuration
3. Check ALB target group health checks
4. Manually start instance refresh with corrected configuration

#### Issue: Application Pipeline - Docker Build Fails

**Symptoms**: "Build and Push Docker Image" step fails

**Diagnosis**: Check workflow logs for Docker build errors

**Common Causes**:
- Syntax errors in Dockerfile
- Missing dependencies in requirements.txt
- Build context too large

**Solution**:
1. Test Docker build locally: `docker build -t test ./backend`
2. Fix errors in Dockerfile or source code
3. Push corrected code and retry

#### Issue: Frontend Deployment - CloudFront Invalidation Fails

**Symptoms**: "Invalidate CloudFront cache" step fails

**Diagnosis**: Check workflow logs for AWS CLI error message

**Common Causes**:
- Incorrect CloudFront distribution ID
- Insufficient IAM permissions
- CloudFront distribution not in "Deployed" state

**Solution**:
1. Verify distribution ID: `aws cloudfront list-distributions`
2. Check IAM permissions for `cloudfront:CreateInvalidation`
3. Manually create invalidation via AWS Console

---

## Test Results Documentation

### Test Execution Checklist

Use this checklist to track test completion:

- [ ] **Test 9.1**: AMI Pipeline execution
  - [ ] First run creates AMI with PackerHash tag
  - [ ] Temporary VPC resources cleaned up
  - [ ] Second run skips build when hash matches
  - [ ] Force build option works correctly

- [ ] **Test 9.2**: Infrastructure Pipeline execution
  - [ ] Core infrastructure provisioned
  - [ ] Service infrastructure provisioned
  - [ ] Terraform outputs captured
  - [ ] Path filtering works for core changes

- [ ] **Test 9.3**: Application Pipeline execution
  - [ ] Pipeline triggers after CI success
  - [ ] Backend and frontend jobs run in parallel
  - [ ] Docker image built and pushed to ECR
  - [ ] ASG instance refresh completes
  - [ ] Frontend assets uploaded to S3
  - [ ] CloudFront cache invalidated

- [ ] **Test 9.4**: Build caching behavior
  - [ ] Backend build skipped when hash matches
  - [ ] New image built when backend changes
  - [ ] Previous images preserved for rollback

### Test Results Template

Document test results using this template:

```markdown
## Test Execution Results

**Date**: YYYY-MM-DD
**Tester**: [Name]
**Environment**: [Staging/Production]
**Branch**: [main/staging]

### Test 9.1: AMI Pipeline
- Status: [PASS/FAIL]
- AMI ID: ami-xxxxx
- PackerHash: [hash_value]
- Duration: [minutes]
- Issues: [None/Description]

### Test 9.2: Infrastructure Pipeline
- Status: [PASS/FAIL]
- Core Apply: [PASS/FAIL]
- Service Apply: [PASS/FAIL]
- Outputs Captured: [YES/NO]
- Duration: [minutes]
- Issues: [None/Description]

### Test 9.3: Application Pipeline
- Status: [PASS/FAIL]
- Backend Build: [PASS/FAIL]
- Frontend Build: [PASS/FAIL]
- Parallel Execution: [YES/NO]
- ASG Refresh: [PASS/FAIL]
- Duration: [minutes]
- Issues: [None/Description]

### Test 9.4: Build Caching
- Status: [PASS/FAIL]
- Cache Hit Test: [PASS/FAIL]
- Cache Miss Test: [PASS/FAIL]
- Rollback Capability: [PASS/FAIL]
- Issues: [None/Description]

### Overall Assessment
- All Tests Passed: [YES/NO]
- Ready for Production: [YES/NO]
- Recommendations: [Description]
```

---

## Next Steps

After completing all staging tests successfully:

1. **Document Results**: Fill out the test results template above
2. **Review Findings**: Discuss any issues or improvements with the team
3. **Production Deployment**: If all tests pass, proceed with production deployment
4. **Monitor Production**: Watch first production deployment closely
5. **Cleanup**: The old workflow has been archived as `.github/workflows/deploy-ec2.yml.old` for reference

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS CLI Command Reference](https://docs.aws.amazon.com/cli/latest/reference/)
- [Packer Documentation](https://www.packer.io/docs)
