# 🗄️ Database Configuration Guide

## Overview

The AI Trading Platform supports two database deployment options:

1. **Kubernetes PostgreSQL** (Default - Cost Effective)
2. **AWS RDS PostgreSQL** (Enterprise - High Availability)

## 📊 Current Configuration

**✅ Currently Using: Kubernetes PostgreSQL**

- **Cost**: ~$10-20/month (server resources only)
- **Reliability**: Good (single instance with persistent storage)
- **Maintenance**: Manual (backups, updates, monitoring)
- **Location**: Runs inside your Kubernetes cluster

## 🔄 Database Options Comparison

| Feature | Kubernetes PostgreSQL | AWS RDS PostgreSQL |
|---------|----------------------|-------------------|
| **Monthly Cost** | $10-20 | $50-80 |
| **High Availability** | Manual setup | Automatic Multi-AZ |
| **Automated Backups** | Manual setup | Built-in |
| **Point-in-time Recovery** | Manual setup | Built-in |
| **Performance Monitoring** | Basic | Advanced insights |
| **Automated Updates** | Manual | Automatic |
| **Read Replicas** | Manual setup | Easy setup |
| **Scaling** | Manual | Automatic |
| **Setup Complexity** | Simple | Medium |

## 🛠️ Current Setup Details

### Kubernetes PostgreSQL Configuration

```yaml
# Currently deployed in k8s/database-deployment.yaml
Database: PostgreSQL 15
Storage: 100GB persistent volume
Memory: 1-2GB allocated
CPU: 0.5-1 core allocated
Connection: postgres-service.trading-platform.svc.cluster.local:5432
```

### Connection String
```bash
DATABASE_URL="postgresql://postgres:password@postgres-service.trading-platform.svc.cluster.local:5432/trading_platform"
```

## 🔄 How to Switch to AWS RDS (If Needed)

If you want to switch to AWS RDS for production, follow these steps:

### Step 1: Enable RDS in Terraform

Edit `terraform/variables.tf`:
```hcl
variable "use_rds" {
  description = "Use AWS RDS instead of Kubernetes PostgreSQL"
  type        = bool
  default     = true  # Change from false to true
}
```

### Step 2: Uncomment RDS Resources

In `terraform/main.tf`, uncomment these sections:

```hcl
# Uncomment the entire RDS section (lines ~237-285)
resource "aws_db_subnet_group" "main" {
  count = var.use_rds ? 1 : 0
  # ... rest of configuration
}

resource "aws_db_instance" "postgres" {
  count = var.use_rds ? 1 : 0
  # ... rest of configuration
}

# Uncomment RDS security group in security-groups.tf
resource "aws_security_group" "rds" {
  count = var.use_rds ? 1 : 0
  # ... rest of configuration
}

# Uncomment RDS KMS key and monitoring role
resource "aws_kms_key" "rds" {
  count = var.use_rds ? 1 : 0
  # ... rest of configuration
}

resource "aws_iam_role" "rds_enhanced_monitoring" {
  count = var.use_rds ? 1 : 0
  # ... rest of configuration
}
```

### Step 3: Update Variables

Create/update `terraform/production.tfvars`:
```hcl
use_rds = true
db_instance_class = "db.t3.medium"  # or larger for production
db_allocated_storage = 100
db_max_allocated_storage = 1000
db_password = "secure-database-password"
```

### Step 4: Deploy RDS

```bash
cd terraform
terraform plan -var-file="production.tfvars"
terraform apply -var-file="production.tfvars"
```

### Step 5: Migrate Data (If Needed)

If you have existing data in Kubernetes PostgreSQL:

```bash
# 1. Backup existing data
kubectl exec -it postgres-0 -n trading-platform -- pg_dump -U postgres trading_platform > backup.sql

# 2. Get RDS endpoint
terraform output db_instance_endpoint

# 3. Restore to RDS
psql -h YOUR_RDS_ENDPOINT -U postgres -d trading_platform < backup.sql
```

### Step 6: Update Application Configuration

The application will automatically use RDS when `use_rds = true` is set.

## 💾 Backup Strategy

### Current (Kubernetes PostgreSQL)

Manual backups recommended:

```bash
# Daily backup script
kubectl exec -it postgres-0 -n trading-platform -- pg_dump -U postgres trading_platform | gzip > backup-$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip -c backup-20240101.sql.gz | kubectl exec -i postgres-0 -n trading-platform -- psql -U postgres -d trading_platform
```

### With RDS (If Enabled)

Automatic backups included:
- **Automated Backups**: Daily with 7-30 day retention
- **Point-in-time Recovery**: Restore to any second within retention period
- **Cross-Region Backups**: Available for disaster recovery

## 📈 Scaling Considerations

### Current Kubernetes PostgreSQL

For scaling, you can:
1. **Increase Resources**: Modify `k8s/database-deployment.yaml`
2. **Add Storage**: Expand PVC size
3. **Read Replicas**: Deploy additional read-only instances

### With RDS (If Enabled)

AWS RDS provides:
1. **Vertical Scaling**: Change instance types easily
2. **Read Replicas**: Up to 5 read replicas
3. **Multi-AZ**: Automatic failover
4. **Storage Autoscaling**: Automatic storage expansion

## 🔍 Monitoring

### Current Setup

Basic monitoring available:
```bash
# Check database status
kubectl get pods -n trading-platform -l app=postgres

# Check logs
kubectl logs postgres-0 -n trading-platform

# Monitor resource usage
kubectl top pod postgres-0 -n trading-platform
```

### With RDS (If Enabled)

Advanced monitoring:
- **Performance Insights**: Query-level performance monitoring
- **Enhanced Monitoring**: OS-level metrics
- **CloudWatch Integration**: Automated alerting
- **Slow Query Logs**: Automatic query analysis

## 💰 Cost Analysis

### Monthly Costs Breakdown

| Item | Kubernetes PostgreSQL | AWS RDS (db.t3.medium) |
|------|----------------------|------------------------|
| **Compute** | $15 (k8s node share) | $45 (dedicated instance) |
| **Storage** | $10 (100GB EBS) | $12 (100GB gp3) |
| **Backups** | $0 (manual) | $5 (automated) |
| **Monitoring** | $0 (basic) | $8 (performance insights) |
| **Total** | **~$25/month** | **~$70/month** |

## 🚀 Recommendations

### For Development/Testing
- ✅ **Use Kubernetes PostgreSQL** (current setup)
- Lower cost, simpler setup
- Good for learning and development

### For Production at Scale
- ⚡ **Consider AWS RDS**
- Better reliability and automation
- Worth the extra cost for business-critical applications

### Migration Path
1. **Start** with Kubernetes PostgreSQL (current)
2. **Monitor** performance and reliability needs
3. **Migrate** to RDS when business requirements justify the cost

## 🔧 Configuration Files

The following files control database configuration:

- `terraform/variables.tf` - Database type selection
- `terraform/main.tf` - RDS infrastructure (commented out)
- `terraform/security-groups.tf` - RDS security group (commented out)
- `k8s/database-deployment.yaml` - Kubernetes PostgreSQL
- `k8s/secrets.yaml` - Database credentials
- `k8s/configmap.yaml` - Database configuration

## 📞 Support

For database issues:
- **Kubernetes PostgreSQL**: Check pod logs and resource usage
- **RDS Migration**: Contact support for assistance
- **Performance Tuning**: Monitor query performance and connection usage

Your current setup with Kubernetes PostgreSQL is production-ready and cost-effective for most use cases!