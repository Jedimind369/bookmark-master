#!/bin/bash

# Stop all containers
echo "Stopping all containers..."
docker-compose --env-file .env.production down

# Restore the original docker-compose.yml
echo "Restoring original docker-compose.yml..."
if [ -f docker-compose.yml.backup ]; then
  cp docker-compose.yml.backup docker-compose.yml
  echo "Original docker-compose.yml restored."
else
  echo "Backup file not found. Cannot restore original docker-compose.yml."
  exit 1
fi

# Clean up Docker resources
echo "Cleaning up Docker resources..."
docker system prune -f
docker builder prune -f
docker image prune -f

# Rebuild and start with original configuration
echo "Rebuilding with original configuration..."
docker-compose --env-file .env.production build --no-cache
docker-compose --env-file .env.production up -d

# Check the status
echo "Container status:"
docker-compose --env-file .env.production ps

# Check logs for the app container
echo "App container logs:"
docker-compose --env-file .env.production logs app 