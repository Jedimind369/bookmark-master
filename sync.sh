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
    
    # Deploy to Replit using CLI
    echo "🔄 Deploying to Replit..."
    
    # Check if replit-cli is installed
    if ! command -v replit &> /dev/null; then
        echo "Installing Replit CLI..."
        npm install -g replit-cli
    fi
    
    # Deploy using Replit CLI
    echo "Deploying to Replit..."
    npx replit-cli deploy
    REPLIT_STATUS=$?
    
    if [ $REPLIT_STATUS -eq 0 ]; then
        echo "✅ Successfully deployed to Replit!"
    else
        echo "❌ Failed to deploy to Replit. Please check your Replit connection."
        echo "Alternative deployment methods:"
        echo "1. Use 'git pull' directly in Replit's shell"
        echo "2. Fork the repository in Replit"
        echo "3. Import from GitHub in Replit"
    fi
else
    echo "❌ Failed to push to GitHub"
fi 