# Terraform Configuration Tests

This directory contains unit tests for validating Terraform configuration files.

## Test Files

### test_s3_frontend_removal.py

Tests that validate the removal of S3 frontend bucket infrastructure from Terraform configuration.

**Property 2: S3 Frontend Resources Removed**

Validates that the following resources are NOT present in `.github/terraform/core/3_storage_auth.tf`:
- `aws_s3_bucket.frontend`
- `aws_s3_bucket_lifecycle_configuration.frontend`
- `aws_s3_bucket_public_access_block.frontend`
- `aws_cloudfront_origin_access_control.frontend`
- `data.aws_iam_policy_document.frontend_s3_policy`
- `aws_s3_bucket_policy.frontend`

**Requirements Validated:** 1.1, 1.2, 1.3, 1.4, 1.5, 1.6

## Running Tests

Run all terraform configuration tests:
```bash
pytest tests/terraform/ -v
```

Run specific test file:
```bash
pytest tests/terraform/test_s3_frontend_removal.py -v
```

## Test Approach

These tests use a simple text-based validation approach:
1. Read the Terraform configuration file
2. Search for specific resource declarations
3. Assert that removed resources are not present in the file

This approach is sufficient for validating configuration file changes and does not require HCL parsing libraries.
