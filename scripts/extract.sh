#!/bin/bash

# Create a temporary container from the image
CONTAINER_ID=$(docker create bookmark-master-app)

# Copy the file from the container to the host
docker cp $CONTAINER_ID:/app/src/server/dist/index.js ./extracted-index.js

# Remove the temporary container
docker rm $CONTAINER_ID

echo "File extracted to extracted-index.js" 