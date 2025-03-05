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

print_message "🔍 Running Bookmark Master Server Diagnostics" "${BLUE}"
echo ""

# Check Node.js version
print_message "Checking Node.js version..." "${YELLOW}"
NODE_VERSION=$(node -v)
print_message "Node.js version: $NODE_VERSION" "${GREEN}"
if [[ "$NODE_VERSION" < "v14" ]]; then
  print_message "⚠️ Node.js version is below the recommended v14. Consider upgrading." "${RED}"
else
  print_message "✅ Node.js version is acceptable." "${GREEN}"
fi
echo ""

# Check npm version
print_message "Checking npm version..." "${YELLOW}"
NPM_VERSION=$(npm -v)
print_message "npm version: $NPM_VERSION" "${GREEN}"
echo ""

# Check if server directory exists
print_message "Checking server directory structure..." "${YELLOW}"
if [ -d "src/server" ]; then
  print_message "✅ Server directory exists." "${GREEN}"
else
  print_message "❌ Server directory not found at src/server!" "${RED}"
fi

# Check if server build exists
if [ -d "src/server/dist" ]; then
  print_message "✅ Server build directory exists." "${GREEN}"
else
  print_message "❌ Server build not found at src/server/dist! Run 'npm run server:build' first." "${RED}"
fi

# Check if main index.js exists
if [ -f "src/server/dist/index.js" ]; then
  print_message "✅ Server entry point exists." "${GREEN}"
else
  print_message "❌ Server entry point not found at src/server/dist/index.js!" "${RED}"
fi
echo ""

# Check for crucial files and dependencies
print_message "Checking crucial files and dependencies..." "${YELLOW}"
FILES_TO_CHECK=(
  "src/server/package.json"
  "src/server/tsconfig.json"
  "src/server/build.js"
  "src/server/src/index.ts"
  "src/server/dist/routes/enrichment.js"
  "src/server/services/zyteService.js"
)

for file in "${FILES_TO_CHECK[@]}"; do
  if [ -f "$file" ]; then
    print_message "✅ $file exists." "${GREEN}"
  else
    print_message "❌ $file not found!" "${RED}"
  fi
done
echo ""

# Check for port conflicts
print_message "Checking for port conflicts..." "${YELLOW}"
PORTS_TO_CHECK=(3000 3001 3002 8080)

for port in "${PORTS_TO_CHECK[@]}"; do
  if lsof -i:$port >/dev/null 2>&1; then
    PROCESS=$(lsof -i:$port | tail -n 1)
    print_message "⚠️ Port $port is currently in use by: $PROCESS" "${RED}"
  else
    print_message "✅ Port $port is available." "${GREEN}"
  fi
done
echo ""

# Check environment variables
print_message "Checking environment variables..." "${YELLOW}"
ENV_VARS=("NODE_ENV" "PORT" "ZYTE_API_KEY" "USE_DIRECT_ZYTE_API")

for var in "${ENV_VARS[@]}"; do
  value=${!var}
  if [ -z "$value" ]; then
    print_message "⚠️ $var is not set." "${YELLOW}"
  else
    print_message "✅ $var is set to: $value" "${GREEN}"
  fi
done
echo ""

# Check if npm dependencies are installed
print_message "Checking if server npm dependencies are installed..." "${YELLOW}"
if [ -d "src/server/node_modules" ]; then
  print_message "✅ Server node_modules exists." "${GREEN}"
else
  print_message "❌ Server node_modules not found! Run 'cd src/server && npm install'." "${RED}"
fi
echo ""

print_message "Diagnostics complete! 🎉" "${BLUE}"
print_message "If you found any issues, try the following steps:" "${YELLOW}"
print_message "1. Run 'cd src/server && npm install' to install dependencies" "${YELLOW}"
print_message "2. Run 'npm run server:build' to rebuild the server" "${YELLOW}"
print_message "3. Run './start-server.sh' to start the server with default settings" "${YELLOW}"
print_message "4. Check server logs in src/server/logs/ for more details" "${YELLOW}" 