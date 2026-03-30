#!/usr/bin/env python3
"""
Configuration validation test for CloudFront changes.

This test validates Properties 4-8 from the design document:
- Property 4: CloudFront S3 Origin Removed
- Property 5: CloudFront ALB Origin Preserved
- Property 6: CloudFront Default Behavior Routes to ALB
- Property 7: API Cache Behavior Configuration
- Property 8: Default Cache Behavior Configuration

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3
"""

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


class TerraformHCLParser:
    """Simple HCL parser for extracting CloudFront configuration."""

    def __init__(self, content: str):
        self.content = content

    def extract_cloudfront_distribution(self) -> Optional[Dict[str, Any]]:
        """Extract CloudFront distribution resource configuration."""
        # Find the aws_cloudfront_distribution.main resource block
        pattern = r'resource\s+"aws_cloudfront_distribution"\s+"main"\s*\{(.*?)\n\}'
        match = re.search(pattern, self.content, re.DOTALL)

        if not match:
            return None

        resource_content = match.group(1)

        return {
            "origins": self._extract_origins(resource_content),
            "default_cache_behavior": self._extract_default_cache_behavior(
                resource_content
            ),
            "ordered_cache_behaviors": self._extract_ordered_cache_behaviors(
                resource_content
            ),
            "has_default_root_object": self._has_attribute(
                resource_content, "default_root_object"
            ),
            "has_custom_error_response": "custom_error_response" in resource_content,
        }

    def _extract_origins(self, content: str) -> List[Dict[str, Any]]:
        """Extract all origin blocks."""
        origins = []

        # Find all origin blocks
        origin_pattern = r"origin\s*\{(.*?)\n  \}"
        for match in re.finditer(origin_pattern, content, re.DOTALL):
            origin_content = match.group(1)

            origin = {
                "origin_id": self._extract_string_value(origin_content, "origin_id"),
                "domain_name": self._extract_string_value(
                    origin_content, "domain_name"
                ),
                "has_origin_access_control_id": "origin_access_control_id"
                in origin_content,
            }
            origins.append(origin)

        return origins

    def _extract_default_cache_behavior(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract default_cache_behavior block."""
        pattern = r"default_cache_behavior\s*\{(.*?)\n  \}"
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            return None

        behavior_content = match.group(1)

        return {
            "target_origin_id": self._extract_string_value(
                behavior_content, "target_origin_id"
            ),
            "allowed_methods": self._extract_list_value(
                behavior_content, "allowed_methods"
            ),
            "viewer_protocol_policy": self._extract_string_value(
                behavior_content, "viewer_protocol_policy"
            ),
        }

    def _extract_ordered_cache_behaviors(self, content: str) -> List[Dict[str, Any]]:
        """Extract all ordered_cache_behavior blocks."""
        behaviors = []

        # Find all ordered_cache_behavior blocks
        pattern = r"ordered_cache_behavior\s*\{(.*?)\n  \}"
        for match in re.finditer(pattern, content, re.DOTALL):
            behavior_content = match.group(1)

            # Extract forwarded_values
            forwarded_values = self._extract_forwarded_values(behavior_content)

            behavior = {
                "path_pattern": self._extract_string_value(
                    behavior_content, "path_pattern"
                ),
                "target_origin_id": self._extract_string_value(
                    behavior_content, "target_origin_id"
                ),
                "allowed_methods": self._extract_list_value(
                    behavior_content, "allowed_methods"
                ),
                "min_ttl": self._extract_number_value(behavior_content, "min_ttl"),
                "default_ttl": self._extract_number_value(
                    behavior_content, "default_ttl"
                ),
                "max_ttl": self._extract_number_value(behavior_content, "max_ttl"),
                "forwarded_values": forwarded_values,
            }
            behaviors.append(behavior)

        return behaviors

    def _extract_forwarded_values(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract forwarded_values block."""
        pattern = r"forwarded_values\s*\{(.*?)\n    \}"
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            return None

        fv_content = match.group(1)

        # Extract cookies block
        cookies_forward = None
        cookies_pattern = r"cookies\s*\{(.*?)\n      \}"
        cookies_match = re.search(cookies_pattern, fv_content, re.DOTALL)
        if cookies_match:
            cookies_content = cookies_match.group(1)
            cookies_forward = self._extract_string_value(cookies_content, "forward")

        return {
            "query_string": self._extract_boolean_value(fv_content, "query_string"),
            "headers": self._extract_list_value(fv_content, "headers"),
            "cookies_forward": cookies_forward,
        }

    def _extract_string_value(self, content: str, key: str) -> Optional[str]:
        """Extract a string value from HCL content."""
        pattern = rf'{key}\s*=\s*"([^"]*)"'
        match = re.search(pattern, content)
        return match.group(1) if match else None

    def _extract_list_value(self, content: str, key: str) -> Optional[List[str]]:
        """Extract a list value from HCL content."""
        pattern = rf"{key}\s*=\s*\[(.*?)\]"
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            return None

        list_content = match.group(1)
        # Extract quoted strings
        items = re.findall(r'"([^"]*)"', list_content)
        return items if items else None

    def _extract_number_value(self, content: str, key: str) -> Optional[int]:
        """Extract a number value from HCL content."""
        pattern = rf"{key}\s*=\s*(\d+)"
        match = re.search(pattern, content)
        return int(match.group(1)) if match else None

    def _extract_boolean_value(self, content: str, key: str) -> Optional[bool]:
        """Extract a boolean value from HCL content."""
        pattern = rf"{key}\s*=\s*(true|false)"
        match = re.search(pattern, content)
        if not match:
            return None
        return match.group(1) == "true"

    def _has_attribute(self, content: str, key: str) -> bool:
        """Check if an attribute exists in the content."""
        pattern = rf"{key}\s*="
        return bool(re.search(pattern, content))


def validate_property_4_s3_origin_removed(config: Dict[str, Any]) -> tuple[bool, str]:
    """
    Property 4: CloudFront S3 Origin Removed

    Validates: Requirements 3.1, 3.2, 3.3, 3.7

    The CloudFront distribution configuration should not contain:
    - An origin block with origin_id = "S3-Frontend"
    - An origin_access_control_id attribute in any origin block
    - A default_root_object attribute
    - A custom_error_response block for 404 errors
    """
    errors = []

    # Check for S3-Frontend origin
    for origin in config["origins"]:
        if origin["origin_id"] == "S3-Frontend":
            errors.append(
                "Found origin with origin_id 'S3-Frontend' (should be removed)"
            )

        if origin["has_origin_access_control_id"]:
            errors.append(
                f"Origin '{origin['origin_id']}' has origin_access_control_id (should be removed)"
            )

    # Check for default_root_object
    if config["has_default_root_object"]:
        errors.append("Found default_root_object attribute (should be removed)")

    # Check for custom_error_response
    if config["has_custom_error_response"]:
        errors.append("Found custom_error_response block (should be removed)")

    if errors:
        return False, "; ".join(errors)

    return True, "Property 4 validated: S3 origin and related attributes removed"


def validate_property_5_alb_origin_preserved(
    config: Dict[str, Any]
) -> tuple[bool, str]:
    """
    Property 5: CloudFront ALB Origin Preserved

    Validates: Requirements 3.4, 3.5

    The CloudFront distribution configuration should contain:
    - An origin block with origin_id = "ALB-Backend" and domain_name = "api.${var.domain_name}"
    - An ordered_cache_behavior block with path_pattern = "/api/*"
    """
    errors = []

    # Check for ALB-Backend origin
    alb_origin = None
    for origin in config["origins"]:
        if origin["origin_id"] == "ALB-Backend":
            alb_origin = origin
            break

    if not alb_origin:
        errors.append("Missing origin with origin_id 'ALB-Backend'")
    else:
        # Check domain_name contains api.${var.domain_name} pattern
        if not alb_origin["domain_name"] or "api." not in alb_origin["domain_name"]:
            errors.append(
                f"ALB origin domain_name '{alb_origin['domain_name']}' does not match expected pattern 'api.${{var.domain_name}}'"
            )

    # Check for /api/* ordered_cache_behavior
    api_behavior = None
    for behavior in config["ordered_cache_behaviors"]:
        if behavior["path_pattern"] == "/api/*":
            api_behavior = behavior
            break

    if not api_behavior:
        errors.append("Missing ordered_cache_behavior with path_pattern '/api/*'")

    if errors:
        return False, "; ".join(errors)

    return True, "Property 5 validated: ALB origin and API cache behavior preserved"


def validate_property_6_default_behavior_routes_to_alb(
    config: Dict[str, Any]
) -> tuple[bool, str]:
    """
    Property 6: CloudFront Default Behavior Routes to ALB

    Validates: Requirements 3.6, 7.1

    The CloudFront distribution's default_cache_behavior block should have
    target_origin_id = "ALB-Backend".
    """
    default_behavior = config["default_cache_behavior"]

    if not default_behavior:
        return False, "Missing default_cache_behavior block"

    if default_behavior["target_origin_id"] != "ALB-Backend":
        return (
            False,
            f"default_cache_behavior target_origin_id is '{default_behavior['target_origin_id']}', expected 'ALB-Backend'",
        )

    return True, "Property 6 validated: Default behavior routes to ALB-Backend"


def validate_property_7_api_cache_behavior(config: Dict[str, Any]) -> tuple[bool, str]:
    """
    Property 7: API Cache Behavior Configuration

    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6

    The CloudFront distribution's ordered_cache_behavior block for path_pattern = "/api/*"
    should have:
    - target_origin_id = "ALB-Backend"
    - allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    - forwarded_values.query_string = true
    - forwarded_values.headers = ["*"]
    - forwarded_values.cookies.forward = "all"
    - min_ttl = 0, default_ttl = 0, max_ttl = 0
    """
    # Find /api/* behavior
    api_behavior = None
    for behavior in config["ordered_cache_behaviors"]:
        if behavior["path_pattern"] == "/api/*":
            api_behavior = behavior
            break

    if not api_behavior:
        return False, "Missing ordered_cache_behavior with path_pattern '/api/*'"

    errors = []

    # Check target_origin_id
    if api_behavior["target_origin_id"] != "ALB-Backend":
        errors.append(
            f"target_origin_id is '{api_behavior['target_origin_id']}', expected 'ALB-Backend'"
        )

    # Check allowed_methods
    expected_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    if set(api_behavior["allowed_methods"] or []) != set(expected_methods):
        errors.append(
            f"allowed_methods is {api_behavior['allowed_methods']}, expected {expected_methods}"
        )

    # Check TTL values
    if api_behavior["min_ttl"] != 0:
        errors.append(f"min_ttl is {api_behavior['min_ttl']}, expected 0")
    if api_behavior["default_ttl"] != 0:
        errors.append(f"default_ttl is {api_behavior['default_ttl']}, expected 0")
    if api_behavior["max_ttl"] != 0:
        errors.append(f"max_ttl is {api_behavior['max_ttl']}, expected 0")

    # Check forwarded_values
    fv = api_behavior["forwarded_values"]
    if not fv:
        errors.append("Missing forwarded_values block")
    else:
        if fv["query_string"] is not True:
            errors.append(
                f"forwarded_values.query_string is {fv['query_string']}, expected true"
            )

        if fv["headers"] != ["*"]:
            errors.append(
                f"forwarded_values.headers is {fv['headers']}, expected ['*']"
            )

        if fv["cookies_forward"] != "all":
            errors.append(
                f"forwarded_values.cookies.forward is '{fv['cookies_forward']}', expected 'all'"
            )

    if errors:
        return False, "; ".join(errors)

    return True, "Property 7 validated: API cache behavior configuration correct"


def validate_property_8_default_cache_behavior(
    config: Dict[str, Any]
) -> tuple[bool, str]:
    """
    Property 8: Default Cache Behavior Configuration

    Validates: Requirements 7.2, 7.3

    The CloudFront distribution's default_cache_behavior block should have:
    - allowed_methods including at least ["GET", "HEAD", "OPTIONS"]
    - viewer_protocol_policy = "redirect-to-https"
    """
    default_behavior = config["default_cache_behavior"]

    if not default_behavior:
        return False, "Missing default_cache_behavior block"

    errors = []

    # Check allowed_methods
    required_methods = {"GET", "HEAD", "OPTIONS"}
    actual_methods = set(default_behavior["allowed_methods"] or [])
    if not required_methods.issubset(actual_methods):
        missing = required_methods - actual_methods
        errors.append(f"allowed_methods missing required methods: {missing}")

    # Check viewer_protocol_policy
    if default_behavior["viewer_protocol_policy"] != "redirect-to-https":
        errors.append(
            f"viewer_protocol_policy is '{default_behavior['viewer_protocol_policy']}', expected 'redirect-to-https'"
        )

    if errors:
        return False, "; ".join(errors)

    return True, "Property 8 validated: Default cache behavior configuration correct"


def main():
    """Run all CloudFront configuration validation tests."""
    # Path to the Terraform file
    terraform_file = (
        Path(__file__).parent.parent.parent.parent.parent
        / ".github"
        / "terraform"
        / "core"
        / "4_edge.tf"
    )

    if not terraform_file.exists():
        print(f"ERROR: Terraform file not found: {terraform_file}")
        sys.exit(1)

    # Read and parse the file
    content = terraform_file.read_text()
    parser = TerraformHCLParser(content)
    config = parser.extract_cloudfront_distribution()

    if not config:
        print(
            "ERROR: Could not find aws_cloudfront_distribution.main resource in 4_edge.tf"
        )
        sys.exit(1)

    # Run all property validations
    properties = [
        (
            "Property 4: CloudFront S3 Origin Removed",
            validate_property_4_s3_origin_removed,
        ),
        (
            "Property 5: CloudFront ALB Origin Preserved",
            validate_property_5_alb_origin_preserved,
        ),
        (
            "Property 6: CloudFront Default Behavior Routes to ALB",
            validate_property_6_default_behavior_routes_to_alb,
        ),
        (
            "Property 7: API Cache Behavior Configuration",
            validate_property_7_api_cache_behavior,
        ),
        (
            "Property 8: Default Cache Behavior Configuration",
            validate_property_8_default_cache_behavior,
        ),
    ]

    all_passed = True
    results = []

    print("=" * 80)
    print("CloudFront Configuration Validation Test")
    print("=" * 80)
    print()

    for property_name, validator in properties:
        passed, message = validator(config)
        status = "✓ PASS" if passed else "✗ FAIL"
        results.append((property_name, passed, message))

        print(f"{status}: {property_name}")
        print(f"  {message}")
        print()

        if not passed:
            all_passed = False

    print("=" * 80)
    if all_passed:
        print("All properties validated successfully!")
        print("=" * 80)
        sys.exit(0)
    else:
        failed_count = sum(1 for _, passed, _ in results if not passed)
        print(f"{failed_count} property validation(s) failed")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
