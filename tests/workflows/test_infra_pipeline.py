"""
Unit tests for Infrastructure Pipeline workflow structure.

Tests validate that the Infrastructure Pipeline workflow file (.github/workflows/infra.yml)
conforms to the requirements specified in the CI/CD Pipeline Refactor spec.

Requirements validated:
- 1.3: Infrastructure Pipeline manual trigger only
- 1.4: Infrastructure Pipeline excludes application code
- 1.5: Infrastructure Pipeline exports required outputs
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


def test_infra_pipeline_manual_trigger_only():
    """
    Test that Infrastructure Pipeline only triggers manually via workflow_dispatch.

    Validates Requirement 1.3: Infrastructure Pipeline manual trigger only
    """
    workflow = load_workflow(".github/workflows/infra.yml")

    # Get the 'on' key (YAML may parse it as True/False/string)
    triggers = workflow.get("on") or workflow.get(True) or workflow.get("true")

    assert (
        triggers is not None
    ), "Infrastructure Pipeline must have trigger configuration"

    # Handle both dict and list formats
    if isinstance(triggers, dict):
        trigger_keys = triggers.keys()
    elif isinstance(triggers, list):
        trigger_keys = triggers
    else:
        trigger_keys = [triggers]

    # Verify workflow_dispatch trigger exists
    assert (
        "workflow_dispatch" in trigger_keys
    ), "Infrastructure Pipeline must have workflow_dispatch trigger"

    # Verify no automatic triggers exist
    assert (
        "push" not in trigger_keys
    ), "Infrastructure Pipeline must not have push trigger"
    assert (
        "pull_request" not in trigger_keys
    ), "Infrastructure Pipeline must not have pull_request trigger"
    assert (
        "workflow_run" not in trigger_keys
    ), "Infrastructure Pipeline must not have workflow_run trigger"


def test_terraform_core_job_applies_core_infrastructure():
    """
    Test that terraform-core job applies core infrastructure.

    Validates Requirement 1.1: Infrastructure Pipeline provisions core infrastructure
    """
    workflow = load_workflow(".github/workflows/infra.yml")

    # Verify terraform-core job exists
    assert (
        "terraform-core" in workflow["jobs"]
    ), "Infrastructure Pipeline must have terraform-core job"

    core_job = workflow["jobs"]["terraform-core"]

    # Verify terraform apply step exists
    apply_step = find_step_by_name(core_job, "Terraform Apply (Core)")
    assert (
        apply_step is not None
    ), "terraform-core job must have 'Terraform Apply (Core)' step"

    # Verify step runs terraform apply
    assert (
        "terraform apply" in apply_step["run"]
    ), "Terraform Apply step must execute 'terraform apply' command"

    # Verify auto-approve flag is present
    assert (
        "-auto-approve" in apply_step["run"]
    ), "Terraform apply must use -auto-approve flag"

    # Verify working directory is core
    assert (
        "TF_DIR_BASE" in core_job["env"]
    ), "terraform-core job must define TF_DIR_BASE environment variable"


def test_terraform_service_job_applies_service_infrastructure():
    """
    Test that terraform-service job applies service infrastructure.

    Validates Requirement 1.2: Infrastructure Pipeline provisions service infrastructure
    """
    workflow = load_workflow(".github/workflows/infra.yml")

    # Verify terraform-service job exists
    assert (
        "terraform-service" in workflow["jobs"]
    ), "Infrastructure Pipeline must have terraform-service job"

    service_job = workflow["jobs"]["terraform-service"]

    # Verify job depends on terraform-core
    assert "needs" in service_job, "terraform-service job must have 'needs' dependency"
    assert (
        "terraform-core" in service_job["needs"]
        or service_job["needs"] == "terraform-core"
    ), "terraform-service job must depend on terraform-core"

    # Verify terraform apply step exists
    apply_step = find_step_by_name(service_job, "Terraform Apply (Service)")
    assert (
        apply_step is not None
    ), "terraform-service job must have 'Terraform Apply (Service)' step"

    # Verify step runs terraform apply
    assert (
        "terraform apply" in apply_step["run"]
    ), "Terraform Apply step must execute 'terraform apply' command"

    # Verify auto-approve flag is present
    assert (
        "-auto-approve" in apply_step["run"]
    ), "Terraform apply must use -auto-approve flag"

    # Verify working directory is service
    assert (
        "TF_DIR_APP" in service_job["env"]
    ), "terraform-service job must define TF_DIR_APP environment variable"


def test_terraform_service_job_defines_required_outputs():
    """
    Test that terraform-service job defines all required outputs.

    Validates Requirement 1.5: Infrastructure Pipeline exports required outputs
    """
    workflow = load_workflow(".github/workflows/infra.yml")

    service_job = workflow["jobs"]["terraform-service"]

    # Verify job has outputs section
    assert "outputs" in service_job, "terraform-service job must define outputs"

    outputs = service_job["outputs"]

    # Verify all required outputs are defined
    required_outputs = [
        "asg_name",
        "aws_region",
        "ecr_repository_url",
        "backend_port",
        "secrets_kms_key_arn",
    ]

    for output_name in required_outputs:
        assert (
            output_name in outputs
        ), f"terraform-service job must define '{output_name}' output"

        # Verify output references tf_output step
        assert (
            "steps.tf_output.outputs" in outputs[output_name]
        ), f"Output '{output_name}' must reference steps.tf_output.outputs"

    # Verify Get Terraform Outputs step exists
    get_outputs_step = find_step_by_name(service_job, "Get Terraform Outputs")
    assert (
        get_outputs_step is not None
    ), "terraform-service job must have 'Get Terraform Outputs' step"

    # Verify step has correct id
    assert (
        get_outputs_step.get("id") == "tf_output"
    ), "Get Terraform Outputs step must have id 'tf_output'"

    # Verify step runs terraform output commands
    assert (
        "terraform output" in get_outputs_step["run"]
    ), "Get Terraform Outputs step must execute 'terraform output' commands"


def test_no_docker_build_steps():
    """
    Test that Infrastructure Pipeline does not contain Docker build steps.

    Validates Requirement 1.4: Infrastructure Pipeline excludes application code
    """
    workflow = load_workflow(".github/workflows/infra.yml")

    # Check all jobs for Docker-related steps
    for job_name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            step_name = step.get("name", "").lower()
            step_run = step.get("run", "").lower()
            step_uses = step.get("uses", "").lower()

            # Verify no Docker build commands
            assert (
                "docker build" not in step_run
            ), f"Job '{job_name}' must not contain 'docker build' command"
            assert (
                "docker push" not in step_run
            ), f"Job '{job_name}' must not contain 'docker push' command"

            # Verify no Docker build actions
            assert (
                "docker/build-push-action" not in step_uses
            ), f"Job '{job_name}' must not use docker/build-push-action"

            # Verify no Docker-related step names
            assert (
                "docker" not in step_name or "ecr" in step_name
            ), f"Job '{job_name}' must not have Docker build steps (found: {step.get('name')})"


def test_no_npm_build_steps():
    """
    Test that Infrastructure Pipeline does not contain npm build steps.

    Validates Requirement 1.4: Infrastructure Pipeline excludes application code
    """
    workflow = load_workflow(".github/workflows/infra.yml")

    # Check all jobs for npm-related steps
    for job_name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            step_run = step.get("run", "").lower()
            step_uses = step.get("uses", "").lower()

            # Verify no npm commands
            assert (
                "npm install" not in step_run
            ), f"Job '{job_name}' must not contain 'npm install' command"
            assert (
                "npm run build" not in step_run
            ), f"Job '{job_name}' must not contain 'npm run build' command"
            assert (
                "npm ci" not in step_run
            ), f"Job '{job_name}' must not contain 'npm ci' command"

            # Verify no Node.js setup
            assert (
                "actions/setup-node" not in step_uses
            ), f"Job '{job_name}' must not use actions/setup-node"
