"""
Unit tests for Frontend Bucket Variable Removal from Terraform configuration.

Tests validate that the frontend_bucket_name variable and all its references
have been removed from the Terraform configuration as specified in the
Remove S3 Frontend Bucket Infrastructure spec.

**Property 1: No Variable References in Terraform Files**
**Property 3: Frontend Bucket Variable Removed**
**Validates: Requirements 2.1, 2.2**
"""

import re
from pathlib import Path


def read_terraform_file(file_path: str) -> str:
    """Read and return the contents of a Terraform file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Terraform file not found: {file_path}")

    with open(path, "r") as f:
        return f.read()


def get_all_terraform_files(directory: str) -> list[Path]:
    """Get all .tf files in the specified directory."""
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    return list(path.glob("*.tf"))


def test_no_frontend_bucket_variable_references_in_terraform_files():
    """
    Test that no .tf files in .github/terraform/core/ contain references to var.frontend_bucket_name.

    **Property 1: No Variable References in Terraform Files**
    **Validates: Requirement 2.2**
    """
    terraform_dir = ".github/terraform/core"
    tf_files = get_all_terraform_files(terraform_dir)

    assert len(tf_files) > 0, f"No .tf files found in {terraform_dir}"

    files_with_references = []

    for tf_file in tf_files:
        content = tf_file.read_text()

        # Check for var.frontend_bucket_name references
        if "var.frontend_bucket_name" in content:
            files_with_references.append(tf_file.name)

    assert (
        len(files_with_references) == 0
    ), f"Found var.frontend_bucket_name references in: {', '.join(files_with_references)}"


def test_frontend_bucket_variable_not_declared():
    """
    Test that variables.tf does not declare a frontend_bucket_name variable.

    **Property 3: Frontend Bucket Variable Removed**
    **Validates: Requirement 2.1**
    """
    content = read_terraform_file(".github/terraform/core/variables.tf")

    # Check for variable declaration using regex to match various formatting styles
    variable_pattern = r'variable\s+"frontend_bucket_name"'

    assert not re.search(
        variable_pattern, content
    ), "frontend_bucket_name variable should not be declared in variables.tf"


def test_no_frontend_bucket_name_string_in_variables():
    """
    Test that the string 'frontend_bucket_name' does not appear anywhere in variables.tf.

    This is a stricter test that catches any mention of the variable name.

    **Validates: Requirement 2.1**
    """
    content = read_terraform_file(".github/terraform/core/variables.tf")

    assert (
        "frontend_bucket_name" not in content
    ), "The string 'frontend_bucket_name' should not appear in variables.tf"


def test_comprehensive_variable_removal():
    """
    Comprehensive test that verifies frontend_bucket_name variable is completely removed.

    Scans all .tf files in the core directory and verifies:
    1. No variable declaration exists
    2. No variable references exist

    **Property 1: No Variable References in Terraform Files**
    **Property 3: Frontend Bucket Variable Removed**
    **Validates: Requirements 2.1, 2.2**
    """
    terraform_dir = ".github/terraform/core"
    tf_files = get_all_terraform_files(terraform_dir)

    issues = []

    for tf_file in tf_files:
        content = tf_file.read_text()

        # Check for variable declaration
        if 'variable "frontend_bucket_name"' in content:
            issues.append(f"{tf_file.name}: Contains variable declaration")

        # Check for variable references
        if "var.frontend_bucket_name" in content:
            issues.append(f"{tf_file.name}: Contains variable reference")

    assert (
        len(issues) == 0
    ), f"Found {len(issues)} issues with frontend_bucket_name variable:\n" + "\n".join(
        issues
    )
