#!/bin/bash

echo "Fixing bcrypt architecture issues..."

# Stop containers
docker-compose --env-file .env.production down

# Remove node_modules in the container
echo "Removing node_modules in the container..."
docker run --rm -v $(pwd)/src/server:/app alpine sh -c "rm -rf /app/node_modules"

# Create a temporary Dockerfile for bcrypt rebuild
cat > Dockerfile.bcrypt << EOF
FROM --platform=linux/amd64 node:20-alpine

WORKDIR /app

COPY src/server/package.json src/server/package-lock.json* ./

RUN apk add --no-cache python3 make g++
RUN npm install bcrypt --build-from-source

CMD ["sh", "-c", "echo 'Bcrypt rebuilt successfully'"]
EOF

# Build the bcrypt image
echo "Building bcrypt with correct architecture..."
docker build -f Dockerfile.bcrypt -t bcrypt-rebuild .

# Clean up
rm Dockerfile.bcrypt

echo "Bcrypt has been rebuilt. Now run ./rebuild-docker.sh to rebuild the application." 