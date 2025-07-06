#!/bin/bash
# AI Trading Platform - Production Deployment Script

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME="trading-platform"
CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    local tools=("aws" "kubectl" "helm" "docker" "terraform")
    for tool in "${tools[@]}"; do
        if ! command -v $tool &> /dev/null; then
            log_error "$tool is not installed or not in PATH"
            exit 1
        fi
    done
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi
    
    # Check required environment variables
    local required_vars=("DATABASE_URL" "REDIS_URL" "SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Environment variable $var is not set"
            exit 1
        fi
    done
    
    log_success "All prerequisites met"
}

deploy_infrastructure() {
    log_info "Deploying AWS infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    terraform init -upgrade
    
    # Plan the deployment
    terraform plan -var-file="${ENVIRONMENT}.tfvars" -out=tfplan
    
    # Apply the plan
    log_info "Applying Terraform plan..."
    terraform apply tfplan
    
    # Get outputs
    aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME
    
    cd ..
    log_success "Infrastructure deployed successfully"
}

build_and_push_images() {
    log_info "Building and pushing Docker images..."
    
    # Set image registry
    local registry="ghcr.io/trading-platform"
    local tag="${GITHUB_SHA:-$(git rev-parse --short HEAD)}"
    
    # Login to GitHub Container Registry
    echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin
    
    # Build and push each service
    local services=("backend" "frontend" "ml_models" "data")
    for service in "${services[@]}"; do
        log_info "Building $service image..."
        docker build -t "${registry}/${service}:${tag}" ./$service
        docker push "${registry}/${service}:${tag}"
        
        # Tag as latest for production
        if [[ $ENVIRONMENT == "production" ]]; then
            docker tag "${registry}/${service}:${tag}" "${registry}/${service}:latest"
            docker push "${registry}/${service}:latest"
        fi
    done
    
    log_success "All images built and pushed"
}

prepare_kubernetes_secrets() {
    log_info "Preparing Kubernetes secrets..."
    
    # Base64 encode secrets
    local db_url_b64=$(echo -n "$DATABASE_URL" | base64)
    local redis_url_b64=$(echo -n "$REDIS_URL" | base64)
    local secret_key_b64=$(echo -n "$SECRET_KEY" | base64)
    local admin_secret_b64=$(echo -n "$ADMIN_SECRET_KEY" | base64)
    
    # Update secrets file
    sed -i "s/REPLACE_WITH_BASE64_DATABASE_URL/$db_url_b64/g" k8s/secrets.yaml
    sed -i "s/REPLACE_WITH_BASE64_REDIS_URL/$redis_url_b64/g" k8s/secrets.yaml
    sed -i "s/REPLACE_WITH_BASE64_SECRET_KEY/$secret_key_b64/g" k8s/secrets.yaml
    sed -i "s/REPLACE_WITH_BASE64_ADMIN_SECRET_KEY/$admin_secret_b64/g" k8s/secrets.yaml
    
    # Add optional API keys if provided
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
        local anthropic_b64=$(echo -n "$ANTHROPIC_API_KEY" | base64)
        sed -i "s/REPLACE_WITH_BASE64_ANTHROPIC_KEY/$anthropic_b64/g" k8s/secrets.yaml
    fi
    
    if [[ -n "${ALPHA_VANTAGE_API_KEY:-}" ]]; then
        local alpha_b64=$(echo -n "$ALPHA_VANTAGE_API_KEY" | base64)
        sed -i "s/REPLACE_WITH_BASE64_ALPHA_VANTAGE_KEY/$alpha_b64/g" k8s/secrets.yaml
    fi
    
    log_success "Kubernetes secrets prepared"
}

deploy_kubernetes_resources() {
    log_info "Deploying Kubernetes resources..."
    
    # Apply resources in order
    local resources=(
        "k8s/namespace.yaml"
        "k8s/secrets.yaml"
        "k8s/configmap.yaml"
        "k8s/database-deployment.yaml"
        "k8s/backend-deployment.yaml"
        "k8s/frontend-deployment.yaml"
        "k8s/ml-service-deployment.yaml"
        "k8s/data-service-deployment.yaml"
        "k8s/ingress.yaml"
    )
    
    for resource in "${resources[@]}"; do
        log_info "Applying $resource..."
        kubectl apply -f $resource
    done
    
    log_success "Kubernetes resources deployed"
}

wait_for_deployment() {
    log_info "Waiting for deployments to be ready..."
    
    # Wait for deployments
    local deployments=("backend-api" "frontend" "ml-service" "data-service" "postgres" "redis")
    for deployment in "${deployments[@]}"; do
        log_info "Waiting for $deployment..."
        kubectl wait --for=condition=available --timeout=600s deployment/$deployment -n trading-platform || {
            if [[ $deployment == "postgres" || $deployment == "redis" ]]; then
                # For StatefulSets, wait for ready condition
                kubectl wait --for=condition=ready --timeout=600s pod -l app=$deployment -n trading-platform
            else
                log_error "Deployment $deployment failed to become ready"
                return 1
            fi
        }
    done
    
    log_success "All deployments are ready"
}

run_health_checks() {
    log_info "Running health checks..."
    
    # Wait a bit for services to fully start
    sleep 30
    
    # Check backend API
    if kubectl run curl-test --image=curlimages/curl:latest --rm -i --restart=Never \
        -- curl -f http://backend-api-service.trading-platform.svc.cluster.local/health; then
        log_success "Backend API health check passed"
    else
        log_error "Backend API health check failed"
        return 1
    fi
    
    # Check frontend
    if kubectl run curl-test --image=curlimages/curl:latest --rm -i --restart=Never \
        -- curl -f http://frontend-service.trading-platform.svc.cluster.local/api/health; then
        log_success "Frontend health check passed"
    else
        log_error "Frontend health check failed"
        return 1
    fi
    
    # Check ML service
    if kubectl run curl-test --image=curlimages/curl:latest --rm -i --restart=Never \
        -- curl -f http://ml-service-service.trading-platform.svc.cluster.local/health; then
        log_success "ML service health check passed"
    else
        log_error "ML service health check failed"
        return 1
    fi
    
    # Check data service
    if kubectl run curl-test --image=curlimages/curl:latest --rm -i --restart=Never \
        -- curl -f http://data-service-service.trading-platform.svc.cluster.local/health; then
        log_success "Data service health check passed"
    else
        log_error "Data service health check failed"
        return 1
    fi
    
    log_success "All health checks passed"
}

setup_monitoring() {
    log_info "Setting up monitoring..."
    
    # Add Prometheus Helm repo
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    # Install Prometheus
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set grafana.adminPassword="$GRAFANA_PASSWORD" \
        --set prometheus.prometheusSpec.retention=30d \
        --wait
    
    log_success "Monitoring setup complete"
}

get_endpoints() {
    log_info "Getting service endpoints..."
    
    # Get load balancer endpoint
    local lb_hostname=$(kubectl get ingress trading-platform-ingress -n trading-platform -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    if [[ -n "$lb_hostname" ]]; then
        log_success "Application endpoints:"
        echo "  Main site: https://$lb_hostname"
        echo "  API: https://api.$lb_hostname"
        echo "  Admin: https://admin.$lb_hostname"
        echo ""
        echo "Default admin credentials:"
        echo "  Username: superadmin"
        echo "  Email: admin@tradingplatform.dev"
        echo "  Password: Admin123!@#ChangeMe"
        echo "  ⚠️  CHANGE PASSWORD IMMEDIATELY AFTER FIRST LOGIN!"
    else
        log_warning "Load balancer endpoint not yet available. Check again in a few minutes."
        echo "Run: kubectl get ingress trading-platform-ingress -n trading-platform"
    fi
}

cleanup_on_failure() {
    log_error "Deployment failed. Cleaning up..."
    
    # Optional: Rollback recent changes
    # kubectl rollout undo deployment/backend-api -n trading-platform
    # kubectl rollout undo deployment/frontend -n trading-platform
    
    log_info "Check logs for debugging:"
    echo "  kubectl logs -l app=backend-api -n trading-platform --tail=50"
    echo "  kubectl logs -l app=frontend -n trading-platform --tail=50"
    echo "  kubectl get events -n trading-platform --sort-by='.lastTimestamp'"
}

main() {
    log_info "Starting deployment for environment: $ENVIRONMENT"
    
    # Trap errors for cleanup
    trap cleanup_on_failure ERR
    
    # Run deployment steps
    check_prerequisites
    
    if [[ "${SKIP_INFRASTRUCTURE:-false}" != "true" ]]; then
        deploy_infrastructure
    fi
    
    if [[ "${SKIP_BUILD:-false}" != "true" ]]; then
        build_and_push_images
    fi
    
    prepare_kubernetes_secrets
    deploy_kubernetes_resources
    wait_for_deployment
    run_health_checks
    
    if [[ "${SETUP_MONITORING:-true}" == "true" ]]; then
        setup_monitoring
    fi
    
    get_endpoints
    
    log_success "🎉 Deployment completed successfully!"
    log_info "🔧 Next steps:"
    echo "  1. Update DNS records to point to the load balancer"
    echo "  2. Configure SSL certificates"
    echo "  3. Set up system API credentials in admin panel"
    echo "  4. Run production smoke tests"
    echo "  5. Set up monitoring alerts"
}

# Show usage if no arguments
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <environment> [options]"
    echo ""
    echo "Environments:"
    echo "  production   - Deploy to production"
    echo "  staging      - Deploy to staging"
    echo ""
    echo "Environment Variables:"
    echo "  SKIP_INFRASTRUCTURE=true   - Skip Terraform deployment"
    echo "  SKIP_BUILD=true           - Skip Docker image building"
    echo "  SETUP_MONITORING=false    - Skip monitoring setup"
    echo ""
    echo "Required Environment Variables:"
    echo "  DATABASE_URL               - PostgreSQL connection string"
    echo "  REDIS_URL                 - Redis connection string"
    echo "  SECRET_KEY                - Application secret key"
    echo "  ADMIN_SECRET_KEY          - Admin panel secret key"
    echo "  GITHUB_TOKEN              - GitHub token for container registry"
    echo "  GRAFANA_PASSWORD          - Grafana admin password"
    echo ""
    echo "Optional API Keys (configured via admin panel later):"
    echo "  ANTHROPIC_API_KEY"
    echo "  ALPHA_VANTAGE_API_KEY"
    echo "  OPENAI_API_KEY"
    echo "  SENDGRID_API_KEY"
    echo "  TWILIO_AUTH_TOKEN"
    exit 1
fi

# Run main function
main "$@"