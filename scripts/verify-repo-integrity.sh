#!/bin/bash

# Skript zur Überprüfung der Repository-Integrität
# Dieses Skript führt verschiedene Prüfungen durch, um sicherzustellen,
# dass das Repository intakt ist und alle wichtigen Dateien vorhanden sind.

echo "Starte Repository-Integritätsprüfung..."

# Wechsle zum Repository-Root-Verzeichnis
cd "$(git rev-parse --show-toplevel)" || exit 1

# Führe git fsck aus, um die Integrität der Git-Objekte zu prüfen
echo "Prüfe Git-Objekte mit git fsck..."
if ! git fsck; then
  echo "FEHLER: Git-Objekte sind beschädigt!"
  exit 1
fi
echo "Git-Objekte sind intakt."

# Prüfe, ob wichtige Dateien vorhanden sind
echo "Prüfe, ob wichtige Dateien vorhanden sind..."
WICHTIGE_DATEIEN=(
  "README.md"
  "docker/Dockerfile"
  "docker/docker-compose.yml"
  "scripts/start-docker.sh"
  "scripts/stop-docker.sh"
  "scripts/backup-to-github.sh"
)

FEHLER=0
for DATEI in "${WICHTIGE_DATEIEN[@]}"; do
  if [ ! -f "$DATEI" ]; then
    echo "FEHLER: Wichtige Datei fehlt: $DATEI"
    FEHLER=1
  fi
done

if [ $FEHLER -eq 0 ]; then
  echo "Alle wichtigen Dateien sind vorhanden."
else
  echo "Es fehlen wichtige Dateien!"
  exit 1
fi

# Prüfe, ob es ungespeicherte Änderungen gibt
echo "Prüfe auf ungespeicherte Änderungen..."
if ! git diff-index --quiet HEAD --; then
  echo "WARNUNG: Es gibt ungespeicherte Änderungen im Repository."
  git status --short
else
  echo "Keine ungespeicherten Änderungen."
fi

# Prüfe, ob lokale Änderungen gepusht wurden
echo "Prüfe, ob lokale Änderungen gepusht wurden..."
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})
BASE=$(git merge-base @ @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "Repository ist synchronisiert mit dem Remote-Repository."
elif [ "$LOCAL" = "$BASE" ]; then
  echo "WARNUNG: Es gibt Änderungen im Remote-Repository, die noch nicht lokal sind."
elif [ "$REMOTE" = "$BASE" ]; then
  echo "WARNUNG: Es gibt lokale Änderungen, die noch nicht gepusht wurden."
else
  echo "WARNUNG: Die lokale und die Remote-Version sind divergiert."
fi

# Prüfe auf doppelte Dateien
echo "Prüfe auf doppelte Dateien..."
if [ -d "./bookmark-master" ]; then
  echo "WARNUNG: Es gibt ein Unterverzeichnis 'bookmark-master', das möglicherweise Duplikate enthält."
  echo "Empfehlung: Führe 'git rm -r bookmark-master' aus, um das Unterverzeichnis zu entfernen."
fi

echo "Repository-Integritätsprüfung abgeschlossen." 