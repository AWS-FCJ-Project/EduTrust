resource "aws_security_group" "alb" {
  name        = "${var.ec2_instance_name}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = data.terraform_remote_state.core.outputs.vpc_id

  ingress {
    description = "HTTP from Internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from Internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.ec2_instance_name}-alb-sg" }
}

resource "aws_lb" "main" {
  name                       = "${var.ec2_instance_name}-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = data.terraform_remote_state.core.outputs.public_subnet_ids
  drop_invalid_header_fields = true

  enable_deletion_protection = false

  access_logs {
    bucket  = data.terraform_remote_state.core.outputs.alb_logs_bucket_id
    prefix  = "alb"
    enabled = true
  }

  tags = { Name = "${var.ec2_instance_name}-alb" }
}

resource "aws_lb_target_group" "backend" {
  name     = "${var.ec2_instance_name}-tg"
  port     = var.backend_port
  protocol = "HTTP"
  vpc_id   = data.terraform_remote_state.core.outputs.vpc_id

  health_check {
    path                = "/docs"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 3
    interval            = 10
    matcher             = "200"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = data.terraform_remote_state.core.outputs.alb_certificate_arn

  default_action {
    type  = "authenticate-cognito"
    order = 1

    authenticate_cognito {
      user_pool_arn       = data.terraform_remote_state.core.outputs.cognito_user_pool_arn
      user_pool_client_id = data.terraform_remote_state.core.outputs.cognito_user_pool_client_id
      user_pool_domain    = data.terraform_remote_state.core.outputs.cognito_user_pool_domain
    }
  }

  default_action {
    type             = "forward"
    order            = 2
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

resource "aws_route53_record" "alb" {
  zone_id = data.terraform_remote_state.core.outputs.route53_zone_id
  name    = "api.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
