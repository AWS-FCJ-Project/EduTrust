"""
Unit tests for Application Pipeline build-backend job structure.

Tests validate that the build-backend job in the Application Pipeline workflow file
(.github/workflows/app.yml) conforms to the requirements specified in the CI/CD
Pipeline Refactor spec.

Requirements validated:
- 3.1: Backend build job builds Docker image
- 3.2: Backend build job pushes Docker image to ECR with content-based tag
- 3.3: Backend build job skips build when image exists
- 3.4: Backend build job updates ASG launch template
- 3.5: Backend build job triggers ASG instance refresh
- 10.1: Content-based Docker image tagging
- 10.3: ASG instance refresh safety configuration
- 10.4: ASG instance refresh failure handling
"""

from pathlib import Path

import yaml


def load_workflow(workflow_path: str) -> dict:
    """Load and parse a GitHub Actions workflow YAML file."""
    path = Path(workflow_path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    with open(path, "r") as f:
        return yaml.safe_load(f)


def find_step_by_name(job: dict, step_name: str) -> dict | None:
    """Find a step in a job by its name."""
    for step in job.get("steps", []):
        if step.get("name") == step_name:
            return step
    return None


def find_step_by_id(job: dict, step_id: str) -> dict | None:
    """Find a step in a job by its id."""
    for step in job.get("steps", []):
        if step.get("id") == step_id:
            return step
    return None


def test_content_hash_computation_step_exists():
    """
    Test that build-backend job computes content hash of backend source code.

    Validates Requirements 3.1, 3.2, 10.1: Content-based Docker image tagging
    """
    workflow = load_workflow(".github/workflows/app.yml")

    # Verify build-backend job exists
    assert (
        "build-backend" in workflow["jobs"]
    ), "Application Pipeline must have build-backend job"

    backend_job = workflow["jobs"]["build-backend"]

    # Verify compute hash step exists
    compute_hash_step = find_step_by_name(backend_job, "Compute Docker Context Hash")
    assert (
        compute_hash_step is not None
    ), "build-backend job must have 'Compute Docker Context Hash' step"

    # Verify step has id for output
    assert (
        compute_hash_step.get("id") == "compute_hash"
    ), "Compute Docker Context Hash step must have id 'compute_hash'"

    # Verify step uses sha256sum
    assert (
        "sha256sum" in compute_hash_step["run"]
    ), "Content hash computation must use sha256sum"

    # Verify step includes backend source files
    assert (
        "backend" in compute_hash_step["run"]
    ), "Content hash must include backend directory"

    # Verify step includes Dockerfile
    assert (
        "Dockerfile" in compute_hash_step["run"]
    ), "Content hash must include Dockerfile"

    # Verify step outputs hash
    assert (
        "GITHUB_OUTPUT" in compute_hash_step["run"]
    ), "Compute hash step must write to GITHUB_OUTPUT"
    assert (
        "image_hash" in compute_hash_step["run"]
    ), "Compute hash step must output 'image_hash'"


def test_ecr_image_check_logic_present():
    """
    Test that build-backend job checks if Docker image exists in ECR.

    Validates Requirement 3.3: Skip build when image exists
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Verify check image step exists
    check_image_step = find_step_by_name(backend_job, "Check if Image Exists in ECR")
    assert (
        check_image_step is not None
    ), "build-backend job must have 'Check if Image Exists in ECR' step"

    # Verify step has id for conditional logic
    assert (
        check_image_step.get("id") == "check_image"
    ), "Check image step must have id 'check_image'"

    # Verify step uses aws ecr describe-images
    assert (
        "aws ecr describe-images" in check_image_step["run"]
    ), "Check image step must use 'aws ecr describe-images' command"

    # Verify step checks for image tag
    assert (
        "imageTag" in check_image_step["run"] or "image-ids" in check_image_step["run"]
    ), "Check image step must check for specific image tag"

    # Verify step outputs exists flag
    assert (
        "GITHUB_OUTPUT" in check_image_step["run"]
    ), "Check image step must write to GITHUB_OUTPUT"
    assert (
        "exists" in check_image_step["run"]
    ), "Check image step must output 'exists' flag"


def test_docker_build_conditional_on_image_existence():
    """
    Test that Docker build is conditional on image existence in ECR.

    Validates Requirement 3.3: Skip build when image exists
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Find Docker build step
    build_step = find_step_by_name(backend_job, "Build and Push Docker Image")
    assert (
        build_step is not None
    ), "build-backend job must have 'Build and Push Docker Image' step"

    # Verify step has conditional
    assert (
        "if" in build_step
    ), "Build and Push Docker Image step must have conditional 'if' statement"

    # Verify conditional checks image existence
    condition = build_step["if"]
    assert (
        "check_image.outputs.exists" in condition
    ), "Build conditional must check check_image.outputs.exists"
    assert (
        "== 'false'" in condition or "!=" in condition
    ), "Build conditional must skip when image exists"

    # Verify step uses docker/build-push-action
    assert "docker/build-push-action" in build_step.get(
        "uses", ""
    ), "Build step must use docker/build-push-action"

    # Verify step pushes to ECR
    assert (
        build_step.get("with", {}).get("push") is True
    ), "Build step must have push: true"

    # Verify step uses computed image tag
    tags = build_step.get("with", {}).get("tags", "")
    assert (
        "image_vars.outputs.image" in tags or "steps.image_vars.outputs.image" in tags
    ), "Build step must use image tag from image_vars step"


def test_ssm_parameter_update_step_exists():
    """
    Test that build-backend job updates SSM parameter with backend environment variables.

    Validates Requirement 3.6: Update SSM parameter store
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Find SSM parameter update step
    ssm_step = find_step_by_name(
        backend_job, "Update SSM Parameter with Backend Environment Variables"
    )
    assert (
        ssm_step is not None
    ), "build-backend job must have 'Update SSM Parameter with Backend Environment Variables' step"

    # Verify step uses aws ssm put-parameter
    assert (
        "aws ssm put-parameter" in ssm_step["run"]
    ), "SSM update step must use 'aws ssm put-parameter' command"

    # Verify parameter name
    assert (
        "/edutrust/backend/env" in ssm_step["run"]
    ), "SSM parameter must be named '/edutrust/backend/env'"

    # Verify parameter type is SecureString
    assert "SecureString" in ssm_step["run"], "SSM parameter must be type SecureString"

    # Verify KMS key is used
    assert (
        "--key-id" in ssm_step["run"] or "key-id" in ssm_step["run"]
    ), "SSM parameter must use KMS key for encryption"

    # Verify overwrite flag
    assert (
        "--overwrite" in ssm_step["run"]
    ), "SSM parameter update must use --overwrite flag"


def test_asg_instance_refresh_safety_configuration():
    """
    Test that ASG instance refresh includes safety configuration.

    Validates Requirement 10.3: ASG instance refresh safety configuration
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Find ASG instance refresh step
    refresh_step = find_step_by_name(backend_job, "Start ASG Instance Refresh")
    assert (
        refresh_step is not None
    ), "build-backend job must have 'Start ASG Instance Refresh' step"

    # Verify step uses aws autoscaling start-instance-refresh
    assert (
        "aws autoscaling start-instance-refresh" in refresh_step["run"]
    ), "Refresh step must use 'aws autoscaling start-instance-refresh' command"

    # Verify MinHealthyPercentage is set to 50
    assert (
        "MinHealthyPercentage" in refresh_step["run"]
    ), "Instance refresh must specify MinHealthyPercentage"
    assert "50" in refresh_step["run"], "MinHealthyPercentage must be set to 50"

    # Verify InstanceWarmup is set
    assert (
        "InstanceWarmup" in refresh_step["run"]
    ), "Instance refresh must specify InstanceWarmup"
    assert "60" in refresh_step["run"], "InstanceWarmup must be set to 60 seconds"

    # Verify step outputs refresh ID
    assert (
        "GITHUB_OUTPUT" in refresh_step["run"]
    ), "Start refresh step must write to GITHUB_OUTPUT"
    assert (
        "refresh_id" in refresh_step["run"]
    ), "Start refresh step must output 'refresh_id'"


def test_asg_instance_refresh_failure_handling():
    """
    Test that build-backend job handles ASG instance refresh failures.

    Validates Requirement 10.4: ASG instance refresh failure handling
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Find monitor refresh step
    monitor_step = find_step_by_name(backend_job, "Monitor ASG Instance Refresh")
    assert (
        monitor_step is not None
    ), "build-backend job must have 'Monitor ASG Instance Refresh' step"

    # Verify step monitors refresh status
    assert (
        "aws autoscaling describe-instance-refreshes" in monitor_step["run"]
    ), "Monitor step must use 'aws autoscaling describe-instance-refreshes' command"

    # Verify step checks for Failed status
    assert (
        "Failed" in monitor_step["run"]
    ), "Monitor step must check for 'Failed' status"

    # Verify step checks for Cancelled status
    assert (
        "Cancelled" in monitor_step["run"]
    ), "Monitor step must check for 'Cancelled' status"

    # Verify step checks for TimedOut status
    assert (
        "TimedOut" in monitor_step["run"] or "Timed" in monitor_step["run"]
    ), "Monitor step must check for 'TimedOut' status"

    # Verify step exits with error on failure
    assert (
        "exit 1" in monitor_step["run"]
    ), "Monitor step must exit with error code 1 on failure"

    # Verify step checks for Successful status
    assert (
        "Successful" in monitor_step["run"]
    ), "Monitor step must check for 'Successful' status"

    # Verify step exits successfully on success
    assert (
        "exit 0" in monitor_step["run"]
    ), "Monitor step must exit with code 0 on success"

    # Verify step includes polling loop
    assert (
        "while" in monitor_step["run"] or "sleep" in monitor_step["run"]
    ), "Monitor step must include polling loop"


def test_launch_template_update_step_exists():
    """
    Test that build-backend job updates ASG launch template with new image tag.

    Validates Requirement 3.4: Update ASG launch template
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Find launch template update step
    update_step = find_step_by_name(
        backend_job, "Update Launch Template with New Image Tag"
    )
    assert (
        update_step is not None
    ), "build-backend job must have 'Update Launch Template with New Image Tag' step"

    # Verify step uses terraform apply
    assert (
        "terraform apply" in update_step["run"]
    ), "Launch template update must use 'terraform apply' command"

    # Verify step uses auto-approve flag
    assert (
        "-auto-approve" in update_step["run"]
    ), "Terraform apply must use -auto-approve flag"

    # Verify step passes backend_image_tag variable
    assert (
        "backend_image_tag" in update_step["run"]
    ), "Terraform apply must pass backend_image_tag variable"

    # Verify step uses computed image tag
    assert (
        "IMAGE_TAG" in update_step["run"] or "image_tag" in update_step["run"]
    ), "Launch template update must use computed image tag"


def test_image_variables_step_exists():
    """
    Test that build-backend job sets image variables for use in subsequent steps.

    Validates Requirements 3.2, 10.1: Content-based image tagging
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Find set image variables step
    image_vars_step = find_step_by_name(backend_job, "Set Image Variables")
    assert (
        image_vars_step is not None
    ), "build-backend job must have 'Set Image Variables' step"

    # Verify step has id for outputs
    assert (
        image_vars_step.get("id") == "image_vars"
    ), "Set Image Variables step must have id 'image_vars'"

    # Verify step outputs image
    assert (
        "GITHUB_OUTPUT" in image_vars_step["run"]
    ), "Set Image Variables step must write to GITHUB_OUTPUT"
    assert (
        "image=" in image_vars_step["run"]
    ), "Set Image Variables step must output 'image'"

    # Verify step outputs image_tag
    assert (
        "image_tag=" in image_vars_step["run"]
    ), "Set Image Variables step must output 'image_tag'"

    # Verify step uses computed hash
    assert (
        "compute_hash.outputs.image_hash" in image_vars_step["run"]
    ), "Set Image Variables step must use computed hash from compute_hash step"


def test_job_outputs_defined():
    """
    Test that build-backend job defines outputs for image and image_tag.

    Validates Requirement 3.2: Backend build job outputs
    """
    workflow = load_workflow(".github/workflows/app.yml")
    backend_job = workflow["jobs"]["build-backend"]

    # Verify job has outputs section
    assert "outputs" in backend_job, "build-backend job must define outputs"

    outputs = backend_job["outputs"]

    # Verify image output is defined
    assert "image" in outputs, "build-backend job must define 'image' output"
    assert (
        "image_vars.outputs.image" in outputs["image"]
    ), "image output must reference image_vars.outputs.image"

    # Verify image_tag output is defined
    assert "image_tag" in outputs, "build-backend job must define 'image_tag' output"
    assert (
        "image_vars.outputs.image_tag" in outputs["image_tag"]
    ), "image_tag output must reference image_vars.outputs.image_tag"
