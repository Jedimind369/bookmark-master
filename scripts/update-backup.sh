#!/bin/bash

# Set the base directory
BASE_DIR="$(pwd)"
BACKUP_DIR="$BASE_DIR/important_files"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Copy important files
echo "Copying important files to backup directory..."

# Server files
cp "$BASE_DIR/server-services-ts/enrichmentService.ts" "$BACKUP_DIR/"
cp "$BASE_DIR/server.js" "$BACKUP_DIR/"
cp "$BASE_DIR/admin-server.js" "$BACKUP_DIR/"
cp "$BASE_DIR/index.ts" "$BACKUP_DIR/"
cp "$BASE_DIR/package.json" "$BACKUP_DIR/"
cp "$BASE_DIR/server-package.json" "$BACKUP_DIR/"
cp "$BASE_DIR/.env.example" "$BACKUP_DIR/"
cp "$BASE_DIR/start-server.sh" "$BACKUP_DIR/"

# Client files
cp "$BASE_DIR/client/src/components/EnrichmentPanel.tsx" "$BACKUP_DIR/"

# Documentation
cp "$BASE_DIR/README.md" "$BACKUP_DIR/"
cp "$BASE_DIR/YOUTUBE_TRANSCRIPT_INFO.md" "$BACKUP_DIR/"
cp "$BASE_DIR/YOUTUBE_TRANSCRIPT_FIX_SUMMARY.md" "$BACKUP_DIR/"
cp "$BASE_DIR/backup/README_BACKUP.md" "$BACKUP_DIR/"

echo "Backup completed successfully!"
echo "Files are available in: $BACKUP_DIR"
echo "To create a zip file for use with other language models, run: cd backup && zip -r important_files.zip important_files/" 