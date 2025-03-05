#!/bin/bash

# Check logs for the app container
echo "App container logs:"
docker-compose --env-file .env.production logs app

# Follow logs in real-time
echo "Following logs in real-time (press Ctrl+C to exit):"
docker-compose --env-file .env.production logs -f app 