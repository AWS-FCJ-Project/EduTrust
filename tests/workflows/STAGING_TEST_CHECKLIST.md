# Staging Test Quick Reference Checklist

## Pre-Test Setup

- [ ] AWS Console access verified
- [ ] AWS CLI configured locally
- [ ] GitHub Actions access confirmed
- [ ] All GitHub secrets configured

## Test 9.1: AMI Pipeline

### First Run
- [ ] Trigger AMI Pipeline (workflow_dispatch, force_build=false)
- [ ] Verify AMI created with PackerHash tag
- [ ] Verify temporary VPC cleaned up
- [ ] Record AMI ID: ________________
- [ ] Record PackerHash: ________________

### Second Run (Hash Match)
- [ ] Trigger AMI Pipeline again (force_build=false)
- [ ] Verify build skipped (logs show "Skipping build")
- [ ] Verify duration < 3 minutes

### Force Build Test
- [ ] Trigger AMI Pipeline (force_build=true)
- [ ] Verify build proceeds despite matching hash
- [ ] Verify old AMI deregistered

**Status**: [ ] PASS [ ] FAIL

---

## Test 9.2: Infrastructure Pipeline

### Core Infrastructure
- [ ] Trigger Infrastructure Pipeline (workflow_dispatch)
- [ ] Verify terraform-core job completes
- [ ] Verify VPC created
- [ ] Verify subnets created (2 public, 2 private)
- [ ] Verify IGW created and attached
- [ ] Verify security groups created
- [ ] Verify S3 bucket created
- [ ] Verify CloudFront distribution created
- [ ] Verify ECR repository created

### Service Infrastructure
- [ ] Verify terraform-service job completes
- [ ] Verify ALB created
- [ ] Verify ASG created
- [ ] Verify launch template created
- [ ] Verify outputs captured:
  - [ ] asg_name
  - [ ] ecr_repository_url
  - [ ] secrets_kms_key_arn
  - [ ] aws_region
  - [ ] backend_port

### Path Filtering
- [ ] Make change to `.github/terraform/core/` file
- [ ] Trigger pipeline
- [ ] Verify core apply executes
- [ ] Make change to non-core file
- [ ] Trigger pipeline
- [ ] Verify core apply skipped

**Status**: [ ] PASS [ ] FAIL

---

## Test 9.3: Application Pipeline

### Trigger Test
- [ ] Push code change to main/feature branch
- [ ] Verify CI Pipeline completes successfully
- [ ] Verify Application Pipeline triggers automatically
- [ ] Record trigger delay: ________ seconds

### Backend Build Job
- [ ] Verify job starts
- [ ] Verify infrastructure outputs read
- [ ] Verify Docker context hash computed
- [ ] Verify ECR login successful
- [ ] Verify image existence check
- [ ] Verify Docker build (if needed)
- [ ] Verify image push to ECR
- [ ] Verify SSM parameter updated
- [ ] Verify launch template updated
- [ ] Verify ASG instance refresh started
- [ ] Verify ASG instance refresh completed
- [ ] Record image tag: ________________

### Frontend Build Job
- [ ] Verify job starts (parallel with backend)
- [ ] Verify Node.js setup
- [ ] Verify npm install
- [ ] Verify npm run build
- [ ] Verify S3 sync
- [ ] Verify CloudFront invalidation

### Parallel Execution
- [ ] Verify both jobs start at same time
- [ ] Verify neither job waits for the other
- [ ] Record backend duration: ________ minutes
- [ ] Record frontend duration: ________ minutes

### Verification
- [ ] Verify new image in ECR
- [ ] Verify ASG instances healthy
- [ ] Verify frontend files in S3
- [ ] Verify CloudFront invalidation completed
- [ ] Test backend endpoint: `curl https://<backend_url>/health`
- [ ] Test frontend: `curl https://<frontend_url>/`

**Status**: [ ] PASS [ ] FAIL

---

## Test 9.4: Build Caching

### Cache Hit Test (No Backend Changes)
- [ ] Push change to frontend or docs (not backend)
- [ ] Wait for CI success
- [ ] Wait for Application Pipeline trigger
- [ ] Verify "Image already exists in ECR, skipping build"
- [ ] Verify Docker build steps skipped
- [ ] Verify ASG still updates
- [ ] Record duration: ________ minutes

### Cache Miss Test (Backend Changes)
- [ ] Push change to backend source code
- [ ] Wait for CI success
- [ ] Wait for Application Pipeline trigger
- [ ] Verify new hash computed
- [ ] Verify "Image does not exist, will build"
- [ ] Verify Docker build executes
- [ ] Verify new image pushed to ECR
- [ ] Record new image tag: ________________
- [ ] Record duration: ________ minutes

### Rollback Capability
- [ ] Verify multiple images in ECR
- [ ] Verify old images NOT deleted
- [ ] Verify image tags are 64-char SHA256 hashes
- [ ] Count images in ECR: ________ images

**Status**: [ ] PASS [ ] FAIL

---

## Overall Test Results

| Test | Status | Duration | Issues |
|------|--------|----------|--------|
| 9.1 AMI Pipeline | [ ] PASS [ ] FAIL | _____ min | ____________ |
| 9.2 Infrastructure Pipeline | [ ] PASS [ ] FAIL | _____ min | ____________ |
| 9.3 Application Pipeline | [ ] PASS [ ] FAIL | _____ min | ____________ |
| 9.4 Build Caching | [ ] PASS [ ] FAIL | _____ min | ____________ |

**All Tests Passed**: [ ] YES [ ] NO

**Ready for Production**: [ ] YES [ ] NO

**Tester**: ________________
**Date**: ________________
**Environment**: ________________

---

## Quick AWS CLI Commands

### Check AMI
```bash
aws ec2 describe-images --owners self --filters "Name=tag:Name,Values=EduTrust-Base-AMI" --query 'Images[*].[ImageId,Tags[?Key==`PackerHash`].Value|[0]]' --output table
```

### Check Temporary VPCs
```bash
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=PackerTempVPC" --query 'Vpcs[*].VpcId' --output table
```

### Check ECR Images
```bash
aws ecr describe-images --repository-name <repo_name> --query 'sort_by(imageDetails,&imagePushedAt)[-5:].[imageTags[0],imagePushedAt]' --output table
```

### Check ASG Status
```bash
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <asg_name> --query 'AutoScalingGroups[0].Instances[*].[InstanceId,HealthStatus,LifecycleState]' --output table
```

### Check Instance Refresh
```bash
aws autoscaling describe-instance-refreshes --auto-scaling-group-name <asg_name> --query 'InstanceRefreshes[0].[Status,PercentageComplete,StatusReason]' --output table
```

### Check CloudFront Invalidations
```bash
aws cloudfront list-invalidations --distribution-id <dist_id> --query 'InvalidationList.Items[0].[Id,Status,CreateTime]' --output table
```

### Check S3 Files
```bash
aws s3 ls s3://<bucket_name>/ --recursive --human-readable | tail -20
```
