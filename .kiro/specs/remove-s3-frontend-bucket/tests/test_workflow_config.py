#!/usr/bin/env python3
"""
Configuration validation test for CI/CD workflow changes.

This test validates Property 9 from the design document:
- Property 9: CI/CD Workflows Environment Variables Removed

Validates: Requirements 4.1, 4.2
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def check_file_for_variable(
    file_path: Path, variable_name: str
) -> Tuple[bool, List[str]]:
    """
    Check if a file contains the specified environment variable.

    Args:
        file_path: Path to the file to check
        variable_name: Name of the environment variable to search for

    Returns:
        Tuple of (found, locations) where:
        - found: True if variable was found, False otherwise
        - locations: List of line numbers where variable was found
    """
    if not file_path.exists():
        return False, []

    content = file_path.read_text()
    locations = []

    # Search for the variable in the content
    # Pattern matches: TF_VAR_frontend_bucket_name: or TF_VAR_frontend_bucket_name =
    pattern = rf"{re.escape(variable_name)}\s*[:=]"

    for line_num, line in enumerate(content.split("\n"), start=1):
        if re.search(pattern, line):
            locations.append(line_num)

    return len(locations) > 0, locations


def validate_property_9_workflow_env_vars_removed() -> Tuple[bool, str]:
    """
    Property 9: CI/CD Workflows Environment Variables Removed

    Validates: Requirements 4.1, 4.2

    The workflow files should not contain TF_VAR_frontend_bucket_name environment variable:
    - .github/workflows/app.yml should not reference TF_VAR_frontend_bucket_name
    - .github/workflows/infra.yml should not reference TF_VAR_frontend_bucket_name
    """
    # Get paths to workflow files
    base_path = Path(__file__).parent.parent.parent.parent.parent
    app_workflow = base_path / ".github" / "workflows" / "app.yml"
    infra_workflow = base_path / ".github" / "workflows" / "infra.yml"

    variable_name = "TF_VAR_frontend_bucket_name"
    errors = []

    # Check app.yml
    if not app_workflow.exists():
        errors.append(f"Workflow file not found: {app_workflow}")
    else:
        found, locations = check_file_for_variable(app_workflow, variable_name)
        if found:
            line_refs = ", ".join(f"line {loc}" for loc in locations)
            errors.append(f"app.yml contains {variable_name} at {line_refs}")

    # Check infra.yml
    if not infra_workflow.exists():
        errors.append(f"Workflow file not found: {infra_workflow}")
    else:
        found, locations = check_file_for_variable(infra_workflow, variable_name)
        if found:
            line_refs = ", ".join(f"line {loc}" for loc in locations)
            errors.append(f"infra.yml contains {variable_name} at {line_refs}")

    if errors:
        return False, "; ".join(errors)

    return (
        True,
        "Property 9 validated: TF_VAR_frontend_bucket_name removed from workflow files",
    )


def main():
    """Run workflow configuration validation test."""
    print("=" * 80)
    print("CI/CD Workflow Configuration Validation Test")
    print("=" * 80)
    print()

    # Run property validation
    property_name = "Property 9: CI/CD Workflows Environment Variables Removed"
    passed, message = validate_property_9_workflow_env_vars_removed()

    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status}: {property_name}")
    print(f"  {message}")
    print()

    print("=" * 80)
    if passed:
        print("All properties validated successfully!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("Property validation failed")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
