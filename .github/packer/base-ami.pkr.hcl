packer {
  required_plugins {
    amazon = {
      version = ">= 1.2.8"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "vpc_id" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "packer_hash" {
  type    = string
  default = "unknown"
}

source "amazon-ebs" "ubuntu" {
  ami_name      = "edutrust-base-ami-{{timestamp}}"
  region        = var.region
  ssh_username  = "ubuntu"
  vpc_id        = var.vpc_id
  subnet_id     = var.subnet_id
  associate_public_ip_address = true

  # --- Cost Optimization: Spot Instances ---
  # Using Spot instances reduces compute cost by up to 90%
  spot_instance_types = ["t3.micro", "t3.small"]
  spot_price          = "auto"

  # --- Cost Optimization: Source AMI Filter ---
  source_ami_filter {
    filters = {
      name                = "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    most_recent = true
    owners      = ["099720109477"] # Canonical
  }

  # --- Cost Optimization: Storage Right-Sizing ---
  # Explicitly using gp3 with minimum required volume size
  launch_block_device_mappings {
    device_name           = "/dev/sda1" # For Ubuntu Noble
    volume_size           = 8           # Minimum size to save storage cost
    volume_type           = "gp3"
    delete_on_termination = true
    throughput            = 125         # Baseline (free tier/min)
    iops                  = 3000        # Baseline (free tier/min)
  }

  # --- AMI Lifecycle Management & Tagging ---
  tags = {
    Name           = "EduTrust-Base-AMI"
    Project        = "EduTrust"
    Environment    = "Production"
    OS             = "Ubuntu-24.04"
    PackerHash     = var.packer_hash
    CreatedBy      = "Packer"
    LifecyclePolicy = "Standard-7-Day-Retention" # Tag for AWS DLM
  }
}

build {
  name    = "edutrust-base-ami"
  sources = ["source.amazon-ebs.ubuntu"]

  provisioner "shell" {
    inline = [
      "echo 'Waiting for cloud-init to complete...'",
      "cloud-init status --wait",
      
      "echo 'Updating system and installing base packages...'",
      "sudo apt-get update -y && sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y",
      "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl jq unzip wget net-tools",
      
      "echo 'Installing Docker...'",
      "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh",
      "sudo sh /tmp/get-docker.sh",
      "sudo systemctl enable --now docker",
      "sudo usermod -aG docker ubuntu",
      
      "echo 'Installing AWS CLI v2...'",
      "curl \"https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip\" -o \"/tmp/awscliv2.zip\"",
      "unzip /tmp/awscliv2.zip -d /tmp/",
      "sudo /tmp/aws/install",
      "rm -rf /tmp/awscliv2.zip /tmp/aws/",
      
      "echo 'Installing CloudWatch Agent...'",
      "wget -P /tmp/ https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb",
      "sudo dpkg -i -E /tmp/amazon-cloudwatch-agent.deb",
      "rm /tmp/amazon-cloudwatch-agent.deb",

      # --- Cost Optimization: Rigorous System Cleanup ---
      # Minimizing AMI size reduces snapshot storage costs
      "echo 'Cleaning up system to minimize AMI size...'",
      "sudo apt-get autoremove -y",
      "sudo apt-get clean",
      "sudo rm -rf /var/lib/apt/lists/*",
      "sudo find /var/log -type f -exec truncate -s 0 {} \\;",
      "sudo rm -rf /tmp/* /var/tmp/*",
      
      "echo 'Cleaning up cloud-init state...'",
      "sudo cloud-init clean --logs --seed",
      "sudo rm -rf /var/lib/cloud/instances/*"
    ]
  }
}
