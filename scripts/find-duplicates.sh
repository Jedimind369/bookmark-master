#!/bin/bash

# Pfad zur Datenbank
DB_PATH="$(pwd)/data/data.sqlite"

# Farben für die Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Suche nach Duplikaten in der Datenbank...${NC}"

# Führe das SQL-Skript aus
RESULT=$(sqlite3 "$DB_PATH" < find-duplicates.sql)

if [ -z "$RESULT" ]; then
    echo -e "${GREEN}Keine Duplikate gefunden!${NC}"
else
    echo -e "${RED}Folgende Duplikate wurden gefunden:${NC}"
    echo -e "URL | Anzahl"
    echo -e "---------------"
    echo -e "$RESULT"
    
    echo ""
    echo -e "${BLUE}Möchten Sie die Duplikate entfernen? (j/n)${NC}"
    read -n 1 REMOVE_DUPLICATES
    
    if [[ $REMOVE_DUPLICATES == "j" || $REMOVE_DUPLICATES == "J" ]]; then
        echo ""
        echo -e "${BLUE}Entferne Duplikate...${NC}"
        
        sqlite3 "$DB_PATH" <<EOF
-- Temporäre Tabelle mit eindeutigen IDs und URLs
CREATE TEMPORARY TABLE unique_bookmarks AS
SELECT MIN(id) as id, url
FROM bookmarks
GROUP BY url;

-- Lösche alle Duplikate
DELETE FROM bookmarks
WHERE id NOT IN (SELECT id FROM unique_bookmarks);
EOF
        
        echo -e "${GREEN}Duplikate wurden erfolgreich entfernt!${NC}"
    fi
fi 