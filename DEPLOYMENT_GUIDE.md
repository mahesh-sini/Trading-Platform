# 🚀 AI Trading Platform - Production Deployment Guide

## Overview

This guide covers the complete deployment process for the AI Trading Platform from infrastructure setup to production readiness. The platform is designed for enterprise-grade deployment with high availability, security, and scalability.

## 📋 Prerequisites

### Required Tools

Install the following tools on your deployment machine:

```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Terraform
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

### AWS Setup

1. **Configure AWS Credentials**:
   ```bash
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Default region: us-east-1
   # Default output format: json
   ```

2. **Verify AWS Access**:
   ```bash
   aws sts get-caller-identity
   ```

### Environment Variables

Create a `.env.production` file with all required variables:

```bash
# Application Configuration (Using Kubernetes PostgreSQL by default)
DATABASE_URL="postgresql://postgres:secure-password@postgres-service.trading-platform.svc.cluster.local:5432/trading_platform"
REDIS_URL="redis://:password@your-redis-endpoint:6379"
SECRET_KEY="your-32-character-secret-key"
ADMIN_SECRET_KEY="your-32-character-admin-secret"

# Container Registry
GITHUB_TOKEN="your-github-token"
GITHUB_ACTOR="your-github-username"

# Monitoring
GRAFANA_PASSWORD="secure-grafana-password"

# Optional System APIs (can be configured later via admin panel)
ANTHROPIC_API_KEY="your-anthropic-key"
ALPHA_VANTAGE_API_KEY="your-alpha-vantage-key"
OPENAI_API_KEY="your-openai-key"
SENDGRID_API_KEY="your-sendgrid-key"
TWILIO_AUTH_TOKEN="your-twilio-token"
```

## 🏗️ Infrastructure Deployment

### Step 1: Create Terraform Variables

Create `terraform/production.tfvars`:

```hcl
# Project Configuration
project_name = "trading-platform"
environment  = "production"
aws_region   = "us-east-1"

# Network Configuration
vpc_cidr = "10.0.0.0/16"
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

# EKS Configuration
kubernetes_version = "1.27"
node_instance_types = ["m5.large", "m5.xlarge"]
node_group_min_size = 3
node_group_max_size = 10
node_group_desired_size = 3

# Database Configuration (Using Kubernetes PostgreSQL - RDS disabled by default)
use_rds = false  # Set to true if you want to use AWS RDS instead
db_name = "trading_platform"
db_username = "postgres"
db_password = "secure-database-password"

# Uncomment these if enabling RDS (use_rds = true)
# db_instance_class = "db.t3.medium"
# db_allocated_storage = 100
# db_max_allocated_storage = 1000

# Redis Configuration
redis_node_type = "cache.t3.medium"
redis_num_cache_nodes = 2
redis_auth_token = "secure-redis-password"

# Domain Configuration
domain_name = "tradingplatform.com"
api_domain_name = "api.tradingplatform.com"
admin_domain_name = "admin.tradingplatform.com"

# Security Configuration
admin_allowed_ips = ["your.office.ip.address/32"]
enable_waf = true
enable_cloudtrail = true

# Feature Flags
enable_real_trading = false  # Enable after testing
enable_auto_trading = false  # Enable after testing
enable_ml_predictions = true
```

### Step 2: Deploy Infrastructure

```bash
# Navigate to project directory
cd /path/to/trading-platform

# Deploy infrastructure
./scripts/deploy.sh production
```

The deployment script will:

1. ✅ Check prerequisites
2. 🏗️ Deploy AWS infrastructure (VPC, EKS, Redis) - **No RDS, using K8s PostgreSQL**
3. 🐳 Build and push Docker images
4. ☸️ Deploy Kubernetes resources (including PostgreSQL)
5. 🔍 Run health checks
6. 📊 Setup monitoring
7. 🌐 Configure endpoints

💰 **Cost Savings**: Using Kubernetes PostgreSQL saves ~$50-80/month compared to RDS

## 🔧 Manual Steps (If Needed)

### Option 1: Step-by-Step Deployment

If you prefer manual control, you can run each step individually:

```bash
# 1. Deploy infrastructure only
SKIP_BUILD=true ./scripts/deploy.sh production

# 2. Build and push images only
cd terraform && terraform output -json > ../infrastructure-outputs.json && cd ..
SKIP_INFRASTRUCTURE=true ./scripts/deploy.sh production

# 3. Deploy Kubernetes resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/database-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ml-service-deployment.yaml
kubectl apply -f k8s/data-service-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

### Option 2: Terraform Only

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file="production.tfvars" -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Get cluster credentials
aws eks update-kubeconfig --region us-east-1 --name trading-platform-production
```

## 🔐 Security Configuration

### Update Default Admin Credentials

⚠️ **CRITICAL**: Change default admin credentials immediately after deployment!

1. Access admin panel: `https://admin.tradingplatform.com/admin/login`
2. Login with default credentials:
   - Username: `superadmin`
   - Password: `Admin123!@#ChangeMe`
3. **Change password immediately**
4. Enable MFA
5. Update email address
6. Configure IP restrictions

### SSL Certificates

Set up SSL certificates using AWS Certificate Manager:

```bash
# Request certificate
aws acm request-certificate \
    --domain-name tradingplatform.com \
    --subject-alternative-names "*.tradingplatform.com" \
    --validation-method DNS \
    --region us-east-1

# Update ingress with certificate ARN
kubectl patch ingress trading-platform-ingress -n trading-platform \
    --type='merge' \
    -p='{"metadata":{"annotations":{"service.beta.kubernetes.io/aws-load-balancer-ssl-cert":"arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT-ID"}}}'
```

## 🔍 Post-Deployment Verification

### Health Checks

```bash
# Check all services
kubectl get pods -n trading-platform
kubectl get services -n trading-platform
kubectl get ingress -n trading-platform

# Check logs
kubectl logs -l app=backend-api -n trading-platform --tail=50
kubectl logs -l app=frontend -n trading-platform --tail=50

# Test endpoints
curl -f https://api.tradingplatform.com/health
curl -f https://tradingplatform.com
```

### Database Verification

```bash
# Connect to PostgreSQL
kubectl run -i --tty postgres-client --image=postgres:15 --rm --restart=Never -- \
    psql -h postgres-service.trading-platform.svc.cluster.local -U postgres -d trading_platform

# Check tables
\dt
SELECT * FROM admin_users LIMIT 1;
```

### Load Testing

```bash
# Install k6 for load testing
sudo apt-get install k6

# Run load test
k6 run tests/load-test.js
```

## 📊 Monitoring Setup

### Access Monitoring Dashboards

- **Grafana**: `http://grafana.tradingplatform.com:3001`
  - Username: `admin`
  - Password: `$GRAFANA_PASSWORD`

- **Prometheus**: `http://prometheus.tradingplatform.com:9090`

### Configure Alerts

Set up alerts for:

1. **High CPU usage** (>80%)
2. **Memory usage** (>85%)
3. **Database connections** (>80% of max)
4. **API response time** (>500ms)
5. **Error rate** (>1%)
6. **Failed logins** (>5 attempts)

## 🌐 DNS Configuration

Update your DNS records to point to the load balancer:

```bash
# Get load balancer hostname
kubectl get ingress trading-platform-ingress -n trading-platform \
    -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Create DNS records
# A record: tradingplatform.com -> Load Balancer IP
# CNAME: *.tradingplatform.com -> Load Balancer Hostname
```

## 🔧 System API Configuration

Configure system APIs via the admin panel:

1. Login to admin panel
2. Navigate to **System Configuration** → **API Management**
3. Add required APIs:

### Essential APIs

| API Provider | Purpose | Priority |
|--------------|---------|----------|
| Alpha Vantage | Market data, charts | High |
| Yahoo Finance | Backup market data | Medium |
| OpenAI | AI predictions | High |
| SendGrid | Email notifications | High |
| Twilio | SMS alerts | Medium |

### API Configuration Steps

1. Click **"Add API"**
2. Select provider type
3. Enter API credentials
4. Test connection
5. Enable API
6. Configure rate limits

## 🧪 Production Testing

### Smoke Tests

```bash
# Test all critical endpoints
curl -f https://tradingplatform.com/health
curl -f https://api.tradingplatform.com/health
curl -f https://admin.tradingplatform.com/admin/health

# Test admin login
curl -X POST https://admin.tradingplatform.com/admin/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"superadmin","password":"your-new-password"}'

# Test user registration
curl -X POST https://api.tradingplatform.com/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"testpass123"}'
```

### Feature Testing

1. **User Registration/Login**
2. **Portfolio Management**
3. **Market Data Display**
4. **Trading Simulation**
5. **Admin Panel Access**
6. **System Configuration**
7. **Monitoring Dashboard**

## 🔄 CI/CD Pipeline

The platform includes automated CI/CD with GitHub Actions:

### Automatic Deployments

- **Staging**: Triggered on push to `develop` branch
- **Production**: Triggered on push to `main` branch

### Manual Deployment

```bash
# Trigger manual deployment
gh workflow run deploy.yml -f environment=production
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Pod Startup Failures

```bash
# Check pod status
kubectl describe pod <pod-name> -n trading-platform

# Check events
kubectl get events -n trading-platform --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n trading-platform --previous
```

#### 2. Database Connection Issues

```bash
# Check database service
kubectl get service postgres-service -n trading-platform

# Test database connectivity
kubectl run -i --tty postgres-test --image=postgres:15 --rm --restart=Never -- \
    pg_isready -h postgres-service.trading-platform.svc.cluster.local
```

#### 3. Load Balancer Issues

```bash
# Check ingress status
kubectl describe ingress trading-platform-ingress -n trading-platform

# Check AWS Load Balancer
aws elbv2 describe-load-balancers
```

#### 4. SSL Certificate Issues

```bash
# Check certificate status
aws acm describe-certificate --certificate-arn <cert-arn>

# Verify DNS validation
dig _acme-challenge.tradingplatform.com TXT
```

### Log Analysis

```bash
# Centralized logging
kubectl logs -l app=backend-api -n trading-platform --tail=100 -f

# Error analysis
kubectl logs -l app=backend-api -n trading-platform | grep ERROR

# Performance monitoring
kubectl top pods -n trading-platform
```

## 📈 Scaling

### Horizontal Pod Autoscaling

HPAs are configured to scale based on:
- CPU usage (70% threshold)
- Memory usage (80% threshold)

### Cluster Autoscaling

EKS cluster autoscaling is configured to:
- Min nodes: 3
- Max nodes: 10
- Scale up when pods can't be scheduled
- Scale down when nodes are underutilized

### Database Scaling

For production scaling:

1. **Read Replicas**: Add read replicas for read-heavy workloads
2. **Connection Pooling**: Configure PgBouncer
3. **Sharding**: Implement horizontal partitioning if needed

## 🔒 Security Hardening

### Network Security

1. **VPC Configuration**: Private subnets for all services
2. **Security Groups**: Restrictive inbound/outbound rules
3. **Network Policies**: Kubernetes network policies
4. **WAF**: AWS WAF for application protection

### Application Security

1. **RBAC**: Role-based access control
2. **MFA**: Multi-factor authentication
3. **Encryption**: All data encrypted at rest and in transit
4. **Secrets Management**: Kubernetes secrets + AWS Secrets Manager

### Monitoring & Compliance

1. **Audit Logging**: All admin actions logged
2. **CloudTrail**: AWS API call logging
3. **GuardDuty**: Threat detection
4. **Config**: Configuration compliance

## 📞 Support & Maintenance

### Daily Tasks

- [ ] Check system health dashboard
- [ ] Review security alerts
- [ ] Monitor resource usage
- [ ] Check backup status

### Weekly Tasks

- [ ] Review performance metrics
- [ ] Update system monitoring thresholds
- [ ] Check for security updates
- [ ] Review user feedback

### Monthly Tasks

- [ ] Security vulnerability assessment
- [ ] Cost optimization review
- [ ] Capacity planning
- [ ] Update documentation

### Emergency Contacts

- **System Administrator**: admin@tradingplatform.com
- **Security Issues**: security@tradingplatform.com
- **Emergency Hotline**: +1-XXX-XXX-XXXX

## 🎉 Success!

Your AI Trading Platform is now successfully deployed to production!

### Access URLs

- **Main Application**: https://tradingplatform.com
- **API Documentation**: https://api.tradingplatform.com/docs
- **Admin Panel**: https://admin.tradingplatform.com/admin/login
- **Monitoring**: http://grafana.tradingplatform.com:3001

### Next Steps

1. ✅ Configure system APIs in admin panel
2. ✅ Set up monitoring alerts
3. ✅ Create user documentation
4. ✅ Train support team
5. ✅ Launch marketing campaigns

**Remember**: Change all default passwords and enable MFA immediately!