#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
  echo -e "${2}$1${NC}"
}

# Function to check if a process is running on a specific port
check_port() {
  lsof -i:$1 >/dev/null 2>&1
  return $?
}

# Function to kill processes on a specific port
kill_port() {
  print_message "Killing process on port $1..." "${YELLOW}"
  lsof -ti:$1 | xargs kill -9 2>/dev/null
}

# Error handler function
handle_error() {
  print_message "ERROR: $1" "${RED}"
  print_message "Cleaning up processes..." "${YELLOW}"
  kill_port 8080
  kill_port 3000
  exit 1
}

# Set working directory to the project root
cd "$(dirname "$0")"
WORKSPACE=$(pwd)

print_message "====== Bookmark App Launcher ======" "${GREEN}"
print_message "Starting from workspace: $WORKSPACE" "${GREEN}"
print_message "Debug: Current directory: $(pwd)" "${BLUE}"

# Kill any existing processes on ports we'll use
print_message "Cleaning up any existing processes..." "${YELLOW}"
kill_port 8080
kill_port 3000

# Start the server
print_message "Setting up server..." "${GREEN}"
cd "$WORKSPACE/src/server"
print_message "Debug: Server directory: $(pwd)" "${BLUE}"

# First, run npm install if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
  print_message "Installing server dependencies..." "${YELLOW}"
  npm install || handle_error "Failed to install server dependencies!"
fi

# Make sure dist directory exists
mkdir -p dist/services
mkdir -p dist/controllers
mkdir -p dist/routes
mkdir -p dist/utils
mkdir -p dist/middleware

# Manually fix the problematic build - copy and transpile our key files
print_message "Manually updating Zyte service files..." "${YELLOW}"

# Copy zyteService.ts and nodeZyteClient.ts to dist/services
cp services/zyteService.ts dist/services/ || handle_error "Failed to copy zyteService.ts"
cp services/nodeZyteClient.ts dist/services/ || handle_error "Failed to copy nodeZyteClient.ts"

# Transpile with Babel
npx babel dist/services/zyteService.ts --out-file dist/services/zyteService.js --extensions '.ts' || handle_error "Failed to transpile zyteService.ts"
npx babel dist/services/nodeZyteClient.ts --out-file dist/services/nodeZyteClient.js --extensions '.ts' || handle_error "Failed to transpile nodeZyteClient.ts"

# Create fixed express-async-handler enrichment route
print_message "Creating fixed enrichment route..." "${YELLOW}"

# Write the fixed enrichment.js file directly
cat > dist/routes/enrichment.js << 'EOF'
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const express = require("express");
const asyncHandler = require("express-async-handler");
const zyteService_1 = require("../../services/zyteService");

const router = express.Router();

// Explizit die Umgebungsvariable für Debug-Zwecke ausgeben
console.log(`enrichment.js: USE_DIRECT_ZYTE_API=${process.env.USE_DIRECT_ZYTE_API}`);

// Initialisiere ZyteService mit expliziter Konfiguration für direkte API
const zyteService = new zyteService_1.ZyteService({
    useDirectApi: process.env.USE_DIRECT_ZYTE_API === 'true'
});

/**
 * @route   POST /api/enrichment/extract-url
 * @desc    Extrahiert Informationen von einer URL mit Zyte
 * @access  Public (for testing)
 */
router.post('/extract-url', asyncHandler(async (req, res) => {
    try {
        const { url, useBrowser } = req.body;
        
        if (!url) {
            res.status(400).json({
                success: false,
                message: 'URL is required'
            });
            return;
        }
        
        console.log(`Extracting URL: ${url}, useBrowser: ${useBrowser}, USE_DIRECT_ZYTE_API: ${process.env.USE_DIRECT_ZYTE_API}`);
        
        const result = await zyteService.extractUrl(url, useBrowser);
        
        res.status(200).json({
            success: true,
            data: result
        });
    } catch (error) {
        console.error('Error in extract-url route:', error);
        res.status(500).json({
            success: false,
            message: 'Error extracting URL',
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
}));

exports.default = router;
EOF

# Copy and transpile index.ts
print_message "Copying and transpiling index.ts..." "${YELLOW}"
cp src/index.ts dist/ || handle_error "Failed to copy index.ts"
npx babel dist/index.ts --out-file dist/index.js --extensions '.ts' || handle_error "Failed to transpile index.ts"

# Print environment variables for debugging
print_message "Setting environment variables for direct Zyte API..." "${BLUE}"
print_message "USE_DIRECT_ZYTE_API=true" "${BLUE}"
print_message "NODE_ENV=development" "${BLUE}"
print_message "PORT=8080" "${BLUE}"
print_message "ZYTE_API_KEY is being set" "${BLUE}"

# Run server in background
print_message "Starting server on port 8080 with direct Zyte API..." "${GREEN}"
USE_DIRECT_ZYTE_API=true PORT=8080 NODE_ENV=development ZYTE_API_KEY=3cdbcbeedcb44cc090ee4ccc58a831d7 node dist/index.js > server.log 2>&1 &
SERVER_PID=$!

print_message "Server started with PID: $SERVER_PID" "${BLUE}"

# Wait for server to start
print_message "Waiting for server to start..." "${YELLOW}"
max_attempts=30
attempt=0
while ! check_port 8080; do
  attempt=$((attempt+1))
  if [ $attempt -ge $max_attempts ]; then
    print_message "Server failed to start!" "${RED}"
    print_message "Check server.log for details:" "${RED}"
    tail -n 50 server.log
    kill $SERVER_PID 2>/dev/null
    exit 1
  fi
  sleep 1
  echo -n "."
done
echo ""
print_message "Server is running on port 8080!" "${GREEN}"

# Test the server API
print_message "Testing server API with a simple request..." "${YELLOW}"
curl -s -X POST -H "Content-Type: application/json" -d '{"url":"https://example.com", "useBrowser":false}' http://localhost:8080/api/enrichment/extract-url > /dev/null && print_message "API test successful!" "${GREEN}" || handle_error "API test failed!"

# Start the client
print_message "Setting up client..." "${GREEN}"
cd "$WORKSPACE/src/client"
print_message "Debug: Client directory: $(pwd)" "${BLUE}"

# First, run npm install if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
  print_message "Installing client dependencies..." "${YELLOW}"
  npm install || handle_error "Failed to install client dependencies!"
fi

# Add a .env.local file for the client to set the API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8080" > .env.local
print_message "Created .env.local with API URL configuration" "${GREEN}"

# Start client in background
print_message "Starting client..." "${GREEN}"
npm run dev > client.log 2>&1 &
CLIENT_PID=$!

print_message "Client started with PID: $CLIENT_PID" "${BLUE}"

# Wait for client to start
print_message "Waiting for client to start..." "${YELLOW}"
max_attempts=30
attempt=0
while ! check_port 3000; do
  attempt=$((attempt+1))
  if [ $attempt -ge $max_attempts ]; then
    print_message "Client failed to start!" "${RED}"
    print_message "Check client.log for details:" "${RED}"
    tail -n 50 client.log
    kill $SERVER_PID 2>/dev/null
    kill $CLIENT_PID 2>/dev/null
    exit 1
  fi
  sleep 1
  echo -n "."
done
echo ""
print_message "Client is running on port 3000!" "${GREEN}"

# Open extraction page in browser
print_message "Opening extraction page in your browser..." "${GREEN}"
if [[ "$OSTYPE" == "darwin"* ]]; then
  open http://localhost:3000/extraction
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  xdg-open http://localhost:3000/extraction
elif [[ "$OSTYPE" == "cygwin" || "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  start http://localhost:3000/extraction
else
  print_message "Please open http://localhost:3000/extraction in your browser" "${YELLOW}"
fi

print_message "====== App is running! ======" "${GREEN}"
print_message "Server: http://localhost:8080" "${GREEN}"
print_message "Client: http://localhost:3000/extraction" "${GREEN}"
print_message "Press CTRL+C to stop the app" "${YELLOW}"
print_message "View logs at:" "${BLUE}"
print_message "Server logs: $WORKSPACE/src/server/server.log" "${BLUE}"
print_message "Client logs: $WORKSPACE/src/client/client.log" "${BLUE}"

# Wait for user to press Ctrl+C
trap "print_message 'Stopping app...' '${YELLOW}'; kill $SERVER_PID 2>/dev/null; kill $CLIENT_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait 