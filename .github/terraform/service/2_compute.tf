data "aws_key_pair" "existing" {
  key_name           = var.ec2_key_name
  include_public_key = false
}

locals {
  key_name = try(data.aws_key_pair.existing.key_name, aws_key_pair.backend[0].key_name)
}

resource "tls_private_key" "backend" {
  count     = data.aws_key_pair.existing.id == null ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "backend" {
  count      = data.aws_key_pair.existing.id == null ? 1 : 0
  key_name   = var.ec2_key_name
  public_key = tls_private_key.backend[0].public_key_openssh
}

resource "aws_security_group" "backend" {
  name        = "${var.ec2_instance_name}-sg"
  description = "Security group for backend EC2"
  vpc_id      = data.terraform_remote_state.core.outputs.vpc_id

  ingress {
    description     = "App port from ALB"
    from_port       = var.backend_port
    to_port         = var.backend_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "HTTPS outbound"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "HTTP outbound"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "DNS outbound (UDP)"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = var.dns_egress_cidr_blocks
  }

  egress {
    description = "DNS outbound (TCP)"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = var.dns_egress_cidr_blocks
  }

  egress {
    description = "DocumentDB (MongoDB) outbound"
    from_port   = 27017
    to_port     = 27017
    protocol    = "tcp"
    cidr_blocks = var.docdb_egress_cidr_blocks
  }

  egress {
    description = "ElastiCache Redis outbound"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = var.redis_egress_cidr_blocks
  }

  tags = { Name = "${var.ec2_instance_name}-sg" }
}

data "aws_ami" "base_ami" {
  most_recent = true
  owners      = ["self"]
  filter {
    name   = "tag:Name"
    values = ["EduTrust-Base-AMI"]
  }
}

resource "aws_launch_template" "backend" {
  name_prefix   = "${var.ec2_instance_name}-lt-"
  image_id      = data.aws_ami.base_ami.id
  instance_type = var.ec2_instance_type
  key_name      = local.key_name

  iam_instance_profile {
    name = data.terraform_remote_state.core.outputs.backend_instance_profile_name
  }

  vpc_security_group_ids = [aws_security_group.backend.id]
  ebs_optimized          = true

  block_device_mappings {
    device_name = "/dev/sda1"
    ebs {
      volume_size = 20
      encrypted   = true
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  user_data = base64encode(<<-EOF
#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
set -x

echo "--- Starting Deployment Script ---"

if ! command -v docker &> /dev/null; then echo "Error: Docker not installed!"; exit 1; fi
if ! command -v aws &> /dev/null; then echo "Error: AWS CLI not installed!"; exit 1; fi

REGION="${var.aws_region}"
ECR_URL="${data.terraform_remote_state.core.outputs.ecr_repository_url}"
TARGET_DIR="/home/ubuntu/app"
mkdir -p $TARGET_DIR

echo "Logging in to ECR..."
ECR_REGISTRY=$(echo "$ECR_URL" | cut -d'/' -f1)
MAX_RETRIES=10
RETRY_COUNT=0
until aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REGISTRY; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then echo "Failed to login to ECR"; exit 1; fi
  sleep 10
done

echo "Retrieving env from SSM..."
aws ssm get-parameter --name "/edutrust/backend/env" --with-decryption --region $REGION --query "Parameter.Value" --output text > $TARGET_DIR/.env

IMAGE="$ECR_URL:${var.backend_image_tag}"
echo "Pulling image: $IMAGE"
RETRY_COUNT=0
until docker pull $IMAGE; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then echo "Failed to pull image"; exit 1; fi
  sleep 10
done

echo "Starting container..."
docker stop aws-fcj-backend || true
docker rm aws-fcj-backend || true
docker run -d --name aws-fcj-backend \
  --restart unless-stopped \
  -p ${var.backend_port}:${var.backend_port} \
  --env-file $TARGET_DIR/.env \
  $IMAGE

echo "Waiting for application to be healthy..."
HEALTH_CHECK_URL="http://localhost:${var.backend_port}/docs"
MAX_HEALTH_RETRIES=15
HEALTH_RETRY=0
until curl -sf "$HEALTH_CHECK_URL" > /dev/null; do
  HEALTH_RETRY=$((HEALTH_RETRY + 1))
  if [ $HEALTH_RETRY -ge $MAX_HEALTH_RETRIES ]; then
    echo "App failed to start!"
    docker logs aws-fcj-backend
    exit 1
  fi
  sleep 10
done

# CloudWatch Agent Configuration
mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CW_EOF'
{
  "metrics": {
    "namespace": "EduTrust/Core",
    "metrics_collected": {
      "cpu": { "measurement": ["cpu_usage_active"], "totalcpu": true },
      "mem": { "measurement": ["mem_used_percent"] },
      "disk": { "resources": ["/"], "measurement": ["disk_used_percent"] },
      "net": { "resources": ["docker*"], "measurement": ["bytes_recv", "bytes_sent"] }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/lib/docker/containers/*/*.log",
            "log_group_name": "${data.terraform_remote_state.core.outputs.container_logs_group_name}",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
CW_EOF
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "${var.ec2_instance_name}-asg-node" }
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [latest_version]
  }
}

resource "aws_autoscaling_group" "backend" {
  name                = "${var.ec2_instance_name}-asg"
  desired_capacity    = var.asg_desired_capacity
  max_size            = var.asg_max_size
  min_size            = var.asg_min_size
  target_group_arns   = [aws_lb_target_group.backend.arn]
  vpc_zone_identifier = data.terraform_remote_state.core.outputs.private_subnet_ids

  launch_template {
    id      = aws_launch_template.backend.id
    version = "$Latest"
  }

  health_check_type         = "EC2"
  health_check_grace_period = 300
  wait_for_capacity_timeout = "0"
  force_delete              = true
  wait_for_elb_capacity     = 0

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 60
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.ec2_instance_name}-asg"
    propagate_at_launch = true
  }
}
