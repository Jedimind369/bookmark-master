#!/bin/bash

# Pfad zur Datenbank
DB_PATH="$(pwd)/data/data.sqlite"

# Farben für die Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Erstelle Indexe für die Datenbank...${NC}"

# Führe das SQL-Skript aus
sqlite3 "$DB_PATH" < create-indexes.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Indexe wurden erfolgreich erstellt!${NC}"
else
    echo -e "${RED}Fehler beim Erstellen der Indexe!${NC}"
    exit 1
fi 