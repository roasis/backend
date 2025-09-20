#!/bin/bash

# Production deployment script with SSL support
set -e

# Fixed configuration for AWS EC2 production
DOMAIN="ec2-16-176-168-206.ap-southeast-2.compute.amazonaws.com"
ENVIRONMENT="prod"
EMAIL="admin@roasis.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Roasis Backend Deployment${NC}"
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Domain: $DOMAIN${NC}"

# Function to setup SSL certificates (self-signed for AWS EC2)
setup_ssl() {
    local domain=$1

    echo -e "${YELLOW}🔐 Setting up self-signed SSL certificate for: $domain${NC}"
    echo -e "${YELLOW}ℹ️  AWS EC2 domains cannot use Let's Encrypt certificates${NC}"

    # Create SSL directory
    mkdir -p ./ssl

    # Generate self-signed certificate
    echo "🔑 Generating self-signed SSL certificate..."
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ./ssl/server.key \
        -out ./ssl/server.crt \
        -subj "/C=US/ST=CA/L=San Francisco/O=Roasis/OU=IT/CN=$domain"

    echo "✅ Self-signed SSL certificate created"
}

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
sudo docker-compose -f docker-compose.prod.yml down || true

# Build new images
echo -e "${YELLOW}🔨 Building new images...${NC}"
sudo docker-compose -f docker-compose.prod.yml build --no-cache

# Production deployment with SSL
# Check if SSL certificates exist
if [ ! -f "./ssl/server.crt" ] || [ ! -f "./ssl/server.key" ]; then
    setup_ssl "$DOMAIN"
fi

echo -e "${YELLOW}📋 Starting production containers...${NC}"
sudo docker-compose -f docker-compose.prod.yml up -d

# Health check with HTTPS
echo -e "${YELLOW}🔍 Waiting for services to be healthy...${NC}"
timeout 120 bash -c "until curl -f -k https://localhost/health; do sleep 2; done"

echo -e "${GREEN}✅ Production deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Backend is running at: https://$DOMAIN${NC}"
echo -e "${GREEN}🔒 Self-signed SSL certificate is active${NC}"
echo -e "${YELLOW}⚠️  You may need to accept the security warning in your browser${NC}"

# Check logs
echo -e "${YELLOW}📋 Recent logs:${NC}"
sudo docker-compose -f docker-compose.prod.yml logs --tail=20

# Show useful commands
echo -e "${YELLOW}🔧 Useful commands:${NC}"
echo "  View logs: sudo docker-compose -f docker-compose.prod.yml logs -f"
echo "  Stop: sudo docker-compose -f docker-compose.prod.yml down"
echo "  Regenerate SSL cert: sudo rm -rf ./ssl && ./deploy.sh"
