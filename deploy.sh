#!/bin/bash

# ============================================================================
# RheXa Backend - Production Deployment Script
# Safely handles database migrations and service startup
# ============================================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

print_header "RheXa Backend - Deployment Script"

print_info "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi
print_success "Docker found: $(docker --version)"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi
print_success "Docker Compose found: $(docker-compose --version)"

# Check .env file
if [ ! -f ".env.production" ]; then
    print_error ".env.production file not found"
    print_info "Creating .env.production from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env.production
        print_warning "Please update .env.production with production values"
        exit 1
    else
        print_error ".env.example file not found"
        exit 1
    fi
fi
print_success ".env.production file found"

# ============================================================================
# Environment Setup
# ============================================================================

print_header "Environment Setup"

# Load environment variables
export $(grep -v '^#' .env.production | xargs)

# Verify critical variables
REQUIRED_VARS=("SECRET_KEY" "DATABASE_URL" "OPENAI_API_KEY")

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required variable $var not set in .env.production"
        exit 1
    fi
done
print_success "All required environment variables are set"

# ============================================================================
# Docker Build & Pull
# ============================================================================

print_header "Building Docker Images"

docker-compose build --no-cache backend
print_success "Backend image built successfully"

# ============================================================================
# Start Services
# ============================================================================

print_header "Starting Services"

print_info "Starting MySQL database..."
docker-compose up -d db
sleep 10  # Wait for database to be ready
print_success "MySQL database started"

print_info "Starting Redis cache..."
docker-compose up -d redis
sleep 5
print_success "Redis started"

# ============================================================================
# Database Migrations
# ============================================================================

print_header "Database Migrations"

print_info "Running Alembic migrations..."
docker-compose exec -T backend alembic upgrade head

if [ $? -eq 0 ]; then
    print_success "Database migrations completed successfully"
else
    print_error "Database migrations failed"
    exit 1
fi

# ============================================================================
# Start Backend Service
# ============================================================================

print_header "Starting Backend Service"

print_info "Starting RheXa Backend API..."
docker-compose up -d backend

# Wait for backend to be healthy
print_info "Waiting for backend to be healthy..."
for i in {1..30}; do
    if docker-compose exec -T backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend is healthy and running"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Backend failed to become healthy"
        exit 1
    fi
    sleep 2
done

# ============================================================================
# Start Additional Services (Optional)
# ============================================================================

if [ "${ENABLE_NGINX:-false}" = "true" ]; then
    print_info "Starting Nginx reverse proxy..."
    docker-compose up -d nginx
    print_success "Nginx started"
fi

# ============================================================================
# Post-Deployment Verification
# ============================================================================

print_header "Post-Deployment Verification"

# Check all services are running
print_info "Checking service status..."
docker-compose ps

# Test API endpoints
print_info "Testing API endpoints..."
API_URL="http://localhost:8000"

# Test health check
if curl -s "$API_URL/health" | grep -q "ok"; then
    print_success "Health check endpoint working"
else
    print_warning "Health check endpoint not responding as expected"
fi

# Test Swagger documentation
if curl -s "$API_URL/docs" | grep -q "swagger"; then
    print_success "Swagger documentation accessible"
else
    print_warning "Swagger documentation not accessible"
fi

# ============================================================================
# Summary & Next Steps
# ============================================================================

print_header "Deployment Complete!"

echo ""
print_success "RheXa Backend is now running in production"
echo ""
echo "Service URLs:"
echo "  - API:                http://localhost:8000"
echo "  - Swagger Docs:       http://localhost:8000/docs"
echo "  - ReDoc:              http://localhost:8000/redoc"
echo "  - Health Check:       http://localhost:8000/health"
echo ""
echo "Database:"
echo "  - Host:               db (localhost)"
echo "  - Port:               3306"
echo "  - Database:           ${DATABASE_NAME:-rhexa_db}"
echo ""
echo "Useful Commands:"
echo "  - View logs:          docker-compose logs -f backend"
echo "  - Restart services:   docker-compose restart"
echo "  - Stop services:      docker-compose down"
echo "  - Enter backend:      docker-compose exec backend bash"
echo "  - Database shell:     docker-compose exec db mysql -u root -p"
echo ""
echo "Next Steps:"
echo "  1. Review logs: docker-compose logs -f backend"
echo "  2. Test endpoints: curl http://localhost:8000/health"
echo "  3. Configure monitoring (Prometheus, Grafana, etc.)"
echo "  4. Set up backups for database volumes"
echo "  5. Configure SSL/TLS certificates"
echo ""

# ============================================================================
# Error Handling
# ============================================================================

trap 'print_error "Deployment failed"; exit 1' ERR

# ============================================================================
# End of Script
# ============================================================================

print_success "Deployment script completed successfully"
exit 0
