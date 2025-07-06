# Terraform Outputs for AI Trading Platform

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnets
}

# EKS Outputs
output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = module.eks.cluster_certificate_authority_data
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = module.eks.cluster_oidc_issuer_url
}

output "oidc_provider_arn" {
  description = "The ARN of the OIDC Provider if enabled"
  value       = module.eks.oidc_provider_arn
}

# Node Group Outputs
output "eks_managed_node_groups" {
  description = "Map of attribute maps for all EKS managed node groups created"
  value       = module.eks.eks_managed_node_groups
}

# Database Outputs (RDS - commented out since using Kubernetes PostgreSQL)
# output "db_instance_endpoint" {
#   description = "RDS instance endpoint"
#   value       = var.use_rds ? aws_db_instance.postgres[0].endpoint : null
#   sensitive   = true
# }

# output "db_instance_id" {
#   description = "RDS instance ID"
#   value       = var.use_rds ? aws_db_instance.postgres[0].id : null
# }

# output "db_instance_arn" {
#   description = "RDS instance ARN"
#   value       = var.use_rds ? aws_db_instance.postgres[0].arn : null
# }

# output "db_instance_port" {
#   description = "RDS instance port"
#   value       = var.use_rds ? aws_db_instance.postgres[0].port : null
# }

# output "db_subnet_group_id" {
#   description = "RDS subnet group ID"
#   value       = var.use_rds ? aws_db_subnet_group.main[0].id : null
# }

# Kubernetes PostgreSQL Connection Info
output "kubernetes_database_url" {
  description = "Kubernetes PostgreSQL connection URL"
  value       = "postgresql://${var.db_username}:${var.db_password}@postgres-service.trading-platform.svc.cluster.local:5432/${var.db_name}"
  sensitive   = true
}

# Redis Outputs
output "redis_cluster_id" {
  description = "ElastiCache cluster ID"
  value       = aws_elasticache_replication_group.redis.id
}

output "redis_cluster_endpoint" {
  description = "ElastiCache cluster endpoint"
  value       = aws_elasticache_replication_group.redis.configuration_endpoint_address
  sensitive   = true
}

output "redis_cluster_port" {
  description = "ElastiCache cluster port"
  value       = aws_elasticache_replication_group.redis.port
}

output "redis_cluster_arn" {
  description = "ElastiCache cluster ARN"
  value       = aws_elasticache_replication_group.redis.arn
}

# S3 Outputs
output "s3_bucket_id" {
  description = "S3 bucket ID"
  value       = aws_s3_bucket.storage.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.storage.arn
}

output "s3_bucket_domain_name" {
  description = "S3 bucket domain name"
  value       = aws_s3_bucket.storage.bucket_domain_name
}

# Security Group Outputs
# output "database_security_group_id" {
#   description = "Database security group ID"
#   value       = var.use_rds ? aws_security_group.rds[0].id : null
# }

output "redis_security_group_id" {
  description = "Redis security group ID"
  value       = aws_security_group.redis.id
}

output "eks_nodes_security_group_id" {
  description = "EKS nodes security group ID"
  value       = aws_security_group.eks_nodes.id
}

# KMS Key Outputs
output "eks_kms_key_id" {
  description = "EKS KMS key ID"
  value       = aws_kms_key.eks.key_id
}

output "ebs_kms_key_id" {
  description = "EBS KMS key ID"
  value       = aws_kms_key.ebs.key_id
}

# output "rds_kms_key_id" {
#   description = "RDS KMS key ID"
#   value       = var.use_rds ? aws_kms_key.rds[0].key_id : null
# }

output "s3_kms_key_id" {
  description = "S3 KMS key ID"
  value       = aws_kms_key.s3.key_id
}

# Connection Strings and URLs
output "database_url" {
  description = "Database connection URL"
  value       = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
  sensitive   = true
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://:${var.redis_auth_token}@${aws_elasticache_replication_group.redis.configuration_endpoint_address}:${aws_elasticache_replication_group.redis.port}"
  sensitive   = true
}

# Kubernetes Configuration
output "kubeconfig_update_command" {
  description = "Command to update kubeconfig"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_id}"
}

# Monitoring Outputs
output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name"
  value       = module.vpc.vpc_flow_log_cloudwatch_log_group_name
}

# DNS and Load Balancer
output "load_balancer_dns_name" {
  description = "Load balancer DNS name (will be populated after ALB creation)"
  value       = "Will be available after Kubernetes ingress deployment"
}

# Admin Panel Access
output "admin_panel_info" {
  description = "Admin panel access information"
  value = {
    default_username = "superadmin"
    default_email    = "admin@tradingplatform.dev"
    login_url       = "https://${var.admin_domain_name}/admin/login"
    setup_required  = "Change default password immediately after first login"
  }
  sensitive = true
}

# Deployment Commands
output "deployment_commands" {
  description = "Commands to deploy the application"
  value = {
    update_kubeconfig = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_id}"
    apply_namespaces  = "kubectl apply -f k8s/namespace.yaml"
    apply_secrets     = "kubectl apply -f k8s/secrets.yaml"
    apply_configmaps  = "kubectl apply -f k8s/configmap.yaml"
    apply_databases   = "kubectl apply -f k8s/database-deployment.yaml"
    apply_backend     = "kubectl apply -f k8s/backend-deployment.yaml"
    apply_frontend    = "kubectl apply -f k8s/frontend-deployment.yaml"
    apply_ml_service  = "kubectl apply -f k8s/ml-service-deployment.yaml"
    apply_data_service = "kubectl apply -f k8s/data-service-deployment.yaml"
    apply_ingress     = "kubectl apply -f k8s/ingress.yaml"
  }
}

# Environment Configuration
output "environment_variables" {
  description = "Environment variables for application configuration"
  value = {
    # Using Kubernetes PostgreSQL instead of RDS
    DATABASE_URL = "postgresql://${var.db_username}:${var.db_password}@postgres-service.trading-platform.svc.cluster.local:5432/${var.db_name}"
    REDIS_URL    = "redis://:${var.redis_auth_token}@${aws_elasticache_replication_group.redis.configuration_endpoint_address}:${aws_elasticache_replication_group.redis.port}"
    AWS_REGION   = var.aws_region
    S3_BUCKET    = aws_s3_bucket.storage.id
    ENVIRONMENT  = var.environment
  }
  sensitive = true
}

# Security Information
output "security_groups" {
  description = "Security group information"
  value = {
    # database_sg = aws_security_group.rds.id  # Commented out since using Kubernetes PostgreSQL
    redis_sg    = aws_security_group.redis.id
    eks_nodes_sg = aws_security_group.eks_nodes.id
  }
}

# Cost Optimization Info
output "cost_optimization_notes" {
  description = "Cost optimization recommendations"
  value = {
    spot_instances_enabled = var.enable_spot_instances
    autoscaling_enabled    = var.enable_autoscaling
    single_nat_gateway     = var.environment != "production" ? true : false
    recommendations = [
      "Enable spot instances for non-production workloads",
      "Use scheduled scaling for predictable traffic patterns",
      "Monitor unused resources with AWS Cost Explorer",
      "Consider Reserved Instances for production databases"
    ]
  }
}