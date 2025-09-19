#!/bin/bash

# EC2 deployment script
set -e

# Stop and remove existing containers
echo "🛑 Stopping existing containers..."
sudo docker-compose down || true

# Build new images
echo "🔨 Building new images..."
sudo docker-compose build --no-cache

# Start containers
echo "▶️ Starting containers..."
sudo docker-compose up -d

# Wait for health check
echo "🔍 Waiting for services to be healthy..."
timeout 120 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'

echo "✅ Deployment completed successfully!"
echo "🌐 Backend is running at: http://localhost:8000"
echo "🔒 HTTPS is available at: https://localhost"

# Check logs
echo "📋 Recent logs:"
sudo docker-compose logs --tail=20