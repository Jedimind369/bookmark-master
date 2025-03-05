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

# Rebuild the app container with no-cache option
echo "Rebuilding the app container with no-cache option..."
docker-compose --env-file .env.production build --no-cache app

# Start the containers
echo "Starting the containers..."
docker-compose --env-file .env.production up -d

# Check the status
echo "Container status:"
docker-compose --env-file .env.production ps

# Check logs for the app container
echo "App container logs:"
docker-compose --env-file .env.production logs app 