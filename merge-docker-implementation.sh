#!/bin/bash

# Skript zum Mergen der Docker-Implementierung in den main Branch

echo "Merging Docker implementation into main branch..."

# Sicherstellen, dass wir auf dem main Branch sind
git checkout main

# Dateien aus dem docker-implementation Branch holen
git checkout docker-implementation -- Dockerfile
git checkout docker-implementation -- docker-compose.yml
git checkout docker-implementation -- index-convert.cjs
git checkout docker-implementation -- .dockerignore
git checkout docker-implementation -- backup-to-github.sh

# Änderungen committen
git add Dockerfile docker-compose.yml index-convert.cjs .dockerignore backup-to-github.sh
git commit -m "Merge Docker implementation from docker-implementation branch"

# Änderungen pushen
git push origin main

echo "Docker implementation successfully merged into main branch!" 