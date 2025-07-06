# AI Trading Platform - AWS Infrastructure with Terraform
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
  }
  
  backend "s3" {
    bucket         = "trading-platform-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "trading-platform-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "AI-Trading-Platform"
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# VPC Configuration
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  
  name = "${var.project_name}-vpc-${var.environment}"
  cidr = var.vpc_cidr
  
  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs
  
  enable_nat_gateway     = true
  single_nat_gateway     = var.environment != "production"
  enable_vpn_gateway     = false
  enable_dns_hostnames   = true
  enable_dns_support     = true
  
  # VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_iam_role  = true
  create_flow_log_cloudwatch_log_group = true
  
  tags = {
    Name = "${var.project_name}-vpc-${var.environment}"
    "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
  }
  
  public_subnet_tags = {
    "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
    "kubernetes.io/role/elb" = "1"
  }
  
  private_subnet_tags = {
    "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
    "kubernetes.io/role/internal-elb" = "1"
  }
}

# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"
  
  cluster_name    = "${var.project_name}-${var.environment}"
  cluster_version = var.kubernetes_version
  
  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true
  cluster_endpoint_public_access_cidrs = var.allowed_cidr_blocks
  
  # Cluster encryption
  cluster_encryption_config = {
    provider_key_arn = aws_kms_key.eks.arn
    resources        = ["secrets"]
  }
  
  # EKS Managed Node Groups
  eks_managed_node_groups = {
    main = {
      name = "main-node-group"
      
      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"
      
      min_size     = var.node_group_min_size
      max_size     = var.node_group_max_size
      desired_size = var.node_group_desired_size
      
      ami_type = "AL2_x86_64"
      
      vpc_security_group_ids = [aws_security_group.eks_nodes.id]
      
      # Launch template configuration
      create_launch_template = true
      launch_template_name   = "${var.project_name}-${var.environment}-node-template"
      
      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = 100
            volume_type           = "gp3"
            iops                  = 3000
            throughput            = 150
            encrypted             = true
            kms_key_id           = aws_kms_key.ebs.arn
            delete_on_termination = true
          }
        }
      }
      
      metadata_options = {
        http_endpoint               = "enabled"
        http_tokens                 = "required"
        http_put_response_hop_limit = 2
        instance_metadata_tags      = "disabled"
      }
      
      tags = {
        Environment = var.environment
        NodeGroup   = "main"
      }
    }
    
    # Separate node group for ML workloads
    ml_workloads = {
      name = "ml-node-group"
      
      instance_types = ["m5.2xlarge", "m5.4xlarge"]
      capacity_type  = "SPOT"
      
      min_size     = 0
      max_size     = 5
      desired_size = 1
      
      ami_type = "AL2_x86_64"
      
      vpc_security_group_ids = [aws_security_group.eks_nodes.id]
      
      # Taints for ML workloads
      taints = {
        ml_workload = {
          key    = "ml-workload"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }
      
      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = 200
            volume_type           = "gp3"
            iops                  = 4000
            throughput            = 250
            encrypted             = true
            kms_key_id           = aws_kms_key.ebs.arn
            delete_on_termination = true
          }
        }
      }
      
      tags = {
        Environment = var.environment
        NodeGroup   = "ml-workloads"
        Purpose     = "machine-learning"
      }
    }
  }
  
  # EKS Add-ons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }
  
  tags = {
    Environment = var.environment
  }
}

# ============================================================================
# RDS PostgreSQL Instance (COMMENTED OUT - Using Kubernetes PostgreSQL)
# ============================================================================
# Uncomment the section below to use AWS RDS instead of Kubernetes PostgreSQL
# Also set variable "use_rds = true" in your terraform.tfvars file
# 
# Benefits of RDS:
# - Automated backups and point-in-time recovery
# - Multi-AZ deployment for high availability
# - Automated software patching
# - Performance insights and monitoring
# - Read replicas for scaling
# Cost: ~$50-80/month for db.t3.medium
# ============================================================================

# resource "aws_db_subnet_group" "main" {
#   count = var.use_rds ? 1 : 0
#   
#   name       = "${var.project_name}-${var.environment}-db-subnet-group"
#   subnet_ids = module.vpc.private_subnets
#   
#   tags = {
#     Name = "${var.project_name}-${var.environment}-db-subnet-group"
#   }
# }

# resource "aws_db_instance" "postgres" {
#   count = var.use_rds ? 1 : 0
#   
#   identifier = "${var.project_name}-${var.environment}-postgres"
#   
#   engine         = "postgres"
#   engine_version = "15.4"
#   instance_class = var.db_instance_class
#   
#   allocated_storage     = var.db_allocated_storage
#   max_allocated_storage = var.db_max_allocated_storage
#   storage_type         = "gp3"
#   storage_encrypted    = true
#   kms_key_id          = aws_kms_key.rds.arn
#   
#   db_name  = var.db_name
#   username = var.db_username
#   password = var.db_password
#   
#   vpc_security_group_ids = [aws_security_group.rds.id]
#   db_subnet_group_name   = aws_db_subnet_group.main[0].name
#   
#   backup_retention_period = var.environment == "production" ? 30 : 7
#   backup_window          = "03:00-04:00"
#   maintenance_window     = "sun:04:00-sun:05:00"
#   
#   skip_final_snapshot       = var.environment != "production"
#   final_snapshot_identifier = var.environment == "production" ? "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null
#   deletion_protection       = var.environment == "production"
#   
#   performance_insights_enabled = true
#   monitoring_interval         = 60
#   monitoring_role_arn         = aws_iam_role.rds_enhanced_monitoring[0].arn
#   
#   tags = {
#     Name = "${var.project_name}-${var.environment}-postgres"
#   }
# }

# ElastiCache Redis Cluster
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-cache-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${var.project_name}-${var.environment}-redis"
  description                = "Redis cluster for ${var.project_name} ${var.environment}"
  
  port                       = 6379
  parameter_group_name       = "default.redis7"
  node_type                  = var.redis_node_type
  num_cache_clusters         = var.redis_num_cache_nodes
  
  engine_version             = "7.0"
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_auth_token
  
  automatic_failover_enabled = var.redis_num_cache_nodes > 1
  multi_az_enabled          = var.redis_num_cache_nodes > 1
  
  snapshot_retention_limit = var.environment == "production" ? 7 : 1
  snapshot_window         = "03:00-05:00"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-redis"
  }
}

# S3 Bucket for Storage
resource "aws_s3_bucket" "storage" {
  bucket = "${var.project_name}-${var.environment}-storage-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket_versioning" "storage" {
  bucket = aws_s3_bucket.storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "storage" {
  bucket = aws_s3_bucket.storage.id
  
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.s3.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }
}

resource "aws_s3_bucket_public_access_block" "storage" {
  bucket = aws_s3_bucket.storage.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Random ID for bucket naming
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# KMS Keys
resource "aws_kms_key" "eks" {
  description             = "EKS Secret Encryption Key for ${var.project_name}-${var.environment}"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  
  tags = {
    Name = "${var.project_name}-${var.environment}-eks-key"
  }
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${var.project_name}-${var.environment}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

resource "aws_kms_key" "ebs" {
  description             = "EBS Encryption Key for ${var.project_name}-${var.environment}"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  
  tags = {
    Name = "${var.project_name}-${var.environment}-ebs-key"
  }
}

resource "aws_kms_alias" "ebs" {
  name          = "alias/${var.project_name}-${var.environment}-ebs"
  target_key_id = aws_kms_key.ebs.key_id
}

# RDS KMS Key (commented out since using Kubernetes PostgreSQL)
# resource "aws_kms_key" "rds" {
#   count = var.use_rds ? 1 : 0
#   
#   description             = "RDS Encryption Key for ${var.project_name}-${var.environment}"
#   deletion_window_in_days = 7
#   enable_key_rotation     = true
#   
#   tags = {
#     Name = "${var.project_name}-${var.environment}-rds-key"
#   }
# }

# resource "aws_kms_alias" "rds" {
#   count = var.use_rds ? 1 : 0
#   
#   name          = "alias/${var.project_name}-${var.environment}-rds"
#   target_key_id = aws_kms_key.rds[0].key_id
# }

resource "aws_kms_key" "s3" {
  description             = "S3 Encryption Key for ${var.project_name}-${var.environment}"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  
  tags = {
    Name = "${var.project_name}-${var.environment}-s3-key"
  }
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${var.project_name}-${var.environment}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# IAM Role for RDS Enhanced Monitoring (commented out since using Kubernetes PostgreSQL)
# resource "aws_iam_role" "rds_enhanced_monitoring" {
#   count = var.use_rds ? 1 : 0
#   
#   name = "${var.project_name}-${var.environment}-rds-monitoring-role"
#   
#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Action = "sts:AssumeRole"
#         Effect = "Allow"
#         Principal = {
#           Service = "monitoring.rds.amazonaws.com"
#         }
#       }
#     ]
#   })
# }

# resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
#   count = var.use_rds ? 1 : 0
#   
#   role       = aws_iam_role.rds_enhanced_monitoring[0].name
#   policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
# }