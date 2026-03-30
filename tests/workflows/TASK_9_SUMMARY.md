# Task 9: Test New Workflows in Staging Environment - Summary

## Overview

Task 9 involves comprehensive integration testing of the three new CI/CD workflows in a staging environment before production deployment. This is a **manual testing task** that requires human interaction with GitHub Actions and AWS Console.

## What Was Delivered

### 1. Comprehensive Testing Guide (`STAGING_TEST_GUIDE.md`)

A detailed 500+ line testing guide that provides:

- **Step-by-step instructions** for each test scenario
- **AWS Console verification steps** with screenshots guidance
- **AWS CLI commands** for automated verification
- **Expected outputs** for each step
- **Troubleshooting section** for common issues
- **Test results documentation template**

### 2. Quick Reference Checklist (`STAGING_TEST_CHECKLIST.md`)

A condensed checklist format for quick execution:

- **Pre-test setup checklist**
- **Per-test checklists** with checkboxes
- **Quick AWS CLI commands** reference
- **Results tracking table**

## Test Scenarios Covered

### Test 9.1: AMI Pipeline Execution
**Requirements**: 6.1, 6.2, 6.3, 6.4

Tests:
- ✅ AMI creation with PackerHash tag
- ✅ Temporary VPC resource cleanup
- ✅ Build skip when hash matches (idempotency)
- ✅ Force build option

### Test 9.2: Infrastructure Pipeline Execution
**Requirements**: 1.1, 1.2, 1.3, 1.5, 9.3, 9.4

Tests:
- ✅ Core infrastructure provisioning (VPC, subnets, IGW, S3, CloudFront, ECR)
- ✅ Service infrastructure provisioning (ALB, ASG, launch template)
- ✅ Terraform output capture
- ✅ Path filtering for core infrastructure changes

### Test 9.3: Application Pipeline Execution
**Requirements**: 2.1, 2.2, 2.4, 3.1, 3.2, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 5.1

Tests:
- ✅ Automatic trigger after CI success
- ✅ Parallel backend and frontend builds
- ✅ Docker image build and push to ECR
- ✅ ASG instance refresh deployment
- ✅ SSM parameter update
- ✅ Frontend S3 upload
- ✅ CloudFront cache invalidation
- ✅ Application accessibility

### Test 9.4: Build Caching Behavior
**Requirements**: 3.3, 10.1

Tests:
- ✅ Build skip when Docker image hash matches
- ✅ New build when backend code changes
- ✅ Content-based image tagging
- ✅ Image preservation for rollback

## How to Execute Tests

### Option 1: Detailed Guide (Recommended for First-Time Testing)

Use `STAGING_TEST_GUIDE.md` for comprehensive instructions:

```bash
# Open the detailed guide
cat tests/workflows/STAGING_TEST_GUIDE.md
```

This guide includes:
- Detailed explanations of what to verify
- Multiple verification methods (Console + CLI)
- Expected outputs and log messages
- Troubleshooting for common issues

### Option 2: Quick Checklist (For Experienced Testers)

Use `STAGING_TEST_CHECKLIST.md` for rapid execution:

```bash
# Open the quick checklist
cat tests/workflows/STAGING_TEST_CHECKLIST.md
```

This checklist provides:
- Checkbox format for tracking progress
- Quick AWS CLI commands
- Results tracking table

## Test Execution Order

**IMPORTANT**: Execute tests in this order:

1. **Test 9.1** (AMI Pipeline) - Creates base AMI
2. **Test 9.2** (Infrastructure Pipeline) - Provisions AWS resources
3. **Test 9.3** (Application Pipeline) - Deploys application code
4. **Test 9.4** (Build Caching) - Validates optimization behavior

## Prerequisites

Before starting tests, ensure:

- [ ] GitHub Actions access with workflow trigger permissions
- [ ] AWS Console access with read permissions for:
  - EC2, VPC, ECR, S3, CloudFront, ALB, ASG, SSM, KMS
- [ ] AWS CLI configured locally
- [ ] All GitHub secrets configured:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `TERRAFORM_VARIABLES`
  - `BACKEND_ENV_FILE`
  - `S3_BUCKET`
  - `CLOUDFRONT_DIST_ID`

## Expected Test Duration

| Test | Duration | Notes |
|------|----------|-------|
| 9.1 AMI Pipeline (First Run) | 10-15 min | Includes Packer build |
| 9.1 AMI Pipeline (Second Run) | 1-2 min | Build skipped |
| 9.2 Infrastructure Pipeline | 10-20 min | Terraform apply for both tiers |
| 9.3 Application Pipeline | 15-25 min | Includes Docker build |
| 9.4 Build Caching (Cache Hit) | 5-8 min | Docker build skipped |
| 9.4 Build Caching (Cache Miss) | 15-25 min | Includes Docker build |
| **Total** | **~60-90 min** | Full test suite |

## Success Criteria

All tests must pass before production deployment:

- ✅ All 4 test scenarios complete successfully
- ✅ No manual cleanup required (resources auto-cleaned)
- ✅ Application accessible and functional after deployment
- ✅ Rollback capability verified (multiple ECR images preserved)
- ✅ No errors in workflow logs
- ✅ All AWS resources in expected state

## What Happens After Testing

### If All Tests Pass:

1. Document results using template in `STAGING_TEST_GUIDE.md`
2. Review findings with team
3. Proceed with production deployment
4. Monitor first production deployment closely
5. The old workflow has been archived as `.github/workflows/deploy-ec2.yml.old` for reference

### If Tests Fail:

1. Document failure details
2. Use troubleshooting section in `STAGING_TEST_GUIDE.md`
3. Fix issues in workflow files
4. Re-run failed tests
5. Do not proceed to production until all tests pass

## Key Testing Principles

### Manual Testing Required

These are **integration tests** that require:
- Manual workflow triggering via GitHub Actions UI
- Visual verification in AWS Console
- Human judgment for "application is functional"
- Real AWS resources (not mocked)

### Why Manual Testing?

- GitHub Actions workflows cannot be unit tested in isolation
- AWS resource provisioning requires real infrastructure
- End-to-end validation requires human verification
- Staging environment mirrors production behavior

### Automation Limitations

While the workflows themselves are automated, the **testing process** is manual because:
- GitHub Actions doesn't provide API for workflow testing
- AWS resource verification requires Console access
- Application functionality testing requires human judgment

## Files Created

```
tests/workflows/
├── STAGING_TEST_GUIDE.md          # Comprehensive testing guide (500+ lines)
├── STAGING_TEST_CHECKLIST.md      # Quick reference checklist
└── TASK_9_SUMMARY.md              # This file
```

## Additional Resources

- **Design Document**: `.kiro/specs/ci-cd-pipeline-refactor/design.md`
- **Requirements**: `.kiro/specs/ci-cd-pipeline-refactor/requirements.md`
- **Workflow Files**:
  - `.github/workflows/ami.yml`
  - `.github/workflows/infra.yml`
  - `.github/workflows/app.yml`

## Questions or Issues?

If you encounter issues during testing:

1. Check the **Troubleshooting** section in `STAGING_TEST_GUIDE.md`
2. Review workflow logs in GitHub Actions
3. Check AWS CloudWatch logs for application errors
4. Verify all GitHub secrets are correctly configured
5. Ensure AWS account has sufficient permissions and quotas

## Next Steps

1. **Review** the testing guides created
2. **Schedule** a testing session with appropriate access
3. **Execute** tests in order (9.1 → 9.2 → 9.3 → 9.4)
4. **Document** results using provided template
5. **Decide** on production deployment readiness

---

**Task Status**: ✅ Testing documentation complete

**Note**: This task provides the testing framework and instructions. The actual test execution must be performed by a human with GitHub Actions and AWS Console access.
