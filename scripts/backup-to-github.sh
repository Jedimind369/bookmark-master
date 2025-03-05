#!/bin/bash

# Backup script for bookmark-master project

echo "Starting backup process for bookmark-master..."

# Create a new branch for the backup
git checkout -b backup-docker

# Add all files to git
git add .

# Commit changes
git commit -m "Backup of bookmark-master with Docker implementation and fixed routing"

# Push to remote repository
git push -u origin backup-docker

echo "Backup completed successfully!" 