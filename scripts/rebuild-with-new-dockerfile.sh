#!/bin/bash

# Stop and remove all containers
echo "Stopping and removing all containers..."
docker-compose --env-file .env.production down

# Clean up Docker resources
echo "Cleaning up Docker resources..."
docker system prune -f

# Clean Docker build cache
echo "Cleaning Docker build cache..."
docker builder prune -f

# Remove any dangling images
echo "Removing dangling images..."
docker image prune -f

# Build using the new Dockerfile
echo "Building with the new Dockerfile..."
docker build -f Dockerfile.new -t bookmark-master-app .

# Update docker-compose.yml to use the pre-built image
echo "Updating docker-compose.yml to use the pre-built image..."
sed -i.bak 's/build:/image: bookmark-master-app\n    #build:/' docker-compose.yml
sed -i.bak '/context:/d' docker-compose.yml
sed -i.bak '/dockerfile:/d' docker-compose.yml
sed -i.bak '/platforms:/d' docker-compose.yml
sed -i.bak '/- linux\/amd64/d' docker-compose.yml

# Start the containers
echo "Starting the containers..."
docker-compose --env-file .env.production up -d

# Check the status
echo "Container status:"
docker-compose --env-file .env.production ps

# Check logs for the app container
echo "App container logs:"
docker-compose --env-file .env.production logs app 