#!/bin/bash

# Sync changes with GitHub and deploy to Replit

# Get the current branch name
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "🚀 Syncing $BRANCH with GitHub..."

# Push to GitHub
echo "📦 Pushing to GitHub..."
git push origin $BRANCH
GITHUB_STATUS=$?

if [ $GITHUB_STATUS -eq 0 ]; then
    echo "✅ Successfully pushed to GitHub!"
    
    # Deploy to Replit
    echo "🔄 Deploying to Replit..."
    echo "Please manually sync your Replit project:"
    echo "1. Go to https://replit.com/@jedimind/BookmarkMaster"
    echo "2. Click on the 'Version Control' tab"
    echo "3. Click 'Pull' to get the latest changes"
    
    # Open Replit in browser
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "https://replit.com/@jedimind/BookmarkMaster"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "https://replit.com/@jedimind/BookmarkMaster"
    elif [[ "$OSTYPE" == "msys" ]]; then
        start "https://replit.com/@jedimind/BookmarkMaster"
    fi
else
    echo "❌ Failed to push to GitHub"
fi 