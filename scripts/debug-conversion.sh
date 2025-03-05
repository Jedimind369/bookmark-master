#!/bin/bash

# Create a temporary container from the image
echo "Creating temporary container..."
CONTAINER_ID=$(docker create bookmark-master-app)

# Copy the TypeScript file and the conversion script
echo "Copying files from container..."
docker cp $CONTAINER_ID:/app/src/server/index.ts ./original-index.ts
docker cp $CONTAINER_ID:/app/convert.sh ./container-convert.sh

# Make the conversion script executable
chmod +x ./container-convert.sh

# Create a test directory structure
echo "Setting up test environment..."
mkdir -p test/src/server
cp original-index.ts test/src/server/index.ts

# Run the conversion script in a controlled environment
echo "Running conversion script on the original TypeScript file..."
cd test
mkdir -p src/server/dist
cat ../container-convert.sh | sed 's|/app/|./|g' > ./convert-local.sh
chmod +x ./convert-local.sh
./convert-local.sh

# Check the output
echo "Checking conversion output..."
cat ./src/server/dist/index.js > ../converted-index.js

# Clean up
echo "Cleaning up..."
cd ..
rm -rf test
docker rm $CONTAINER_ID

echo "Original TypeScript file saved to original-index.ts"
echo "Converted JavaScript file saved to converted-index.js"
echo "Conversion script saved to container-convert.sh"

# Try to run the converted file with Node.js
echo "Attempting to run the converted JavaScript file..."
node -c converted-index.js 2> conversion-errors.txt
if [ $? -eq 0 ]; then
  echo "No syntax errors found in the converted JavaScript file."
else
  echo "Syntax errors found in the converted JavaScript file. See conversion-errors.txt for details."
fi 