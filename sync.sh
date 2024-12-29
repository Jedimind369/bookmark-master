#!/bin/bash

# Sync changes with both GitHub and Replit

# Get the current branch name
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "🚀 Syncing $BRANCH with GitHub and Replit..."

# Push to GitHub
echo "📦 Pushing to GitHub..."
git push origin $BRANCH
GITHUB_STATUS=$?

# Push to Replit
echo "🔄 Pushing to Replit..."
git push replit $BRANCH
REPLIT_STATUS=$?

# Check if both pushes were successful
if [ $GITHUB_STATUS -eq 0 ] && [ $REPLIT_STATUS -eq 0 ]; then
    echo "✅ Successfully synced with both repositories!"
else
    echo "❌ There were some issues:"
    [ $GITHUB_STATUS -ne 0 ] && echo "   - Failed to push to GitHub"
    [ $REPLIT_STATUS -ne 0 ] && echo "   - Failed to push to Replit"
fi 