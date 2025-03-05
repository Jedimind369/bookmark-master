#!/bin/bash

# Skript zum Starten der Docker-Umgebung für Bookmark-Master

echo "Starte Docker-Umgebung für Bookmark-Master..."

# In das Docker-Verzeichnis wechseln
cd "$(dirname "$0")/../docker"

# Docker-Compose starten
docker-compose up -d

# Status der Container anzeigen
docker-compose ps

echo "Docker-Umgebung erfolgreich gestartet!"
echo "Die Anwendung ist unter http://localhost:8000 erreichbar."
echo "Grafana ist unter http://localhost:3000 erreichbar."
echo "Prometheus ist unter http://localhost:9090 erreichbar." 