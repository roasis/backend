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

# Function to setup SSL certificates
setup_ssl() {
    local domain=$1

    echo -e "${YELLOW}🔐 Setting up SSL for domain: $domain${NC}"

    # Update nginx.prod.conf with actual domain
    sed -i.bak "s/your-domain.com/$domain/g" nginx.prod.conf

    # Create certbot directories
    mkdir -p ./certbot/conf
    mkdir -p ./certbot/www

    # Download SSL parameters if not exists
    if [ ! -e "./certbot/conf/options-ssl-nginx.conf" ]; then
        echo "📥 Downloading SSL parameters..."
        curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "./certbot/conf/options-ssl-nginx.conf"
        curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "./certbot/conf/ssl-dhparams.pem"
    fi

    # Create dummy certificate for initial nginx start
    echo "🔑 Creating temporary certificate..."
    local path="/etc/letsencrypt/live/$domain"
    mkdir -p "./certbot/conf/live/$domain"
    sudo docker-compose -f docker-compose.prod.yml run --rm --entrypoint "\
      openssl req -x509 -nodes -newkey rsa:4096 -days 1\
        -keyout '$path/privkey.pem' \
        -out '$path/fullchain.pem' \
        -subj '/CN=localhost'" certbot

    # Start nginx
    echo "🌐 Starting nginx..."
    sudo docker-compose -f docker-compose.prod.yml up --force-recreate -d nginx

    # Remove dummy certificate
    echo "🗑️ Removing temporary certificate..."
    sudo docker-compose -f docker-compose.prod.yml run --rm --entrypoint "\
      rm -Rf /etc/letsencrypt/live/$domain && \
      rm -Rf /etc/letsencrypt/archive/$domain && \
      rm -Rf /etc/letsencrypt/renewal/$domain.conf" certbot

    # Get real certificate
    echo "📜 Requesting Let's Encrypt certificate..."
    sudo docker-compose -f docker-compose.prod.yml run --rm --entrypoint "\
      certbot certonly --webroot -w /var/www/certbot \
        -d $domain \
        --email $EMAIL \
        --rsa-key-size 4096 \
        --agree-tos \
        --force-renewal" certbot

    # Reload nginx
    echo "🔄 Reloading nginx..."
    sudo docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
}

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
sudo docker-compose -f docker-compose.prod.yml down || true

# Build new images
echo -e "${YELLOW}🔨 Building new images...${NC}"
sudo docker-compose -f docker-compose.prod.yml build --no-cache

# Production deployment with SSL
# Check if SSL certificates exist
if [ ! -d "./certbot/conf/live/$DOMAIN" ]; then
    setup_ssl "$DOMAIN"
else
    echo -e "${YELLOW}📋 Starting production containers...${NC}"
    sudo docker-compose -f docker-compose.prod.yml up -d
fi

# Health check with HTTPS
echo -e "${YELLOW}🔍 Waiting for services to be healthy...${NC}"
timeout 120 bash -c "until curl -f -k https://localhost/health; do sleep 2; done"

echo -e "${GREEN}✅ Production deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Backend is running at: https://$DOMAIN${NC}"
echo -e "${GREEN}🔒 SSL certificate is active${NC}"

# Check logs
echo -e "${YELLOW}📋 Recent logs:${NC}"
sudo docker-compose -f docker-compose.prod.yml logs --tail=20

# Show useful commands
echo -e "${YELLOW}🔧 Useful commands:${NC}"
echo "  View logs: sudo docker-compose -f docker-compose.prod.yml logs -f"
echo "  Stop: sudo docker-compose -f docker-compose.prod.yml down"
echo "  SSL renewal test: sudo docker-compose -f docker-compose.prod.yml exec certbot certbot renew --dry-run"
