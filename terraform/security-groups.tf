# Security Groups for AI Trading Platform

# ============================================================================
# Security Group for RDS PostgreSQL (COMMENTED OUT - Using Kubernetes PostgreSQL)
# ============================================================================
# Uncomment when using RDS instead of Kubernetes PostgreSQL
# ============================================================================

# resource "aws_security_group" "rds" {
#   count = var.use_rds ? 1 : 0
#   
#   name_prefix = "${var.project_name}-${var.environment}-rds-"
#   vpc_id      = module.vpc.vpc_id
#   
#   description = "Security group for RDS PostgreSQL instance"
#   
#   ingress {
#     description = "PostgreSQL from EKS nodes"
#     from_port   = 5432
#     to_port     = 5432
#     protocol    = "tcp"
#     security_groups = [aws_security_group.eks_nodes.id]
#   }
#   
#   # Allow connections from VPC for debugging (remove in production)
#   ingress {
#     description = "PostgreSQL from VPC"
#     from_port   = 5432
#     to_port     = 5432
#     protocol    = "tcp"
#     cidr_blocks = [module.vpc.vpc_cidr_block]
#   }
#   
#   egress {
#     description = "All outbound traffic"
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
#   
#   tags = {
#     Name = "${var.project_name}-${var.environment}-rds-sg"
#   }
#   
#   lifecycle {
#     create_before_destroy = true
#   }
# }

# Security Group for ElastiCache Redis
resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-${var.environment}-redis-"
  vpc_id      = module.vpc.vpc_id
  
  description = "Security group for ElastiCache Redis cluster"
  
  ingress {
    description = "Redis from EKS nodes"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }
  
  # Allow connections from VPC for debugging (remove in production)
  ingress {
    description = "Redis from VPC"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }
  
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-${var.environment}-redis-sg"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Security Group for EKS Nodes
resource "aws_security_group" "eks_nodes" {
  name_prefix = "${var.project_name}-${var.environment}-eks-nodes-"
  vpc_id      = module.vpc.vpc_id
  
  description = "Security group for EKS worker nodes"
  
  # Allow nodes to communicate with each other
  ingress {
    description = "Node to node communication"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }
  
  # Allow pods to communicate with the EKS cluster API
  ingress {
    description = "EKS cluster API"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    security_groups = [module.eks.cluster_security_group_id]
  }
  
  # Allow worker nodes to receive communication from ALB
  ingress {
    description = "ALB to nodes"
    from_port   = 1025
    to_port     = 65535
    protocol    = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  # NodePort services
  ingress {
    description = "NodePort services"
    from_port   = 30000
    to_port     = 32767
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }
  
  # SSH access (only from bastion or admin IPs)
  dynamic "ingress" {
    for_each = length(var.admin_allowed_ips) > 0 ? [1] : []
    content {
      description = "SSH from admin IPs"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.admin_allowed_ips
    }
  }
  
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-${var.environment}-eks-nodes-sg"
    "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "owned"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Security Group for Application Load Balancer
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-${var.environment}-alb-"
  vpc_id      = module.vpc.vpc_id
  
  description = "Security group for Application Load Balancer"
  
  # HTTP
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # Admin panel access (restricted IPs)
  dynamic "ingress" {
    for_each = length(var.admin_allowed_ips) > 0 ? [1] : []
    content {
      description = "Admin HTTPS access"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = var.admin_allowed_ips
    }
  }
  
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-${var.environment}-alb-sg"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "${var.project_name}-${var.environment}-vpc-endpoints-"
  vpc_id      = module.vpc.vpc_id
  
  description = "Security group for VPC endpoints"
  
  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }
  
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-${var.environment}-vpc-endpoints-sg"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Security Group for Bastion Host (if needed)
resource "aws_security_group" "bastion" {
  count = var.environment == "production" ? 1 : 0
  
  name_prefix = "${var.project_name}-${var.environment}-bastion-"
  vpc_id      = module.vpc.vpc_id
  
  description = "Security group for bastion host"
  
  ingress {
    description = "SSH from admin IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_allowed_ips
  }
  
  egress {
    description = "SSH to private subnets"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.private_subnet_cidrs
  }
  
  egress {
    description = "HTTPS for package updates"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    description = "HTTP for package updates"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-${var.environment}-bastion-sg"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Security Group Rules for EKS Cluster
resource "aws_security_group_rule" "cluster_to_nodes" {
  description              = "Allow cluster to communicate with worker nodes"
  from_port                = 1025
  to_port                  = 65535
  protocol                 = "tcp"
  security_group_id        = module.eks.cluster_security_group_id
  source_security_group_id = aws_security_group.eks_nodes.id
  type                     = "egress"
}

resource "aws_security_group_rule" "nodes_to_cluster" {
  description              = "Allow worker nodes to communicate with cluster API"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.eks_nodes.id
  source_security_group_id = module.eks.cluster_security_group_id
  type                     = "ingress"
}

# Additional security group for monitoring
resource "aws_security_group" "monitoring" {
  name_prefix = "${var.project_name}-${var.environment}-monitoring-"
  vpc_id      = module.vpc.vpc_id
  
  description = "Security group for monitoring services (Prometheus, Grafana)"
  
  # Prometheus
  ingress {
    description = "Prometheus"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
    cidr_blocks = var.admin_allowed_ips
  }
  
  # Grafana
  ingress {
    description = "Grafana"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
    cidr_blocks = var.admin_allowed_ips
  }
  
  # Node Exporter
  ingress {
    description = "Node Exporter"
    from_port   = 9100
    to_port     = 9100
    protocol    = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }
  
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-${var.environment}-monitoring-sg"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}