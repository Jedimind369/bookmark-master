#!/bin/bash

# Backup-Skript für das Bookmark-Master-Projekt

echo "Starte Backup-Prozess für Bookmark-Master..."

# Aktuelles Datum für den Branch-Namen
DATUM=$(date +"%Y-%m-%d")
BRANCH_NAME="backup-$DATUM"

# Sicherstellen, dass wir auf dem main Branch sind
git checkout main

# Neuen Branch für das Backup erstellen
git checkout -b $BRANCH_NAME

# Alle Dateien zu Git hinzufügen
git add .

# Änderungen committen
git commit -m "Backup von Bookmark-Master vom $DATUM"

# Zum Remote-Repository pushen
git push -u origin $BRANCH_NAME

echo "Backup erfolgreich abgeschlossen!"
echo "Branch: $BRANCH_NAME wurde erstellt und zu GitHub gepusht." 