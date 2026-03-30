# Design Document: Remove S3 Frontend Bucket Infrastructure

## Overview

This design addresses the removal of S3-based frontend hosting infrastructure following the migration to AWS Amplify. The current architecture includes an S3 bucket for frontend assets, CloudFront distribution with dual origins (S3 and ALB), and associated IAM policies. Since Amplify now handles frontend hosting independently, these S3 resources are redundant and should be removed.

The design focuses on:
- Removing 6 S3-related Terraform resources from core infrastructure
- Updating CloudFront to route all traffic through the ALB backend origin
- Removing frontend_bucket_name variable and environment references
- Preserving all backend infrastructure and API routing functionality

This is a destructive infrastructure change that requires careful sequencing to avoid service disruption. The CloudFront distribution will be reconfigured to use only the ALB backend origin, with API traffic continuing to route through `/api/*` paths.

## Architecture

### Current Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│      CloudFront Distribution        │
│  ┌───────────────────────────────┐  │
│  │  Default: S3-Frontend         │  │
│  │  /api/*: ALB-Backend          │  │
│  └───────────────────────────────┘  │
└────────┬──────────────────┬─────────┘
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌──────────────┐
│  S3 Frontend    │  │  ALB Backend │
│  (via OAC)      │  │  (HTTPS)     │
└─────────────────┘  └──────────────┘
```

### Target Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│      CloudFront Distribution        │
│  ┌───────────────────────────────┐  │
│  │  Default: ALB-Backend         │  │
│  │  /api/*: ALB-Backend          │  │
│  └───────────────────────────────┘  │
└────────┬────────────────────────────┘
         │
         ▼
  ┌──────────────┐
  │  ALB Backend │
  │  (HTTPS)     │
  └──────────────┘
```

### Architectural Changes

1. **CloudFront Origin Simplification**: Remove S3-Frontend origin, retain only ALB-Backend origin
2. **Default Behavior Update**: Route default traffic to ALB-Backend instead of S3-Frontend
3. **Resource Cleanup**: Remove S3 bucket, OAC, bucket policy, and lifecycle configuration
4. **Configuration Cleanup**: Remove frontend_bucket_name variable from Terraform and CI/CD

The ALB backend will handle all incoming traffic, including any non-API requests. The `/api/*` path pattern will continue to route to the same ALB origin with API-specific caching and header forwarding settings.

## Components and Interfaces

### Terraform Resources to Remove

#### 3_storage_auth.tf

1. **aws_s3_bucket.frontend**
   - Resource: S3 bucket for frontend assets
   - Identifier: `var.frontend_bucket_name`
   - Dependencies: Referenced by lifecycle config, public access block, OAC, bucket policy

2. **aws_s3_bucket_lifecycle_configuration.frontend**
   - Resource: Lifecycle rules for multipart upload cleanup
   - Dependencies: Depends on aws_s3_bucket.frontend

3. **aws_s3_bucket_public_access_block.frontend**
   - Resource: Public access restrictions
   - Dependencies: Depends on aws_s3_bucket.frontend

4. **aws_cloudfront_origin_access_control.frontend**
   - Resource: OAC for CloudFront to access private S3 bucket
   - Dependencies: Referenced by CloudFront distribution origin

5. **data.aws_iam_policy_document.frontend_s3_policy**
   - Resource: IAM policy document for S3 bucket access
   - Dependencies: References aws_s3_bucket.frontend and aws_cloudfront_distribution.main

6. **aws_s3_bucket_policy.frontend**
   - Resource: Bucket policy allowing CloudFront access
   - Dependencies: Depends on aws_s3_bucket.frontend and data.aws_iam_policy_document.frontend_s3_policy

#### variables.tf

1. **variable.frontend_bucket_name**
   - Type: string
   - Usage: Referenced in aws_s3_bucket.frontend resource

### Terraform Resources to Modify

#### 4_edge.tf - aws_cloudfront_distribution.main

**Attributes to Remove:**
- `default_root_object = "index.html"` - No longer serving static files
- `origin` block with `origin_id = "S3-Frontend"` - Removing S3 origin
- `custom_error_response` block for 404 errors - No longer needed for SPA routing

**Attributes to Modify:**
- `default_cache_behavior.target_origin_id`: Change from `"S3-Frontend"` to `"ALB-Backend"`

**Attributes to Preserve:**
- `enabled`, `is_ipv6_enabled`, `web_acl_id`, `aliases` - Core distribution settings
- `origin` block with `origin_id = "ALB-Backend"` - Backend API origin
- `ordered_cache_behavior` for `/api/*` - API routing configuration
- `restrictions`, `viewer_certificate` - Security and SSL settings
- All other CloudFront configuration

### CI/CD Workflow Changes

#### .github/workflows/app.yml

**Environment Variables to Remove:**
- `TF_VAR_frontend_bucket_name: ${{ secrets.TF_VAR_frontend_bucket_name }}`

Location: `build-backend` job, `env` section

#### .github/workflows/infra.yml

**Environment Variables to Remove:**
- `TF_VAR_frontend_bucket_name: ${{ secrets.TF_VAR_frontend_bucket_name }}`

Locations:
- `terraform-core` job, `env` section
- `terraform-service` job, `env` section

### Resources to Preserve

All backend infrastructure must remain unchanged:
- ALB resources (load balancer, target groups, listeners)
- Route53 hosted zone and DNS records
- ACM certificates (ALB and CloudFront)
- ECR repository and lifecycle policies
- Cognito user pool and client
- S3 bucket for ALB logs (aws_s3_bucket.alb_logs)
- VPC, subnets, security groups, and networking resources
- WAF web ACL

## Data Models

### CloudFront Distribution Configuration

**Before:**
```hcl
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  
  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "S3-Frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }
  
  origin {
    domain_name = "api.${var.domain_name}"
    origin_id   = "ALB-Backend"
    custom_origin_config { ... }
  }
  
  default_cache_behavior {
    target_origin_id = "S3-Frontend"
    ...
  }
  
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    target_origin_id = "ALB-Backend"
    ...
  }
  
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }
}
```

**After:**
```hcl
resource "aws_cloudfront_distribution" "main" {
  enabled         = true
  is_ipv6_enabled = true
  
  origin {
    domain_name = "api.${var.domain_name}"
    origin_id   = "ALB-Backend"
    custom_origin_config { ... }
  }
  
  default_cache_behavior {
    target_origin_id = "ALB-Backend"
    ...
  }
  
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    target_origin_id = "ALB-Backend"
    ...
  }
}
```

### Variable Configuration

**Before (variables.tf):**
```hcl
variable "domain_name" { type = string }
variable "cognito_domain_prefix" { type = string }
variable "frontend_bucket_name" { type = string }
```

**After (variables.tf):**
```hcl
variable "domain_name" { type = string }
variable "cognito_domain_prefix" { type = string }
```

### CI/CD Environment Variables

**Before (workflows):**
```yaml
env:
  TF_VAR_domain_name: ${{ secrets.TF_VAR_domain_name }}
  TF_VAR_cognito_domain_prefix: ${{ secrets.TF_VAR_cognito_domain_prefix }}
  TF_VAR_frontend_bucket_name: ${{ secrets.TF_VAR_frontend_bucket_name }}
```

**After (workflows):**
```yaml
env:
  TF_VAR_domain_name: ${{ secrets.TF_VAR_domain_name }}
  TF_VAR_cognito_domain_prefix: ${{ secrets.TF_VAR_cognito_domain_prefix }}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: No Variable References in Terraform Files

*For any* Terraform file in the core infrastructure directory, the file should not contain any references to `var.frontend_bucket_name`.

**Validates: Requirements 2.2**

### Property 2: S3 Frontend Resources Removed

The Terraform configuration file `3_storage_auth.tf` should not contain any of the following resource definitions:
- `aws_s3_bucket.frontend`
- `aws_s3_bucket_lifecycle_configuration.frontend`
- `aws_s3_bucket_public_access_block.frontend`
- `aws_cloudfront_origin_access_control.frontend`
- `data.aws_iam_policy_document.frontend_s3_policy`
- `aws_s3_bucket_policy.frontend`

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**

### Property 3: Frontend Bucket Variable Removed

The Terraform configuration file `variables.tf` should not contain a variable declaration for `frontend_bucket_name`.

**Validates: Requirements 2.1**


### Property 4: CloudFront S3 Origin Removed

The CloudFront distribution configuration in `4_edge.tf` should not contain:
- An origin block with `origin_id = "S3-Frontend"`
- An `origin_access_control_id` attribute in any origin block
- A `default_root_object` attribute
- A `custom_error_response` block for 404 errors

**Validates: Requirements 3.1, 3.2, 3.3, 3.7**

### Property 5: CloudFront ALB Origin Preserved

The CloudFront distribution configuration in `4_edge.tf` should contain:
- An origin block with `origin_id = "ALB-Backend"` and `domain_name = "api.${var.domain_name}"`
- An `ordered_cache_behavior` block with `path_pattern = "/api/*"`

**Validates: Requirements 3.4, 3.5**

### Property 6: CloudFront Default Behavior Routes to ALB

The CloudFront distribution's `default_cache_behavior` block should have `target_origin_id = "ALB-Backend"`.

**Validates: Requirements 3.6, 7.1**


### Property 7: API Cache Behavior Configuration

The CloudFront distribution's `ordered_cache_behavior` block for `path_pattern = "/api/*"` should have:
- `target_origin_id = "ALB-Backend"`
- `allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]`
- `forwarded_values.query_string = true`
- `forwarded_values.headers = ["*"]`
- `forwarded_values.cookies.forward = "all"`
- `min_ttl = 0`, `default_ttl = 0`, `max_ttl = 0`

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**

### Property 8: Default Cache Behavior Configuration

The CloudFront distribution's `default_cache_behavior` block should have:
- `allowed_methods` including at least `["GET", "HEAD", "OPTIONS"]`
- `viewer_protocol_policy = "redirect-to-https"`

**Validates: Requirements 7.2, 7.3**

### Property 9: CI/CD Workflows Environment Variables Removed

The workflow files should not contain `TF_VAR_frontend_bucket_name` environment variable:
- `.github/workflows/app.yml` should not reference `TF_VAR_frontend_bucket_name`
- `.github/workflows/infra.yml` should not reference `TF_VAR_frontend_bucket_name`

**Validates: Requirements 4.1, 4.2**


## Error Handling

### Terraform State Management

**Issue**: Removing resources from Terraform configuration without proper state management can cause drift.

**Handling**:
- Before removing resource definitions, verify current Terraform state
- Use `terraform state list` to confirm resources exist in state
- Consider using `terraform state rm` for resources that should be preserved in AWS but removed from Terraform management
- For resources that should be destroyed, allow Terraform to handle deletion through normal apply process

### CloudFront Distribution Update

**Issue**: CloudFront distribution updates can take 15-30 minutes to propagate globally.

**Handling**:
- Expect extended deployment times when applying CloudFront changes
- Monitor CloudFront distribution status during deployment
- Verify distribution reaches "Deployed" status before considering changes complete
- Plan maintenance window if zero-downtime is required

**Issue**: Removing the S3 origin while it's the default target could cause service disruption.

**Handling**:
- Update default_cache_behavior target before removing S3 origin
- Terraform will handle the atomic update of the distribution
- CloudFront will continue serving from old configuration until new configuration is deployed


### S3 Bucket Deletion

**Issue**: S3 buckets cannot be deleted if they contain objects.

**Handling**:
- Verify S3 bucket is empty before attempting deletion
- If bucket contains objects, either:
  - Manually empty the bucket through AWS Console
  - Use AWS CLI: `aws s3 rm s3://bucket-name --recursive`
  - Add `force_destroy = true` to bucket resource temporarily (not recommended for production)
- Terraform will fail gracefully if bucket is not empty, preventing accidental data loss

**Issue**: S3 bucket policy references CloudFront distribution ARN, creating circular dependency.

**Handling**:
- Terraform dependency graph will handle proper deletion order
- Bucket policy will be removed before bucket deletion
- CloudFront distribution will be updated before bucket policy removal

### Variable Reference Errors

**Issue**: Removing variable declaration while references still exist will cause Terraform validation errors.

**Handling**:
- Remove all variable references before removing variable declaration
- Use grep/search to find all occurrences: `grep -r "var.frontend_bucket_name" .github/terraform/`
- Terraform validate will catch any remaining references before apply

### CI/CD Pipeline Failures

**Issue**: Removing environment variables from workflows while Terraform still expects them could cause pipeline failures.

**Handling**:
- Remove Terraform variable references first
- Then remove CI/CD environment variables
- Coordinate changes across multiple files in single commit
- Test workflow changes in feature branch before merging to main


## Testing Strategy

### Overview

This infrastructure change involves configuration file modifications rather than application code. Testing focuses on validating Terraform configuration correctness and verifying that the changes produce the expected infrastructure state.

### Static Analysis Testing

**Terraform Validation**:
- Run `terraform validate` to check syntax and configuration correctness
- Run `terraform fmt -check` to verify formatting standards
- Run `terraform plan` to preview changes before applying

**Configuration File Testing**:
- Use grep/ripgrep to verify absence of removed resources and variables
- Parse HCL files to validate CloudFront configuration structure
- Check that all variable references are resolved

### Unit Testing Approach

Unit tests will verify specific configuration requirements:

1. **Resource Absence Tests**: Verify specific S3 resources are not present in 3_storage_auth.tf
2. **Variable Absence Tests**: Verify frontend_bucket_name is not declared in variables.tf
3. **CloudFront Configuration Tests**: Verify CloudFront distribution has correct origin and cache behavior settings
4. **Workflow Configuration Tests**: Verify CI/CD workflows do not reference TF_VAR_frontend_bucket_name

These tests should be implemented as shell scripts or Python scripts that parse the Terraform and YAML files to verify the expected configuration state.


### Property-Based Testing Approach

For this infrastructure configuration change, property-based testing is less applicable than for application code. However, we can apply property-based thinking to validate configuration consistency:

**Property Test Library**: Not applicable for this infrastructure change. Configuration validation will use static analysis tools.

**Configuration Properties to Validate**:

1. **No Variable References Property** (Property 1):
   - Scan all `.tf` files in core infrastructure
   - Assert no file contains `var.frontend_bucket_name`
   - Implementation: Shell script with grep or Python script with HCL parser

2. **Resource Removal Property** (Property 2):
   - Parse `3_storage_auth.tf` with HCL parser
   - Assert none of the 6 S3-related resources are defined
   - Implementation: Python script with `python-hcl2` library

3. **CloudFront Configuration Properties** (Properties 4-8):
   - Parse `4_edge.tf` with HCL parser
   - Assert CloudFront distribution structure matches expected configuration
   - Verify origin configurations, cache behaviors, and removed attributes
   - Implementation: Python script with `python-hcl2` library

4. **Workflow Configuration Property** (Property 9):
   - Parse workflow YAML files
   - Assert `TF_VAR_frontend_bucket_name` is not present in env sections
   - Implementation: Python script with `pyyaml` library

### Integration Testing

**Terraform Plan Verification**:
- Run `terraform plan` in test environment
- Verify plan shows deletion of 6 S3-related resources
- Verify plan shows update (not replacement) of CloudFront distribution
- Verify plan shows no changes to preserved backend resources

**Terraform Apply in Test Environment**:
- Apply changes to a test/staging environment first
- Verify CloudFront distribution updates successfully
- Verify S3 resources are deleted
- Test API endpoints through CloudFront domain
- Verify `/api/*` requests route correctly to backend

### Manual Verification

**Post-Deployment Checks**:
1. Verify CloudFront distribution status is "Deployed"
2. Test API endpoints: `curl https://domain.com/api/health`
3. Verify non-API requests route to backend (should return backend response or 404)
4. Check AWS Console to confirm S3 frontend bucket is deleted
5. Verify CloudFront distribution has only one origin (ALB-Backend)
6. Check CloudFront cache behaviors match expected configuration

**Rollback Plan**:
- Keep previous Terraform state backup
- Document S3 bucket name and configuration for potential restoration
- Have CloudFront configuration backup available
- Test rollback procedure in staging environment before production deployment

