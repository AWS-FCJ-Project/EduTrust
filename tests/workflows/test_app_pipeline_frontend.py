"""
Unit tests for Application Pipeline build-frontend job structure.

Tests validate that the build-frontend job in the Application Pipeline workflow file
(.github/workflows/app.yml) conforms to the requirements specified in the CI/CD
Pipeline Refactor spec.

Requirements validated:
- 4.1: Frontend build job builds static assets
- 4.2: Frontend build job uploads assets to S3
- 4.3: Frontend build job deletes removed files from S3
- 4.4: Frontend build job invalidates CloudFront cache
- 5.2: Frontend build job does not depend on backend build job
- 5.3: Frontend build job executes in parallel with backend
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


def test_frontend_job_does_not_depend_on_backend():
    """
    Test that build-frontend job does not depend on build-backend job.

    Validates Requirements 5.2, 5.3: Parallel build execution
    """
    workflow = load_workflow(".github/workflows/app.yml")

    # Verify build-frontend job exists
    assert (
        "build-frontend" in workflow["jobs"]
    ), "Application Pipeline must have build-frontend job"

    frontend_job = workflow["jobs"]["build-frontend"]

    # Verify job does not have needs dependency on build-backend
    needs = frontend_job.get("needs", [])
    if isinstance(needs, str):
        needs = [needs]

    assert (
        "build-backend" not in needs
    ), "build-frontend job must not depend on build-backend job (should run in parallel)"

    # Verify job does not have conditional based on build-backend
    job_if = frontend_job.get("if", "")
    assert (
        "build-backend" not in job_if
    ), "build-frontend job must not have conditional based on build-backend job"


def test_npm_install_step_exists():
    """
    Test that build-frontend job runs npm install.

    Validates Requirement 4.1: Frontend build job builds static assets
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    # Find npm install step
    install_step = find_step_by_name(frontend_job, "Install dependencies")
    assert (
        install_step is not None
    ), "build-frontend job must have 'Install dependencies' step"

    # Verify step runs npm install
    assert (
        "npm install" in install_step["run"]
    ), "Install dependencies step must run 'npm install' command"

    # Verify step runs in frontend directory
    working_dir = install_step.get("working-directory", "")
    assert "frontend" in working_dir, "npm install must run in frontend directory"


def test_npm_build_step_exists():
    """
    Test that build-frontend job runs npm run build.

    Validates Requirement 4.1: Frontend build job builds static assets
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    # Find npm build step
    build_step = find_step_by_name(frontend_job, "Build frontend")
    assert build_step is not None, "build-frontend job must have 'Build frontend' step"

    # Verify step runs npm run build
    assert (
        "npm run build" in build_step["run"]
    ), "Build frontend step must run 'npm run build' command"

    # Verify step runs in frontend directory
    working_dir = build_step.get("working-directory", "")
    assert "frontend" in working_dir, "npm run build must run in frontend directory"


def test_s3_sync_includes_delete_flag():
    """
    Test that S3 sync includes --delete flag to remove old files.

    Validates Requirements 4.2, 4.3: Frontend deployment with file cleanup
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    # Find S3 sync step
    s3_sync_step = find_step_by_name(frontend_job, "Sync to S3")
    assert s3_sync_step is not None, "build-frontend job must have 'Sync to S3' step"

    # Verify step uses aws s3 sync
    assert (
        "aws s3 sync" in s3_sync_step["run"]
    ), "S3 sync step must use 'aws s3 sync' command"

    # Verify step includes --delete flag
    assert (
        "--delete" in s3_sync_step["run"]
    ), "S3 sync must include --delete flag to remove old files"

    # Verify step syncs frontend output directory
    assert (
        "frontend/out" in s3_sync_step["run"] or "out/" in s3_sync_step["run"]
    ), "S3 sync must upload frontend build output directory"

    # Verify step syncs to S3 bucket
    assert "s3://" in s3_sync_step["run"], "S3 sync must target S3 bucket"
    assert (
        "S3_BUCKET" in s3_sync_step["run"]
    ), "S3 sync must use S3_BUCKET environment variable"


def test_cloudfront_invalidation_step_exists():
    """
    Test that CloudFront cache invalidation step exists after S3 sync.

    Validates Requirement 4.4: CloudFront cache invalidation
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    # Find CloudFront invalidation step
    cf_invalidation_step = find_step_by_name(
        frontend_job, "Invalidate CloudFront cache"
    )
    assert (
        cf_invalidation_step is not None
    ), "build-frontend job must have 'Invalidate CloudFront cache' step"

    # Verify step uses aws cloudfront create-invalidation
    assert (
        "aws cloudfront create-invalidation" in cf_invalidation_step["run"]
    ), "CloudFront invalidation step must use 'aws cloudfront create-invalidation' command"

    # Verify step invalidates all paths
    assert (
        "--paths" in cf_invalidation_step["run"]
    ), "CloudFront invalidation must specify --paths"
    assert (
        "/*" in cf_invalidation_step["run"]
    ), "CloudFront invalidation must invalidate all paths (/*)"

    # Verify step uses distribution ID
    assert (
        "--distribution-id" in cf_invalidation_step["run"]
    ), "CloudFront invalidation must specify --distribution-id"
    assert (
        "CLOUDFRONT_DIST_ID" in cf_invalidation_step["run"]
    ), "CloudFront invalidation must use CLOUDFRONT_DIST_ID environment variable"


def test_cloudfront_invalidation_after_s3_sync():
    """
    Test that CloudFront invalidation step comes after S3 sync step.

    Validates Requirement 4.4: CloudFront cache invalidation after S3 upload
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    steps = frontend_job.get("steps", [])

    # Find indices of S3 sync and CloudFront invalidation steps
    s3_sync_index = None
    cf_invalidation_index = None

    for i, step in enumerate(steps):
        if step.get("name") == "Sync to S3":
            s3_sync_index = i
        elif step.get("name") == "Invalidate CloudFront cache":
            cf_invalidation_index = i

    assert s3_sync_index is not None, "build-frontend job must have 'Sync to S3' step"
    assert (
        cf_invalidation_index is not None
    ), "build-frontend job must have 'Invalidate CloudFront cache' step"

    # Verify CloudFront invalidation comes after S3 sync
    assert (
        cf_invalidation_index > s3_sync_index
    ), "CloudFront invalidation must occur after S3 sync"


def test_nodejs_setup_step_exists():
    """
    Test that build-frontend job sets up Node.js environment.

    Validates Requirement 4.1: Frontend build job builds static assets
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    # Find Node.js setup step
    nodejs_step = find_step_by_name(frontend_job, "Setup Node.js")
    assert nodejs_step is not None, "build-frontend job must have 'Setup Node.js' step"

    # Verify step uses actions/setup-node
    assert "actions/setup-node" in nodejs_step.get(
        "uses", ""
    ), "Node.js setup step must use actions/setup-node action"

    # Verify Node.js version is specified
    with_config = nodejs_step.get("with", {})
    assert "node-version" in with_config, "Node.js setup must specify node-version"

    # Verify npm cache is enabled
    assert (
        "cache" in with_config
    ), "Node.js setup should enable npm cache for faster builds"
    assert with_config["cache"] == "npm", "Node.js setup cache must be set to 'npm'"


def test_aws_credentials_configured():
    """
    Test that build-frontend job configures AWS credentials.

    Validates Requirements 4.2, 4.4: AWS service access for S3 and CloudFront
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    # Find AWS credentials configuration step
    aws_creds_step = find_step_by_name(frontend_job, "Configure AWS credentials")
    assert (
        aws_creds_step is not None
    ), "build-frontend job must have 'Configure AWS credentials' step"

    # Verify step uses aws-actions/configure-aws-credentials
    assert "aws-actions/configure-aws-credentials" in aws_creds_step.get(
        "uses", ""
    ), "AWS credentials step must use aws-actions/configure-aws-credentials action"

    # Verify credentials are configured
    with_config = aws_creds_step.get("with", {})
    assert (
        "aws-access-key-id" in with_config
    ), "AWS credentials must include aws-access-key-id"
    assert (
        "aws-secret-access-key" in with_config
    ), "AWS credentials must include aws-secret-access-key"
    assert "aws-region" in with_config, "AWS credentials must include aws-region"


def test_frontend_job_has_required_environment_variables():
    """
    Test that build-frontend job defines required environment variables.

    Validates Requirements 4.2, 4.4: S3 bucket and CloudFront distribution configuration
    """
    workflow = load_workflow(".github/workflows/app.yml")
    frontend_job = workflow["jobs"]["build-frontend"]

    # Verify job has env section
    assert "env" in frontend_job, "build-frontend job must define environment variables"

    env_vars = frontend_job["env"]

    # Verify S3_BUCKET is defined
    assert (
        "S3_BUCKET" in env_vars
    ), "build-frontend job must define S3_BUCKET environment variable"

    # Verify CLOUDFRONT_DIST_ID is defined
    assert (
        "CLOUDFRONT_DIST_ID" in env_vars
    ), "build-frontend job must define CLOUDFRONT_DIST_ID environment variable"

    # Verify AWS credentials are defined
    assert (
        "AWS_ACCESS_KEY_ID" in env_vars
    ), "build-frontend job must define AWS_ACCESS_KEY_ID environment variable"
    assert (
        "AWS_SECRET_ACCESS_KEY" in env_vars
    ), "build-frontend job must define AWS_SECRET_ACCESS_KEY environment variable"
