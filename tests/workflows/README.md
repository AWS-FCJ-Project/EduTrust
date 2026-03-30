# Workflow Tests and Documentation

This directory contains unit tests and staging test documentation for GitHub Actions workflow files.

## Overview

This directory includes:

1. **Unit Tests** - Automated tests that validate workflow file structure
2. **Staging Test Documentation** - Manual testing guides for integration testing

### Unit Tests

These tests validate the structure and configuration of workflow files to ensure they conform to the CI/CD Pipeline Refactor specification. The tests parse workflow YAML files and verify:

- Trigger configurations
- Job definitions and dependencies
- Required outputs
- Absence of application build steps in infrastructure workflows

### Staging Test Documentation

Comprehensive guides for manual integration testing of workflows in a staging environment before production deployment.

## Running Tests

### Install Dependencies

```bash
pip install -r tests/requirements.txt
```

### Run All Workflow Tests

```bash
pytest tests/workflows/ -v
```

### Run Specific Test File

```bash
pytest tests/workflows/test_infra_pipeline.py -v
```

### Run Specific Test

```bash
pytest tests/workflows/test_infra_pipeline.py::test_infra_pipeline_manual_trigger_only -v
```

## Test Files

### `test_infra_pipeline.py`

Tests for the Infrastructure Pipeline workflow (`.github/workflows/infra.yml`).

**Tests:**
- `test_infra_pipeline_manual_trigger_only` - Validates Requirement 1.3
- `test_terraform_core_job_applies_core_infrastructure` - Validates Requirement 1.1
- `test_terraform_service_job_applies_service_infrastructure` - Validates Requirement 1.2
- `test_terraform_service_job_defines_required_outputs` - Validates Requirement 1.5
- `test_no_docker_build_steps` - Validates Requirement 1.4
- `test_no_npm_build_steps` - Validates Requirement 1.4

## Test Structure

Each test follows this pattern:

1. Load the workflow YAML file
2. Parse and validate specific sections
3. Assert expected structure and configuration
4. Provide clear error messages on failure

## Adding New Tests

To add tests for a new workflow:

1. Create a new test file: `test_<workflow_name>.py`
2. Import the `load_workflow` helper function
3. Write test functions following the naming convention: `test_<feature_description>`
4. Document which requirements each test validates

## Staging Test Documentation

### Quick Start

For staging environment testing, use these documents:

1. **`TASK_9_SUMMARY.md`** - Overview and context for Task 9 testing
2. **`STAGING_TEST_GUIDE.md`** - Comprehensive step-by-step testing guide (500+ lines)
3. **`STAGING_TEST_CHECKLIST.md`** - Quick reference checklist for rapid execution

### Test Scenarios

The staging tests cover:

- **Test 9.1**: AMI Pipeline execution (Requirements 6.1-6.4)
- **Test 9.2**: Infrastructure Pipeline execution (Requirements 1.1-1.3, 1.5, 9.3-9.4)
- **Test 9.3**: Application Pipeline execution (Requirements 2.1-2.2, 2.4, 3.1-3.2, 3.4-3.5, 4.1-4.4, 5.1)
- **Test 9.4**: Build caching behavior (Requirements 3.3, 10.1)

### Prerequisites for Staging Tests

- GitHub Actions access with workflow trigger permissions
- AWS Console access (EC2, VPC, ECR, S3, CloudFront, ALB, ASG, SSM, KMS)
- AWS CLI configured locally
- All GitHub secrets configured

### Expected Duration

- Full test suite: ~60-90 minutes
- Individual tests: 1-25 minutes each

See `STAGING_TEST_GUIDE.md` for detailed instructions.

## CI Integration

These unit tests should be run in the CI pipeline to catch workflow configuration errors before merge. Staging tests are executed manually before production deployment.
