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

# Default environment
DEFAULT_PORT=8080
DEFAULT_ENV="development"
DEFAULT_ZYTE_API_KEY="3cdbcbeedcb44cc090ee4ccc58a831d7"
DEFAULT_USE_DIRECT_ZYTE_API="true"

# Parse command line arguments
ENVIRONMENT=$DEFAULT_ENV
PORT=$DEFAULT_PORT
USE_DIRECT_ZYTE_API=$DEFAULT_USE_DIRECT_ZYTE_API
ZYTE_API_KEY=$DEFAULT_ZYTE_API_KEY

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --env|-e)
      ENVIRONMENT="$2"
      shift
      shift
      ;;
    --port|-p)
      PORT="$2"
      shift
      shift
      ;;
    --direct|-d)
      USE_DIRECT_ZYTE_API="$2"
      shift
      shift
      ;;
    --api-key|-k)
      ZYTE_API_KEY="$2"
      shift
      shift
      ;;
    --help|-h)
      print_message "Usage: ./start-server.sh [options]" "${BLUE}"
      print_message "Options:" "${BLUE}"
      print_message "  --env, -e       Set environment (development, production, test) [default: development]" "${BLUE}"
      print_message "  --port, -p      Set server port [default: 8080]" "${BLUE}"
      print_message "  --direct, -d    Use direct Zyte API (true/false) [default: true]" "${BLUE}"
      print_message "  --api-key, -k   Set Zyte API key" "${BLUE}"
      print_message "  --help, -h      Show this help message" "${BLUE}"
      exit 0
      ;;
    *)
      print_message "Unknown option: $key" "${RED}"
      print_message "Use --help for usage information" "${YELLOW}"
      exit 1
      ;;
  esac
done

# Main execution
print_message "🚀 Starting the Bookmark Master server with:" "${GREEN}"
print_message "   - Environment: ${ENVIRONMENT}" "${BLUE}"
print_message "   - Port: ${PORT}" "${BLUE}"
print_message "   - Direct Zyte API: ${USE_DIRECT_ZYTE_API}" "${BLUE}"

# Check if port is already in use
if check_port $PORT; then
  print_message "⚠️  Port $PORT is already in use. Attempting to kill the process..." "${YELLOW}"
  lsof -ti:$PORT | xargs kill -9 2>/dev/null
  sleep 2
  
  if check_port $PORT; then
    print_message "❌ Failed to free port $PORT. Please choose a different port or free it manually." "${RED}"
    exit 1
  else
    print_message "✅ Port $PORT has been freed successfully." "${GREEN}"
  fi
fi

# Check if we need to build the server first
if [ ! -d "src/server/dist" ] || [ ! -f "src/server/dist/index.js" ]; then
  print_message "🔨 Server build not found. Building server first..." "${YELLOW}"
  cd src/server && npm run build
  BUILD_RESULT=$?
  
  if [ $BUILD_RESULT -ne 0 ]; then
    print_message "❌ Server build failed. Please check the errors above." "${RED}"
    exit 1
  fi
  
  print_message "✅ Server built successfully!" "${GREEN}"
  cd ../..
fi

# Set environment variables and start the server
print_message "🚀 Starting server..." "${GREEN}"

# Export environment variables
export PORT=$PORT
export NODE_ENV=$ENVIRONMENT
export ZYTE_API_KEY=$ZYTE_API_KEY
export USE_DIRECT_ZYTE_API=$USE_DIRECT_ZYTE_API

# Start the server
cd src/server && node --max-old-space-size=2048 --expose-gc dist/index.js

# Check if server started successfully
SERVER_EXIT_CODE=$?
if [ $SERVER_EXIT_CODE -ne 0 ]; then
  print_message "❌ Server failed to start with exit code $SERVER_EXIT_CODE" "${RED}"
  exit $SERVER_EXIT_CODE
fi 