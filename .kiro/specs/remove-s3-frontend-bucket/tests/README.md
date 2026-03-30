# CloudFront Configuration Validation Tests

This directory contains configuration validation tests for the S3 frontend bucket removal spec.

## Test Files

### test_cloudfront_config.py

Validates CloudFront distribution configuration changes (Task 3.3).

**Properties Validated:**
- Property 4: CloudFront S3 Origin Removed
- Property 5: CloudFront ALB Origin Preserved
- Property 6: CloudFront Default Behavior Routes to ALB
- Property 7: API Cache Behavior Configuration
- Property 8: Default Cache Behavior Configuration

**Requirements Validated:** 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3

**Usage:**
```bash
python .kiro/specs/remove-s3-frontend-bucket/tests/test_cloudfront_config.py
```

**Exit Codes:**
- 0: All properties validated successfully
- 1: One or more property validations failed

### test_workflow_config.py

Validates CI/CD workflow configuration changes (Task 4.3).

**Properties Validated:**
- Property 9: CI/CD Workflows Environment Variables Removed

**Requirements Validated:** 4.1, 4.2

**Usage:**
```bash
python .kiro/specs/remove-s3-frontend-bucket/tests/test_workflow_config.py
```

**Exit Codes:**
- 0: All properties validated successfully
- 1: One or more property validations failed

## Test Approach

These tests use static analysis to validate Terraform configuration files without creating any AWS resources. The tests parse HCL (HashiCorp Configuration Language) files and verify that the configuration matches the expected structure defined in the design document.

## Dependencies

The tests use only Python standard library modules (no external dependencies required):
- `re` - Regular expression parsing for HCL content
- `pathlib` - File path handling
- `sys` - Exit code handling
- `typing` - Type hints

## Running All Tests

To run all configuration validation tests:

```bash
# Run CloudFront configuration test
python .kiro/specs/remove-s3-frontend-bucket/tests/test_cloudfront_config.py

# Run workflow configuration test
python .kiro/specs/remove-s3-frontend-bucket/tests/test_workflow_config.py
```

## Test Output

Each test provides detailed output showing:
- Property name being validated
- Pass/Fail status
- Detailed message explaining the validation result
- Summary of total passed/failed validations

Example output:
```
================================================================================
CloudFront Configuration Validation Test
================================================================================

✓ PASS: Property 4: CloudFront S3 Origin Removed
  Property 4 validated: S3 origin and related attributes removed

✓ PASS: Property 5: CloudFront ALB Origin Preserved
  Property 5 validated: ALB origin and API cache behavior preserved

...

================================================================================
All properties validated successfully!
================================================================================
```
