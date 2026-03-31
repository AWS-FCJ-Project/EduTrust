"""
Unit tests for S3 Frontend Bucket Removal from Terraform configuration.

Tests validate that S3 frontend resources have been removed from the Terraform
configuration as specified in the Remove S3 Frontend Bucket Infrastructure spec.

**Property 2: S3 Frontend Resources Removed**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
"""

from pathlib import Path


def read_terraform_file(file_path: str) -> str:
    """Read and return the contents of a Terraform file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Terraform file not found: {file_path}")

    with open(path, "r") as f:
        return f.read()


def test_s3_frontend_bucket_removed():
    """
    Test that aws_s3_bucket.frontend resource is not present in 3_storage_auth.tf.

    **Validates: Requirement 1.1**
    """
    content = read_terraform_file(".github/terraform/core/3_storage_auth.tf")

    assert (
        'resource "aws_s3_bucket" "frontend"' not in content
    ), "aws_s3_bucket.frontend resource should be removed from 3_storage_auth.tf"


def test_s3_frontend_lifecycle_configuration_removed():
    """
    Test that aws_s3_bucket_lifecycle_configuration.frontend is not present.

    **Validates: Requirement 1.2**
    """
    content = read_terraform_file(".github/terraform/core/3_storage_auth.tf")

    assert (
        'resource "aws_s3_bucket_lifecycle_configuration" "frontend"' not in content
    ), "aws_s3_bucket_lifecycle_configuration.frontend should be removed from 3_storage_auth.tf"


def test_s3_frontend_public_access_block_removed():
    """
    Test that aws_s3_bucket_public_access_block.frontend is not present.

    **Validates: Requirement 1.3**
    """
    content = read_terraform_file(".github/terraform/core/3_storage_auth.tf")

    assert (
        'resource "aws_s3_bucket_public_access_block" "frontend"' not in content
    ), "aws_s3_bucket_public_access_block.frontend should be removed from 3_storage_auth.tf"


def test_cloudfront_oac_frontend_removed():
    """
    Test that aws_cloudfront_origin_access_control.frontend is not present.

    **Validates: Requirement 1.4**
    """
    content = read_terraform_file(".github/terraform/core/3_storage_auth.tf")

    assert (
        'resource "aws_cloudfront_origin_access_control" "frontend"' not in content
    ), "aws_cloudfront_origin_access_control.frontend should be removed from 3_storage_auth.tf"


def test_frontend_s3_policy_document_removed():
    """
    Test that data.aws_iam_policy_document.frontend_s3_policy is not present.

    **Validates: Requirement 1.5**
    """
    content = read_terraform_file(".github/terraform/core/3_storage_auth.tf")

    assert (
        'data "aws_iam_policy_document" "frontend_s3_policy"' not in content
    ), "data.aws_iam_policy_document.frontend_s3_policy should be removed from 3_storage_auth.tf"


def test_s3_frontend_bucket_policy_removed():
    """
    Test that aws_s3_bucket_policy.frontend is not present.

    **Validates: Requirement 1.6**
    """
    content = read_terraform_file(".github/terraform/core/3_storage_auth.tf")

    assert (
        'resource "aws_s3_bucket_policy" "frontend"' not in content
    ), "aws_s3_bucket_policy.frontend should be removed from 3_storage_auth.tf"


def test_all_s3_frontend_resources_removed():
    """
    Comprehensive test that verifies all 6 S3 frontend resources are removed.

    **Property 2: S3 Frontend Resources Removed**
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
    """
    content = read_terraform_file(".github/terraform/core/3_storage_auth.tf")

    # List of all S3 frontend resources that should NOT be present
    forbidden_resources = [
        'resource "aws_s3_bucket" "frontend"',
        'resource "aws_s3_bucket_lifecycle_configuration" "frontend"',
        'resource "aws_s3_bucket_public_access_block" "frontend"',
        'resource "aws_cloudfront_origin_access_control" "frontend"',
        'data "aws_iam_policy_document" "frontend_s3_policy"',
        'resource "aws_s3_bucket_policy" "frontend"',
    ]

    found_resources = []
    for resource in forbidden_resources:
        if resource in content:
            found_resources.append(resource)

    assert (
        len(found_resources) == 0
    ), f"Found {len(found_resources)} S3 frontend resources that should be removed: {found_resources}"
