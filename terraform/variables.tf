# Terraform Variables for AI Trading Platform

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "trading-platform"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# Database Configuration
variable "use_rds" {
  description = "Use AWS RDS instead of Kubernetes PostgreSQL"
  type        = bool
  default     = false  # Using Kubernetes PostgreSQL by default (set to true to enable RDS)
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "Initial storage allocation for RDS"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "Maximum storage allocation for RDS"
  type        = number
  default     = 1000
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "trading_platform"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access EKS API server"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# EKS Configuration
variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.27"
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS nodes"
  type        = list(string)
  default     = ["m5.large", "m5.xlarge"]
}

variable "node_group_min_size" {
  description = "Minimum number of nodes in the node group"
  type        = number
  default     = 1
}

variable "node_group_max_size" {
  description = "Maximum number of nodes in the node group"
  type        = number
  default     = 10
}

variable "node_group_desired_size" {
  description = "Desired number of nodes in the node group"
  type        = number
  default     = 3
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.medium"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes in Redis cluster"
  type        = number
  default     = 2
}

variable "redis_auth_token" {
  description = "Auth token for Redis"
  type        = string
  sensitive   = true
}

# InfluxDB Configuration (if using InfluxDB Cloud)
variable "influxdb_url" {
  description = "InfluxDB Cloud URL"
  type        = string
  default     = ""
}

variable "influxdb_token" {
  description = "InfluxDB token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "influxdb_org" {
  description = "InfluxDB organization"
  type        = string
  default     = ""
}

variable "influxdb_bucket" {
  description = "InfluxDB bucket"
  type        = string
  default     = ""
}

# Domain Configuration
variable "domain_name" {
  description = "Primary domain name"
  type        = string
  default     = "tradingplatform.com"
}

variable "api_domain_name" {
  description = "API domain name"
  type        = string
  default     = "api.tradingplatform.com"
}

variable "admin_domain_name" {
  description = "Admin domain name"
  type        = string
  default     = "admin.tradingplatform.com"
}

# SSL Configuration
variable "certificate_arn" {
  description = "ARN of the SSL certificate"
  type        = string
  default     = ""
}

# Monitoring Configuration
variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# Backup Configuration
variable "backup_retention_period" {
  description = "Database backup retention period"
  type        = number
  default     = 7
}

# API Keys and Secrets (configured via admin panel)
variable "system_api_keys" {
  description = "System API keys configuration"
  type = map(object({
    key_name    = string
    description = string
    required    = bool
  }))
  default = {
    alpha_vantage = {
      key_name    = "ALPHA_VANTAGE_API_KEY"
      description = "Alpha Vantage API key for market data"
      required    = false
    }
    polygon = {
      key_name    = "POLYGON_API_KEY"
      description = "Polygon.io API key for market data"
      required    = false
    }
    openai = {
      key_name    = "OPENAI_API_KEY"
      description = "OpenAI API key for ML predictions"
      required    = false
    }
    anthropic = {
      key_name    = "ANTHROPIC_API_KEY"
      description = "Anthropic API key for ML analysis"
      required    = false
    }
    sendgrid = {
      key_name    = "SENDGRID_API_KEY"
      description = "SendGrid API key for email notifications"
      required    = false
    }
    twilio = {
      key_name    = "TWILIO_AUTH_TOKEN"
      description = "Twilio auth token for SMS notifications"
      required    = false
    }
  }
}

# Security Configuration
variable "enable_waf" {
  description = "Enable AWS WAF"
  type        = bool
  default     = true
}

variable "enable_shield" {
  description = "Enable AWS Shield Advanced"
  type        = bool
  default     = false
}

variable "admin_allowed_ips" {
  description = "IP addresses allowed to access admin panel"
  type        = list(string)
  default     = []
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Enable spot instances for non-critical workloads"
  type        = bool
  default     = false
}

variable "enable_autoscaling" {
  description = "Enable cluster autoscaling"
  type        = bool
  default     = true
}

# Feature Flags
variable "enable_real_trading" {
  description = "Enable real trading functionality"
  type        = bool
  default     = false
}

variable "enable_auto_trading" {
  description = "Enable automated trading"
  type        = bool
  default     = false
}

variable "enable_ml_predictions" {
  description = "Enable ML prediction features"
  type        = bool
  default     = true
}

# Compliance
variable "enable_cloudtrail" {
  description = "Enable AWS CloudTrail"
  type        = bool
  default     = true
}

variable "enable_config" {
  description = "Enable AWS Config"
  type        = bool
  default     = true
}

# Performance
variable "enable_performance_insights" {
  description = "Enable RDS Performance Insights"
  type        = bool
  default     = true
}

variable "enable_enhanced_monitoring" {
  description = "Enable RDS Enhanced Monitoring"
  type        = bool
  default     = true
}