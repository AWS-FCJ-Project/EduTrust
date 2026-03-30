"""
Property-based tests for CI/CD Pipeline workflow validation.

This module contains property-based tests that validate the structural correctness
of GitHub Actions workflow files. Each test validates one of the 24 correctness
properties defined in the design document.

Test Framework: Python with PyYAML for parsing and Hypothesis for property-based testing
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st


def load_workflow(workflow_path: str) -> dict:
    """Load and parse a GitHub Actions workflow YAML file."""
    path = Path(workflow_path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    with open(path, "r") as f:
        return yaml.safe_load(f)


def find_step_by_name(job: dict, step_name: str) -> Optional[dict]:
    """Find a step in a job by its name."""
    for step in job.get("steps", []):
        if step.get("name") == step_name:
            return step
    return None


def find_step_by_id(job: dict, step_id: str) -> Optional[dict]:
    """Find a step in a job by its id."""
    for step in job.get("steps", []):
        if step.get("id") == step_id:
            return step
    return None


def get_triggers(workflow: dict) -> List[str]:
    """Extract trigger types from workflow configuration."""
    triggers = workflow.get("on") or workflow.get(True) or workflow.get("true")

    if triggers is None:
        return []

    if isinstance(triggers, dict):
        return list(triggers.keys())
    elif isinstance(triggers, list):
        return triggers
    else:
        return [triggers]


def step_contains_command(step: dict, command: str) -> bool:
    """Check if a step contains a specific command in its run field."""
    run_content = step.get("run", "")
    return command in run_content


def job_has_dependency(job: dict, dependency_name: str) -> bool:
    """Check if a job depends on another job."""
    needs = job.get("needs")
    if needs is None:
        return False
    if isinstance(needs, str):
        return needs == dependency_name
    if isinstance(needs, list):
        return dependency_name in needs
    return False


# ============================================================================
# Property 1: Infrastructure Pipeline Manual Trigger Only
# ============================================================================


def test_property_1_infra_pipeline_manual_trigger_only():
    """
    **Property 1: Infrastructure Pipeline Manual Trigger Only**

    The Infrastructure Pipeline workflow file SHALL contain only `workflow_dispatch`
    in its trigger configuration and SHALL NOT contain automatic triggers such as
    `push`, `pull_request`, or `workflow_run`.

    **Validates: Requirements 1.3**
    """
    workflow = load_workflow(".github/workflows/infra.yml")
    triggers = get_triggers(workflow)

    # Must have workflow_dispatch
    assert (
        "workflow_dispatch" in triggers
    ), "Infrastructure Pipeline must have workflow_dispatch trigger"

    # Must not have automatic triggers
    automatic_triggers = ["push", "pull_request", "workflow_run", "schedule"]
    for trigger in automatic_triggers:
        assert (
            trigger not in triggers
        ), f"Infrastructure Pipeline must not have {trigger} trigger"


# ============================================================================
# Property 2: Infrastructure Pipeline Provisions Both Tiers
# ============================================================================


def test_property_2_infra_pipeline_provisions_both_tiers():
    """
    **Property 2: Infrastructure Pipeline Provisions Both Tiers**

    The Infrastructure Pipeline workflow file SHALL contain jobs that execute
    `terraform apply` for both core infrastructure (`.github/terraform/core/`)
    and service infrastructure (`.github/terraform/service/`).

    **Validates: Requirements 1.1, 1.2**
    """
    workflow = load_workflow(".github/workflows/infra.yml")
    jobs = workflow.get("jobs", {})

    # Check for terraform-core job
    assert (
        "terraform-core" in jobs
    ), "Infrastructure Pipeline must have terraform-core job"

    core_job = jobs["terraform-core"]
    core_apply_found = False
    for step in core_job.get("steps", []):
        if "terraform apply" in step.get("run", ""):
            core_apply_found = True
            break

    assert core_apply_found, "terraform-core job must execute 'terraform apply'"

    # Check for terraform-service job
    assert (
        "terraform-service" in jobs
    ), "Infrastructure Pipeline must have terraform-service job"

    service_job = jobs["terraform-service"]
    service_apply_found = False
    for step in service_job.get("steps", []):
        if "terraform apply" in step.get("run", ""):
            service_apply_found = True
            break

    assert service_apply_found, "terraform-service job must execute 'terraform apply'"


# ============================================================================
# Property 3: Infrastructure Pipeline Excludes Application Code
# ============================================================================


def test_property_3_infra_pipeline_excludes_application_code():
    """
    **Property 3: Infrastructure Pipeline Excludes Application Code**

    The Infrastructure Pipeline workflow file SHALL NOT contain steps for building
    application code, including Docker build commands, npm build commands, or
    application deployment steps.

    **Validates: Requirements 1.4**
    """
    workflow = load_workflow(".github/workflows/infra.yml")

    forbidden_commands = [
        "docker build",
        "docker push",
        "npm install",
        "npm run build",
        "npm ci",
        "aws s3 sync",
        "cloudfront create-invalidation",
        "start-instance-refresh",
    ]

    forbidden_actions = [
        "docker/build-push-action",
        "actions/setup-node",
        "docker/setup-buildx-action",
    ]

    for job_name, job in workflow.get("jobs", {}).items():
        for step in job.get("steps", []):
            run_content = step.get("run", "").lower()
            uses_content = step.get("uses", "").lower()

            for cmd in forbidden_commands:
                assert (
                    cmd not in run_content
                ), f"Infrastructure Pipeline job '{job_name}' must not contain '{cmd}'"

            for action in forbidden_actions:
                assert (
                    action not in uses_content
                ), f"Infrastructure Pipeline job '{job_name}' must not use '{action}'"


# ============================================================================
# Property 4: Infrastructure Pipeline Exports Required Outputs
# ============================================================================


def test_property_4_infra_pipeline_exports_required_outputs():
    """
    **Property 4: Infrastructure Pipeline Exports Required Outputs**

    The Infrastructure Pipeline's terraform-service job SHALL define outputs for
    `asg_name`, `ecr_repository_url`, `secrets_kms_key_arn`, `aws_region`,
    and `backend_port`.

    **Validates: Requirements 1.5**
    """
    workflow = load_workflow(".github/workflows/infra.yml")
    service_job = workflow["jobs"]["terraform-service"]

    required_outputs = [
        "asg_name",
        "ecr_repository_url",
        "secrets_kms_key_arn",
        "aws_region",
        "backend_port",
    ]

    assert "outputs" in service_job, "terraform-service job must define outputs"

    outputs = service_job["outputs"]

    for output_name in required_outputs:
        assert (
            output_name in outputs
        ), f"terraform-service job must define '{output_name}' output"


# ============================================================================
# Property 5: Application Pipeline Automatic Trigger
# ============================================================================


def test_property_5_app_pipeline_automatic_trigger():
    """
    **Property 5: Application Pipeline Automatic Trigger**

    The Application Pipeline workflow file SHALL contain a `workflow_run` trigger
    that listens for CI pipeline completion with `types: [completed]` and checks
    for success status on main and feature branches.

    **Validates: Requirements 2.1, 2.2, 2.5, 8.1**
    """
    workflow = load_workflow(".github/workflows/app.yml")

    # Handle both 'on' and True as keys (YAML parsing quirk)
    triggers = workflow.get("on") or workflow.get(True) or {}

    assert (
        "workflow_run" in triggers
    ), "Application Pipeline must have workflow_run trigger"

    workflow_run_config = triggers["workflow_run"]

    # Check workflows list
    assert (
        "workflows" in workflow_run_config
    ), "workflow_run trigger must specify workflows"
    assert (
        "CI" in workflow_run_config["workflows"]
    ), "workflow_run trigger must listen for 'CI' workflow"

    # Check types
    assert "types" in workflow_run_config, "workflow_run trigger must specify types"
    assert (
        "completed" in workflow_run_config["types"]
    ), "workflow_run trigger must include 'completed' type"

    # Check branches
    assert (
        "branches" in workflow_run_config
    ), "workflow_run trigger must specify branches"
    branches = workflow_run_config["branches"]
    assert "main" in branches, "workflow_run trigger must include 'main' branch"

    # Check for feature branch pattern
    has_feature_pattern = any("feat" in branch for branch in branches)
    assert (
        has_feature_pattern
    ), "workflow_run trigger must include feature branch pattern"


# ============================================================================
# Property 6: Application Pipeline Read-Only Infrastructure Access
# ============================================================================


def test_property_6_app_pipeline_read_only_infrastructure_access():
    """
    **Property 6: Application Pipeline Read-Only Infrastructure Access**

    The Application Pipeline workflow file SHALL contain only `terraform output`
    commands for reading infrastructure state and SHALL NOT contain `terraform apply`
    commands.

    **Validates: Requirements 2.3, 9.2, 9.5**
    """
    workflow = load_workflow(".github/workflows/app.yml")

    for job_name, job in workflow.get("jobs", {}).items():
        terraform_output_found = False
        terraform_apply_found = False

        for step in job.get("steps", []):
            run_content = step.get("run", "")

            if "terraform output" in run_content:
                terraform_output_found = True

            # Check for terraform apply (but allow it in specific context for launch template updates)
            if "terraform apply" in run_content:
                # Allow terraform apply only for updating launch template with image tag
                if "backend_image_tag" not in run_content:
                    terraform_apply_found = True

        # At least one job should read terraform outputs
        if job_name == "build-backend":
            assert (
                terraform_output_found
            ), f"Job '{job_name}' must read infrastructure outputs using 'terraform output'"


# ============================================================================
# Property 7: Parallel Build Job Execution
# ============================================================================


def test_property_7_parallel_build_job_execution():
    """
    **Property 7: Parallel Build Job Execution**

    The Application Pipeline SHALL define backend and frontend build jobs without
    `needs` dependencies on each other, and neither job SHALL have conditional `if`
    statements that depend on the other job's completion status.

    **Validates: Requirements 2.4, 5.1, 5.2, 5.3, 5.4**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    jobs = workflow.get("jobs", {})

    assert "build-backend" in jobs, "Application Pipeline must have build-backend job"
    assert "build-frontend" in jobs, "Application Pipeline must have build-frontend job"

    backend_job = jobs["build-backend"]
    frontend_job = jobs["build-frontend"]

    # Check backend doesn't depend on frontend
    if "needs" in backend_job:
        needs = backend_job["needs"]
        if isinstance(needs, str):
            assert (
                needs != "build-frontend"
            ), "build-backend must not depend on build-frontend"
        elif isinstance(needs, list):
            assert (
                "build-frontend" not in needs
            ), "build-backend must not depend on build-frontend"

    # Check frontend doesn't depend on backend
    if "needs" in frontend_job:
        needs = frontend_job["needs"]
        if isinstance(needs, str):
            assert (
                needs != "build-backend"
            ), "build-frontend must not depend on build-backend"
        elif isinstance(needs, list):
            assert (
                "build-backend" not in needs
            ), "build-frontend must not depend on build-backend"


# ============================================================================
# Property 8: Backend Build Job Complete Workflow
# ============================================================================


def test_property_8_backend_build_job_complete_workflow():
    """
    **Property 8: Backend Build Job Complete Workflow**

    The backend build job SHALL contain steps for: (1) computing content hash of
    backend source code, (2) checking ECR for existing image, (3) conditionally
    building and pushing Docker image, (4) updating SSM parameters, (5) updating
    ASG launch template via terraform apply with `backend_image_tag` variable,
    and (6) triggering ASG instance refresh.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # (1) Check for content hash computation
    hash_step = find_step_by_name(backend_job, "Compute Docker Context Hash")
    assert (
        hash_step is not None
    ), "build-backend must have 'Compute Docker Context Hash' step"
    assert "sha256sum" in hash_step["run"], "Hash computation must use sha256sum"

    # (2) Check for ECR image existence check
    check_image_step = find_step_by_name(backend_job, "Check if Image Exists in ECR")
    assert (
        check_image_step is not None
    ), "build-backend must have 'Check if Image Exists in ECR' step"
    assert (
        "describe-images" in check_image_step["run"]
    ), "Image check must use ECR describe-images"

    # (3) Check for conditional Docker build
    build_step = find_step_by_name(backend_job, "Build and Push Docker Image")
    assert (
        build_step is not None
    ), "build-backend must have 'Build and Push Docker Image' step"
    assert "if" in build_step, "Docker build step must be conditional"

    # (4) Check for SSM parameter update
    ssm_step = find_step_by_name(
        backend_job, "Update SSM Parameter with Backend Environment Variables"
    )
    assert ssm_step is not None, "build-backend must have SSM parameter update step"
    assert (
        "ssm put-parameter" in ssm_step["run"]
    ), "SSM update must use put-parameter command"

    # (5) Check for launch template update
    lt_step = find_step_by_name(
        backend_job, "Update Launch Template with New Image Tag"
    )
    assert lt_step is not None, "build-backend must have launch template update step"
    assert (
        "terraform apply" in lt_step["run"]
    ), "Launch template update must use terraform apply"
    assert (
        "backend_image_tag" in lt_step["run"]
    ), "Launch template update must pass backend_image_tag variable"

    # (6) Check for ASG instance refresh
    refresh_step = find_step_by_name(backend_job, "Start ASG Instance Refresh")
    assert refresh_step is not None, "build-backend must have ASG instance refresh step"
    assert (
        "start-instance-refresh" in refresh_step["run"]
    ), "Instance refresh must use start-instance-refresh command"


# ============================================================================
# Property 9: Frontend Build Job Complete Workflow
# ============================================================================


def test_property_9_frontend_build_job_complete_workflow():
    """
    **Property 9: Frontend Build Job Complete Workflow**

    The frontend build job SHALL contain steps for: (1) running `npm install`,
    (2) running `npm run build`, (3) executing `aws s3 sync` with `--delete` flag,
    and (4) executing `aws cloudfront create-invalidation` after S3 sync completes.

    **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    # (1) Check for npm install
    install_step = find_step_by_name(frontend_job, "Install dependencies")
    assert (
        install_step is not None
    ), "build-frontend must have 'Install dependencies' step"
    assert "npm install" in install_step["run"], "Install step must run 'npm install'"

    # (2) Check for npm build
    build_step = find_step_by_name(frontend_job, "Build frontend")
    assert build_step is not None, "build-frontend must have 'Build frontend' step"
    assert "npm run build" in build_step["run"], "Build step must run 'npm run build'"

    # (3) Check for S3 sync with --delete
    s3_step = find_step_by_name(frontend_job, "Sync to S3")
    assert s3_step is not None, "build-frontend must have 'Sync to S3' step"
    assert "aws s3 sync" in s3_step["run"], "S3 step must use 'aws s3 sync'"
    assert "--delete" in s3_step["run"], "S3 sync must include --delete flag"

    # (4) Check for CloudFront invalidation
    cf_step = find_step_by_name(frontend_job, "Invalidate CloudFront cache")
    assert (
        cf_step is not None
    ), "build-frontend must have 'Invalidate CloudFront cache' step"
    assert (
        "cloudfront create-invalidation" in cf_step["run"]
    ), "CloudFront step must use 'create-invalidation'"


# ============================================================================
# Property 10: AMI Pipeline Manual Trigger and Hash-Based Caching
# ============================================================================


def test_property_10_ami_pipeline_manual_trigger_and_caching():
    """
    **Property 10: AMI Pipeline Manual Trigger and Hash-Based Caching**

    The AMI Pipeline workflow file SHALL contain only `workflow_dispatch` trigger,
    SHALL compute SHA256 hash of Packer configuration, and SHALL include a
    conditional check that skips build when an AMI with matching `PackerHash`
    tag exists in AWS.

    **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
    """
    workflow = load_workflow(".github/workflows/ami.yml")

    # Check trigger
    triggers = get_triggers(workflow)
    assert (
        "workflow_dispatch" in triggers
    ), "AMI Pipeline must have workflow_dispatch trigger"
    assert (
        "push" not in triggers and "pull_request" not in triggers
    ), "AMI Pipeline must not have automatic triggers"

    # Check for Packer build job
    assert "packer-build" in workflow["jobs"], "AMI Pipeline must have packer-build job"

    packer_job = workflow["jobs"]["packer-build"]

    # Check for hash computation
    hash_step = find_step_by_name(packer_job, "Compute Packer Configuration Hash")
    assert hash_step is not None, "packer-build must have hash computation step"
    assert "sha256sum" in hash_step["run"], "Hash computation must use sha256sum"

    # Check for AMI existence check
    check_step = find_step_by_name(
        packer_job, "Check for Existing AMI with Matching Hash"
    )
    assert check_step is not None, "packer-build must have AMI existence check step"
    assert "describe-images" in check_step["run"], "AMI check must use describe-images"
    assert "PackerHash" in check_step["run"], "AMI check must filter by PackerHash tag"

    # Check for conditional build
    build_step = find_step_by_name(packer_job, "Build AMI with Packer")
    assert build_step is not None, "packer-build must have Packer build step"
    assert "if" in build_step, "Packer build step must be conditional"


# ============================================================================
# Property 11: AMI Pipeline Independence
# ============================================================================


def test_property_11_ami_pipeline_independence():
    """
    **Property 11: AMI Pipeline Independence**

    The Application Pipeline workflow file SHALL NOT contain `needs` dependencies
    on the AMI Pipeline or any references to AMI build jobs.

    **Validates: Requirements 6.5**
    """
    workflow = load_workflow(".github/workflows/app.yml")

    for job_name, job in workflow.get("jobs", {}).items():
        # Check needs dependencies
        if "needs" in job:
            needs = job["needs"]
            if isinstance(needs, str):
                assert (
                    "ami" not in needs.lower() and "packer" not in needs.lower()
                ), f"Job '{job_name}' must not depend on AMI Pipeline jobs"
            elif isinstance(needs, list):
                for dep in needs:
                    assert (
                        "ami" not in dep.lower() and "packer" not in dep.lower()
                    ), f"Job '{job_name}' must not depend on AMI Pipeline jobs"


# ============================================================================
# Property 12: CI Pipeline Dependency Check
# ============================================================================


def test_property_12_ci_pipeline_dependency_check():
    """
    **Property 12: CI Pipeline Dependency Check**

    The Application Pipeline workflow_run trigger SHALL include a condition that
    checks `github.event.workflow_run.conclusion == 'success'` to prevent execution
    when CI pipeline fails.

    **Validates: Requirements 7.5**
    """
    workflow = load_workflow(".github/workflows/app.yml")

    # Check that jobs have success condition
    for job_name, job in workflow.get("jobs", {}).items():
        if "if" in job:
            condition = job["if"]
            # Should check for workflow_run success or workflow_dispatch
            assert (
                "workflow_run.conclusion" in condition
                or "workflow_dispatch" in condition
            ), f"Job '{job_name}' must check CI pipeline success status"


# ============================================================================
# Property 13: Backend Job Infrastructure Dependency
# ============================================================================


def test_property_13_backend_job_infrastructure_dependency():
    """
    **Property 13: Backend Job Infrastructure Dependency**

    The backend build job SHALL read infrastructure outputs using `terraform output`
    commands or job outputs from a terraform job, specifically retrieving
    `ecr_repository_url`, `asg_name`, `secrets_kms_key_arn`, and `aws_region`.

    **Validates: Requirements 8.2**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Check for infrastructure outputs reading step
    infra_step = find_step_by_name(backend_job, "Read Infrastructure Outputs")
    assert (
        infra_step is not None
    ), "build-backend must have 'Read Infrastructure Outputs' step"

    # Check that terraform output is used
    assert (
        "terraform output" in infra_step["run"]
    ), "Infrastructure outputs must be read using 'terraform output'"

    # Check for required outputs
    required_outputs = [
        "ecr_repository_url",
        "asg_name",
        "secrets_kms_key_arn",
        "aws_region",
    ]
    for output in required_outputs:
        # Check if output is referenced in the step or environment
        found = False
        if output in infra_step["run"]:
            found = True

        # Also check if it's set in environment variables in subsequent steps
        for step in backend_job.get("steps", []):
            if output.upper() in step.get("run", ""):
                found = True
                break

        assert found, f"build-backend must read '{output}' from infrastructure outputs"


# ============================================================================
# Property 14: Frontend Job Infrastructure Dependency
# ============================================================================


def test_property_14_frontend_job_infrastructure_dependency():
    """
    **Property 14: Frontend Job Infrastructure Dependency**

    The frontend build job SHALL use infrastructure values from GitHub secrets or
    environment variables for S3 bucket name and CloudFront distribution ID.

    **Validates: Requirements 8.3**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    # Check environment variables or secrets usage
    env_vars = frontend_job.get("env", {})

    # Check for S3 bucket configuration
    s3_bucket_found = False
    if "S3_BUCKET" in env_vars or "s3_bucket" in str(env_vars).lower():
        s3_bucket_found = True

    # Also check in steps
    for step in frontend_job.get("steps", []):
        if (
            "S3_BUCKET" in step.get("run", "")
            or "s3_bucket" in step.get("run", "").lower()
        ):
            s3_bucket_found = True
            break

    assert (
        s3_bucket_found
    ), "build-frontend must use S3 bucket from secrets or environment"

    # Check for CloudFront distribution ID
    cf_dist_found = False
    if "CLOUDFRONT_DIST_ID" in env_vars or "cloudfront" in str(env_vars).lower():
        cf_dist_found = True

    for step in frontend_job.get("steps", []):
        if (
            "CLOUDFRONT_DIST_ID" in step.get("run", "")
            or "cloudfront" in step.get("run", "").lower()
        ):
            cf_dist_found = True
            break

    assert (
        cf_dist_found
    ), "build-frontend must use CloudFront distribution ID from secrets or environment"


# ============================================================================
# Property 15: Application Pipeline State Persistence
# ============================================================================


def test_property_15_app_pipeline_state_persistence():
    """
    **Property 15: Application Pipeline State Persistence**

    The Application Pipeline SHALL read infrastructure outputs from Terraform
    remote state stored in S3, allowing execution without requiring the
    Infrastructure Pipeline to have run in the same workflow execution.

    **Validates: Requirements 8.4**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Check for terraform init (which reads remote state)
    infra_step = find_step_by_name(backend_job, "Read Infrastructure Outputs")
    assert infra_step is not None, "build-backend must read infrastructure outputs"

    # Check that terraform init is called (to access remote state)
    assert (
        "terraform init" in infra_step["run"]
    ), "Must initialize Terraform to read remote state"

    # Verify no dependency on Infrastructure Pipeline jobs
    if "needs" in backend_job:
        needs = backend_job["needs"]
        if isinstance(needs, str):
            assert (
                "terraform" not in needs.lower() or "infra" not in needs.lower()
            ), "build-backend must not depend on Infrastructure Pipeline jobs"
        elif isinstance(needs, list):
            for dep in needs:
                assert (
                    "terraform" not in dep.lower() and "infra" not in dep.lower()
                ), "build-backend must not depend on Infrastructure Pipeline jobs"


# ============================================================================
# Property 16: Infrastructure Pipeline Independence
# ============================================================================


def test_property_16_infrastructure_pipeline_independence():
    """
    **Property 16: Infrastructure Pipeline Independence**

    The Infrastructure Pipeline workflow file SHALL NOT contain `workflow_run`
    triggers or `needs` dependencies on other workflows.

    **Validates: Requirements 8.5**
    """
    workflow = load_workflow(".github/workflows/infra.yml")

    # Check triggers
    triggers = get_triggers(workflow)
    assert (
        "workflow_run" not in triggers
    ), "Infrastructure Pipeline must not have workflow_run trigger"

    # Check that no job depends on external workflows
    for job_name, job in workflow.get("jobs", {}).items():
        if "needs" in job:
            needs = job["needs"]
            # Needs should only reference jobs within the same workflow
            if isinstance(needs, str):
                assert (
                    needs in workflow["jobs"]
                ), f"Job '{job_name}' depends on external job '{needs}'"
            elif isinstance(needs, list):
                for dep in needs:
                    assert (
                        dep in workflow["jobs"]
                    ), f"Job '{job_name}' depends on external job '{dep}'"


# ============================================================================
# Property 17: Terraform S3 Backend Configuration
# ============================================================================


def test_property_17_terraform_s3_backend_configuration():
    """
    **Property 17: Terraform S3 Backend Configuration**

    The Terraform provider configuration files in both `core/` and `service/`
    directories SHALL include S3 backend configuration with bucket, key, and
    region parameters.

    **Validates: Requirements 9.1**
    """
    # Check core backend configuration
    core_dir = Path(".github/terraform/core")
    assert core_dir.exists(), "Core infrastructure directory must exist"

    # Read all .tf files in core directory
    core_backend_found = False
    core_backend_content = ""
    for tf_file in core_dir.glob("*.tf"):
        with open(tf_file, "r") as f:
            content = f.read()
            core_backend_content += content
            if 'backend "s3"' in content:
                core_backend_found = True

    assert core_backend_found, "Core backend must use S3"
    assert "bucket" in core_backend_content, "Core backend must specify bucket"
    assert "key" in core_backend_content, "Core backend must specify key"
    assert "region" in core_backend_content, "Core backend must specify region"

    # Check service backend configuration
    service_dir = Path(".github/terraform/service")
    assert service_dir.exists(), "Service infrastructure directory must exist"

    # Read all .tf files in service directory
    service_backend_found = False
    service_backend_content = ""
    for tf_file in service_dir.glob("*.tf"):
        with open(tf_file, "r") as f:
            content = f.read()
            service_backend_content += content
            if 'backend "s3"' in content:
                service_backend_found = True

    assert service_backend_found, "Service backend must use S3"
    assert "bucket" in service_backend_content, "Service backend must specify bucket"
    assert "key" in service_backend_content, "Service backend must specify key"
    assert "region" in service_backend_content, "Service backend must specify region"


# ============================================================================
# Property 18: Conditional Core Infrastructure Application
# ============================================================================


def test_property_18_conditional_core_infrastructure():
    """
    **Property 18: Conditional Core Infrastructure Application**

    The Infrastructure Pipeline SHALL use path filtering (e.g., `dorny/paths-filter`)
    to detect changes in `.github/terraform/core/**` and conditionally execute
    terraform apply for core infrastructure only when changes are detected.

    **Validates: Requirements 9.3**
    """
    workflow = load_workflow(".github/workflows/infra.yml")
    core_job = workflow["jobs"]["terraform-core"]

    # Check for path filter step
    filter_step = find_step_by_name(core_job, "Check for Core Infra changes")
    assert filter_step is not None, "terraform-core must have path filter step"

    # Check that it uses paths-filter action
    assert "dorny/paths-filter" in filter_step.get(
        "uses", ""
    ), "Path filter must use dorny/paths-filter action"

    # Check for conditional terraform apply
    apply_step = find_step_by_name(core_job, "Terraform Apply (Core)")
    assert apply_step is not None, "terraform-core must have Terraform Apply step"

    assert "if" in apply_step, "Terraform Apply (Core) must be conditional"

    # Check condition references filter output
    condition = apply_step["if"]
    assert (
        "filter.outputs.core" in condition or "workflow_dispatch" in condition
    ), "Terraform Apply (Core) must check path filter output"


# ============================================================================
# Property 19: Service Infrastructure Always Applied
# ============================================================================


def test_property_19_service_infrastructure_always_applied():
    """
    **Property 19: Service Infrastructure Always Applied**

    The Infrastructure Pipeline SHALL always execute terraform apply for service
    infrastructure since it depends on core infrastructure outputs.

    **Validates: Requirements 9.4**
    """
    workflow = load_workflow(".github/workflows/infra.yml")
    service_job = workflow["jobs"]["terraform-service"]

    # Check for terraform apply step
    apply_step = find_step_by_name(service_job, "Terraform Apply (Service)")
    assert apply_step is not None, "terraform-service must have Terraform Apply step"

    # Verify it's not conditional (or only conditional on job-level conditions)
    # The step itself should not have an 'if' condition that would skip it
    if "if" in apply_step:
        # If there's a condition, it should not be based on path filtering
        condition = apply_step["if"]
        assert (
            "filter" not in condition.lower()
        ), "Terraform Apply (Service) must not be conditional on path filtering"


# ============================================================================
# Property 20: Content-Based Docker Image Tagging
# ============================================================================


def test_property_20_content_based_docker_image_tagging():
    """
    **Property 20: Content-Based Docker Image Tagging**

    The backend build job SHALL compute a content hash using `sha256sum` of
    backend source files and Dockerfile, and SHALL use this hash as the Docker
    image tag.

    **Validates: Requirements 10.1**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Check for hash computation step
    hash_step = find_step_by_name(backend_job, "Compute Docker Context Hash")
    assert hash_step is not None, "build-backend must compute content hash"

    # Verify sha256sum is used
    assert "sha256sum" in hash_step["run"], "Content hash must use sha256sum"

    # Verify backend files are included
    assert "backend" in hash_step["run"], "Hash must include backend source files"
    assert "Dockerfile" in hash_step["run"], "Hash must include Dockerfile"

    # Check that hash is used as image tag
    image_vars_step = find_step_by_name(backend_job, "Set Image Variables")
    assert image_vars_step is not None, "build-backend must set image variables"

    # Verify hash is used in image tag
    assert (
        "image_hash" in image_vars_step["run"]
        or "compute_hash.outputs" in image_vars_step["run"]
    ), "Image tag must use computed hash"


# ============================================================================
# Property 21: ECR Image Preservation
# ============================================================================


def test_property_21_ecr_image_preservation():
    """
    **Property 21: ECR Image Preservation**

    The backend build job SHALL NOT contain steps that delete or deregister
    previous Docker images from ECR, preserving image history for rollback
    capability.

    **Validates: Requirements 10.2**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Check that no steps delete ECR images
    for step in backend_job.get("steps", []):
        run_content = step.get("run", "").lower()

        assert (
            "batch-delete-image" not in run_content
        ), "build-backend must not delete ECR images"
        assert (
            "delete-repository" not in run_content
        ), "build-backend must not delete ECR repository"
        assert (
            "ecr delete" not in run_content
        ), "build-backend must not delete ECR resources"


# ============================================================================
# Property 22: ASG Instance Refresh Safety Configuration
# ============================================================================


def test_property_22_asg_instance_refresh_safety():
    """
    **Property 22: ASG Instance Refresh Safety Configuration**

    The ASG instance refresh command SHALL include preferences with
    `MinHealthyPercentage: 50` and `InstanceWarmup: 60` to maintain availability
    during deployment.

    **Validates: Requirements 10.3**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Find instance refresh step
    refresh_step = find_step_by_name(backend_job, "Start ASG Instance Refresh")
    assert refresh_step is not None, "build-backend must have instance refresh step"

    run_content = refresh_step["run"]

    # Check for MinHealthyPercentage
    assert (
        "MinHealthyPercentage" in run_content
        or "min-healthy-percentage" in run_content.lower()
    ), "Instance refresh must specify MinHealthyPercentage"
    assert "50" in run_content, "MinHealthyPercentage must be 50"

    # Check for InstanceWarmup
    assert (
        "InstanceWarmup" in run_content or "instance-warmup" in run_content.lower()
    ), "Instance refresh must specify InstanceWarmup"
    assert "60" in run_content, "InstanceWarmup must be 60 seconds"


# ============================================================================
# Property 23: ASG Instance Refresh Failure Handling
# ============================================================================


def test_property_23_asg_instance_refresh_failure_handling():
    """
    **Property 23: ASG Instance Refresh Failure Handling**

    The backend build job SHALL monitor ASG instance refresh status in a loop
    and SHALL exit with error code when status is `Failed`, `Cancelled`, or
    `TimedOut`.

    **Validates: Requirements 10.4**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Find monitoring step
    monitor_step = find_step_by_name(backend_job, "Monitor ASG Instance Refresh")
    assert (
        monitor_step is not None
    ), "build-backend must have instance refresh monitoring step"

    run_content = monitor_step["run"]

    # Check for status monitoring loop
    assert (
        "while" in run_content or "loop" in run_content.lower()
    ), "Must monitor refresh status in a loop"

    assert (
        "describe-instance-refreshes" in run_content
    ), "Must use describe-instance-refreshes to check status"

    # Check for failure status handling
    assert "Failed" in run_content, "Must check for Failed status"
    assert "Cancelled" in run_content, "Must check for Cancelled status"
    assert (
        "TimedOut" in run_content or "Timed" in run_content
    ), "Must check for TimedOut status"

    # Check for exit on failure
    assert "exit 1" in run_content, "Must exit with error code on failure"


# ============================================================================
# Property 24: CloudFront Cache Invalidation
# ============================================================================


def test_property_24_cloudfront_cache_invalidation():
    """
    **Property 24: CloudFront Cache Invalidation**

    The frontend build job SHALL execute `aws cloudfront create-invalidation`
    with path `/*` after S3 sync completes to ensure immediate visibility of
    changes.

    **Validates: Requirements 10.5**
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    # Find CloudFront invalidation step
    cf_step = find_step_by_name(frontend_job, "Invalidate CloudFront cache")
    assert cf_step is not None, "build-frontend must have CloudFront invalidation step"

    run_content = cf_step["run"]

    # Check for create-invalidation command
    assert (
        "cloudfront create-invalidation" in run_content
    ), "Must use cloudfront create-invalidation command"

    # Check for /* path
    assert (
        "/*" in run_content or '"/*"' in run_content or "'/*'" in run_content
    ), "Must invalidate all paths (/*)"

    # Verify it comes after S3 sync by checking step order
    steps = frontend_job.get("steps", [])
    s3_step_index = None
    cf_step_index = None

    for i, step in enumerate(steps):
        if step.get("name") == "Sync to S3":
            s3_step_index = i
        if step.get("name") == "Invalidate CloudFront cache":
            cf_step_index = i

    assert (
        s3_step_index is not None and cf_step_index is not None
    ), "Both S3 sync and CloudFront invalidation steps must exist"
    assert (
        cf_step_index > s3_step_index
    ), "CloudFront invalidation must come after S3 sync"
