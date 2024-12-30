#!/bin/bash

# Sync changes with GitHub and provide Replit deployment instructions

# Get the current branch name
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "🚀 Syncing $BRANCH with GitHub..."

# Push to GitHub
echo "📦 Pushing to GitHub..."
git push origin $BRANCH
GITHUB_STATUS=$?

if [ $GITHUB_STATUS -eq 0 ]; then
    echo "✅ Successfully pushed to GitHub!"
    echo ""
    echo "To deploy to Replit:"
    echo "1. Open Replit Shell in your project"
    echo "2. Run these commands:"
    echo "   git fetch origin"
    echo "   git reset --hard origin/main"
    echo "   npm install"
    echo "   npm run build"
    echo ""
    echo "💡 Tip: If Replit is slow, you can:"
    echo "1. Create a new Replit from GitHub"
    echo "2. Import https://github.com/Jedimind369/bookmark-master.git"
    echo ""
    
    # Ask if user wants to open Replit
    read -p "Would you like to open Replit in your browser? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open "https://replit.com/@jedimind/BookmarkMaster"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            xdg-open "https://replit.com/@jedimind/BookmarkMaster"
        elif [[ "$OSTYPE" == "msys" ]]; then
            start "https://replit.com/@jedimind/BookmarkMaster"
        fi
    fi
else
    echo "❌ Failed to push to GitHub"
fi 