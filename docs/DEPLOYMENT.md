# AI Trading Platform - Deployment Guide

## Overview

This guide covers the complete deployment process for the AI Trading Platform, from local development to production deployment on AWS with Kubernetes orchestration.

## Prerequisites

### Required Tools
- Docker & Docker Compose
- Kubernetes CLI (kubectl)
- Helm 3.x
- AWS CLI
- Terraform (for infrastructure)
- Node.js 18+ and Python 3.9+

### AWS Services Required
- Amazon EKS (Kubernetes)
- Amazon RDS (PostgreSQL)
- Amazon ElastiCache (Redis)
- Amazon InfluxDB Cloud or self-hosted InfluxDB
- Amazon S3 (storage)
- Amazon CloudFront (CDN)
- Amazon Route 53 (DNS)
- Amazon Certificate Manager (SSL)

## Environment Setup

### 1. Local Development Environment

#### Docker Compose Setup
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: trading_platform
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: password
      DOCKER_INFLUXDB_INIT_ORG: trading-platform
      DOCKER_INFLUXDB_INIT_BUCKET: market-data
    volumes:
      - influxdb_data:/var/lib/influxdb2

  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

volumes:
  postgres_data:
  redis_data:
  influxdb_data:
```

#### Environment Variables
```bash
# .env.local
NODE_ENV=development
API_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_platform
REDIS_URL=redis://localhost:6379
INFLUXDB_URL=http://localhost:8086
KAFKA_BROKERS=localhost:9092

# API Keys
ANTHROPIC_API_KEY=your_anthropic_key
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
POLYGON_API_KEY=your_polygon_key

# JWT
JWT_SECRET=your_jwt_secret_key
JWT_EXPIRES_IN=24h

# Stripe
STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

#### Start Local Environment
```bash
# Start infrastructure services
docker-compose -f docker-compose.dev.yml up -d

# Install dependencies
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
cd ../ml-service && pip install -r requirements.txt

# Run database migrations
cd backend && alembic upgrade head

# Start services
# Terminal 1: Backend API
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: ML Service
cd ml-service && python -m uvicorn main:app --reload --port 8001

# Terminal 4: Data Service
cd data-service && python -m uvicorn main:app --reload --port 8002
```

### 2. Staging Environment

#### AWS Infrastructure Setup with Terraform

```hcl
# infrastructure/main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC Configuration
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "trading-platform-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
  
  tags = {
    Environment = var.environment
  }
}

# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  
  cluster_name    = "trading-platform-${var.environment}"
  cluster_version = "1.27"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  node_groups = {
    main = {
      desired_capacity = 3
      max_capacity     = 10
      min_capacity     = 1
      
      instance_types = ["m5.large"]
      
      k8s_labels = {
        Environment = var.environment
      }
    }
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "postgres" {
  identifier = "trading-platform-${var.environment}"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true
  
  db_name  = "trading_platform"
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = var.environment != "production"
  
  tags = {
    Environment = var.environment
  }
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "main" {
  name       = "trading-platform-cache-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "trading-platform-${var.environment}"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
  
  tags = {
    Environment = var.environment
  }
}
```

#### Deploy Infrastructure
```bash
# Initialize Terraform
cd infrastructure
terraform init

# Plan deployment
terraform plan -var-file="staging.tfvars"

# Apply infrastructure
terraform apply -var-file="staging.tfvars"

# Get EKS credentials
aws eks update-kubeconfig --region us-west-2 --name trading-platform-staging
```

### 3. Kubernetes Deployment

#### Namespace Setup
```yaml
# k8s/namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: trading-platform
  labels:
    name: trading-platform
---
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
  labels:
    name: monitoring
```

#### Secrets Management
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: trading-platform
type: Opaque
data:
  database-url: <base64-encoded-database-url>
  redis-url: <base64-encoded-redis-url>
  jwt-secret: <base64-encoded-jwt-secret>
  stripe-secret: <base64-encoded-stripe-secret>
  anthropic-api-key: <base64-encoded-anthropic-key>
  alpaca-api-key: <base64-encoded-alpaca-key>
  alpaca-secret: <base64-encoded-alpaca-secret>
```

#### ConfigMaps
```yaml
# k8s/configmaps.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: trading-platform
data:
  NODE_ENV: "staging"
  LOG_LEVEL: "info"
  API_VERSION: "v1"
  CORS_ORIGIN: "https://staging.tradingplatform.com"
  RATE_LIMIT_WINDOW: "900000"
  RATE_LIMIT_MAX: "1000"
```

#### Backend API Deployment
```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-api
  namespace: trading-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend-api
  template:
    metadata:
      labels:
        app: backend-api
    spec:
      containers:
      - name: backend-api
        image: your-registry/trading-platform-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
        envFrom:
        - configMapRef:
            name: app-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: backend-api-service
  namespace: trading-platform
spec:
  selector:
    app: backend-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

#### Frontend Deployment
```yaml
# k8s/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: trading-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: your-registry/trading-platform-frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "https://api-staging.tradingplatform.com"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: trading-platform
spec:
  selector:
    app: frontend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: ClusterIP
```

#### ML Service Deployment
```yaml
# k8s/ml-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-service
  namespace: trading-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ml-service
  template:
    metadata:
      labels:
        app: ml-service
    spec:
      containers:
      - name: ml-service
        image: your-registry/trading-platform-ml:latest
        ports:
        - containerPort: 8001
        env:
        - name: MODEL_PATH
          value: "/models"
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        volumeMounts:
        - name: model-storage
          mountPath: /models
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: ml-models-pvc
```

#### Ingress Configuration
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: trading-platform-ingress
  namespace: trading-platform
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/use-regex: "true"
spec:
  tls:
  - hosts:
    - staging.tradingplatform.com
    - api-staging.tradingplatform.com
    secretName: trading-platform-tls
  rules:
  - host: staging.tradingplatform.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
  - host: api-staging.tradingplatform.com
    http:
      paths:
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: backend-api-service
            port:
              number: 80
```

### 4. Helm Charts

#### Chart Structure
```
helm/
├── trading-platform/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-staging.yaml
│   ├── values-production.yaml
│   └── templates/
│       ├── backend/
│       ├── frontend/
│       ├── ml-service/
│       ├── data-service/
│       ├── configmaps.yaml
│       ├── secrets.yaml
│       └── ingress.yaml
```

#### Chart.yaml
```yaml
apiVersion: v2
name: trading-platform
description: AI-Powered Trading Platform Helm Chart
type: application
version: 1.0.0
appVersion: "1.0.0"
dependencies:
- name: postgresql
  version: 12.x.x
  repository: https://charts.bitnami.com/bitnami
  condition: postgresql.enabled
- name: redis
  version: 17.x.x
  repository: https://charts.bitnami.com/bitnami
  condition: redis.enabled
```

#### Values.yaml
```yaml
# Default values for trading-platform
global:
  imageRegistry: ""
  imagePullSecrets: []
  
replicaCount:
  backend: 3
  frontend: 2
  mlService: 2
  dataService: 2

image:
  backend:
    repository: trading-platform/backend
    tag: "latest"
    pullPolicy: IfNotPresent
  frontend:
    repository: trading-platform/frontend
    tag: "latest"
    pullPolicy: IfNotPresent

service:
  type: ClusterIP
  backend:
    port: 80
    targetPort: 8000
  frontend:
    port: 80
    targetPort: 3000

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: tradingplatform.com
      paths:
        - path: /
          pathType: Prefix
          service: frontend
    - host: api.tradingplatform.com
      paths:
        - path: /v1
          pathType: Prefix
          service: backend
  tls:
    - secretName: trading-platform-tls
      hosts:
        - tradingplatform.com
        - api.tradingplatform.com

resources:
  backend:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "500m"
  frontend:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "250m"

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80

postgresql:
  enabled: false
  external:
    host: "your-rds-endpoint"
    port: 5432
    database: "trading_platform"

redis:
  enabled: false
  external:
    host: "your-elasticache-endpoint"
    port: 6379
```

#### Deploy with Helm
```bash
# Add required repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install staging environment
helm install trading-platform-staging ./helm/trading-platform \
  -f ./helm/trading-platform/values-staging.yaml \
  --namespace trading-platform \
  --create-namespace

# Upgrade deployment
helm upgrade trading-platform-staging ./helm/trading-platform \
  -f ./helm/trading-platform/values-staging.yaml \
  --namespace trading-platform
```

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy Trading Platform

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: trading-platform

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
    
    - name: Install dependencies
      run: |
        cd backend && pip install -r requirements.txt
        cd ../frontend && npm ci
    
    - name: Run tests
      run: |
        cd backend && python -m pytest
        cd ../frontend && npm test
    
    - name: Run security scans
      run: |
        cd backend && bandit -r .
        cd ../frontend && npm audit

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push Docker images
      run: |
        # Backend
        docker build -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.sha }} ./backend
        docker push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.sha }}
        
        # Frontend
        docker build -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.sha }} ./frontend
        docker push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.sha }}
        
        # ML Service
        docker build -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-ml:${{ github.sha }} ./ml-service
        docker push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-ml:${{ github.sha }}

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-west-2
    
    - name: Update kubeconfig
      run: aws eks update-kubeconfig --name trading-platform-staging
    
    - name: Deploy to staging
      run: |
        helm upgrade trading-platform-staging ./helm/trading-platform \
          -f ./helm/trading-platform/values-staging.yaml \
          --set image.backend.tag=${{ github.sha }} \
          --set image.frontend.tag=${{ github.sha }} \
          --set image.mlService.tag=${{ github.sha }} \
          --namespace trading-platform

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-west-2
    
    - name: Update kubeconfig
      run: aws eks update-kubeconfig --name trading-platform-production
    
    - name: Deploy to production
      run: |
        helm upgrade trading-platform-production ./helm/trading-platform \
          -f ./helm/trading-platform/values-production.yaml \
          --set image.backend.tag=${{ github.sha }} \
          --set image.frontend.tag=${{ github.sha }} \
          --set image.mlService.tag=${{ github.sha }} \
          --namespace trading-platform
```

## Monitoring & Logging

### Prometheus & Grafana Setup
```bash
# Install monitoring stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Install Grafana dashboards
kubectl apply -f monitoring/grafana-dashboards.yaml
```

### Application Metrics
```python
# backend/monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_TRADES = Gauge('active_trades_total', 'Number of active trades')
PREDICTION_ACCURACY = Gauge('prediction_accuracy', 'Model prediction accuracy', ['model', 'timeframe'])

# Middleware for metrics collection
@app.middleware("http")
async def add_metrics(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.observe(duration)
    
    return response
```

## Security Hardening

### Network Policies
```yaml
# k8s/network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-api-netpol
  namespace: trading-platform
spec:
  podSelector:
    matchLabels:
      app: backend-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 5432  # PostgreSQL
    - protocol: TCP
      port: 6379  # Redis
    - protocol: TCP
      port: 443   # HTTPS
```

### Pod Security Standards
```yaml
# k8s/pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: trading-platform-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## Backup & Disaster Recovery

### Database Backup Strategy
```bash
#!/bin/bash
# scripts/backup-database.sh

# Automated PostgreSQL backup
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="trading_platform_backup_${DATE}.sql"

# Create backup
pg_dump $DATABASE_URL > "${BACKUP_DIR}/${BACKUP_FILE}"

# Compress backup
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# Upload to S3
aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}.gz" s3://trading-platform-backups/postgres/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```

### Disaster Recovery Plan
1. **RTO (Recovery Time Objective)**: 15 minutes
2. **RPO (Recovery Point Objective)**: 1 minute
3. **Multi-region deployment** with automatic failover
4. **Database replication** with read replicas
5. **Automated backup verification** and restoration testing

## Production Checklist

### Pre-deployment
- [ ] Security scan completed
- [ ] Load testing performed
- [ ] Backup strategy verified
- [ ] Monitoring configured
- [ ] SSL certificates validated
- [ ] DNS configuration verified
- [ ] Database migrations tested
- [ ] Environment variables configured
- [ ] Rate limiting configured
- [ ] Logging configured

### Post-deployment
- [ ] Health checks passing
- [ ] Metrics collection verified
- [ ] Alerting rules configured
- [ ] Performance baseline established
- [ ] Security monitoring active
- [ ] Backup schedules running
- [ ] Documentation updated
- [ ] Team notifications sent

## Troubleshooting

### Common Issues
1. **Pod startup failures**: Check resource limits and dependencies
2. **Database connection errors**: Verify network policies and credentials
3. **High latency**: Check resource allocation and database queries
4. **Memory leaks**: Monitor application metrics and restart policies
5. **Certificate issues**: Verify cert-manager and DNS configuration

### Debugging Commands
```bash
# Check pod status
kubectl get pods -n trading-platform

# View pod logs
kubectl logs -f deployment/backend-api -n trading-platform

# Exec into pod
kubectl exec -it deployment/backend-api -n trading-platform -- /bin/bash

# Check resource usage
kubectl top pods -n trading-platform

# View events
kubectl get events -n trading-platform --sort-by='.lastTimestamp'
```

This comprehensive deployment guide covers all aspects of deploying the AI Trading Platform from development to production with proper monitoring, security, and disaster recovery procedures.