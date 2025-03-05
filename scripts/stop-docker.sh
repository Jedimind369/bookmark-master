#!/bin/bash

# stop-docker.sh
# Script to gracefully stop all Docker containers for the Bookmark Master project

echo "Stopping Docker containers..."

# Change to the directory containing docker-compose.yml
cd "$(dirname "$0")/../docker" || {
    echo "Error: Could not change to docker directory!"
    exit 1
}

# Stop and remove containers, networks, images, and volumes
docker-compose down

echo "Docker containers have been stopped." 