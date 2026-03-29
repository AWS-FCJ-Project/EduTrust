resource "aws_cloudwatch_log_metric_filter" "http_4xx" {
  name           = "HTTP4xxCount"
  pattern        = "[level, client, dash, request, status_code=4*]"
  log_group_name = data.terraform_remote_state.core.outputs.container_logs_group_name

  metric_transformation {
    name          = "HTTP_4xx_Count"
    namespace     = "EduTrust/App"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "http_5xx" {
  name           = "HTTP5xxCount"
  pattern        = "[level, client, dash, request, status_code=5*]"
  log_group_name = data.terraform_remote_state.core.outputs.container_logs_group_name

  metric_transformation {
    name          = "HTTP_5xx_Count"
    namespace     = "EduTrust/App"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.ec2_instance_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type       = "text",
        x          = 0,
        y          = 0,
        width      = 24,
        height     = 1,
        properties = { markdown = "# Infrastructure Health Metrics" }
      },
      {
        type   = "metric",
        x      = 0,
        y      = 1,
        width  = 12,
        height = 6,
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.main.arn_suffix, { label = "Total Requests", stat = "Sum" }],
            [".", "HTTPCode_Target_5XX_Count", ".", ".", { label = "Target 5xx", color = "#d13212", stat = "Sum" }],
            [".", "HTTPCode_ELB_5XX_Count", ".", ".", { label = "ELB 5xx", color = "#ff0000", stat = "Sum" }]
          ],
          view   = "timeSeries",
          region = var.aws_region,
          title  = "ALB Throughput & Errors",
          period = 60
        }
      },
      {
        type   = "metric",
        x      = 12,
        y      = 1,
        width  = 12,
        height = 6,
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", aws_lb.main.arn_suffix, { label = "Avg Latency", stat = "Average" }],
            [".", ".", ".", ".", { label = "P90 Latency", stat = "p90" }]
          ],
          view   = "timeSeries",
          region = var.aws_region,
          title  = "Target Response Time (Latency)",
          period = 60
        }
      },
      {
        type   = "log",
        x      = 0,
        y      = 7,
        width  = 24,
        height = 12,
        properties = {
          query  = "SOURCE '${data.terraform_remote_state.core.outputs.container_logs_group_name}' | fields @timestamp, @message | sort @timestamp desc | limit 100",
          region = var.aws_region,
          title  = "Backend Container Logs (Live Feed)",
          view   = "table"
        }
      }
    ]
  })
}
