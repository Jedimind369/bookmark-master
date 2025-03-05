#!/bin/bash

# Farben für die Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Funktion zum Anzeigen des Menüs
show_menu() {
    clear
    echo -e "${BLUE}=== Bookmark-Master Datenbank-Tools ===${NC}"
    echo -e "${YELLOW}1.${NC} DB Browser für SQLite öffnen"
    echo -e "${YELLOW}2.${NC} Indexe erstellen"
    echo -e "${YELLOW}3.${NC} Backup erstellen"
    echo -e "${YELLOW}4.${NC} Duplikate finden und entfernen"
    echo -e "${YELLOW}5.${NC} Alle Lesezeichen anzeigen"
    echo -e "${YELLOW}6.${NC} Beenden"
    echo ""
    echo -e "${BLUE}Wähle eine Option (1-6):${NC}"
}

# Funktion zum Öffnen von DB Browser
open_db_browser() {
    DB_BROWSER_APP="/Applications/DB Browser for SQLite.app"
    SQLITE_DB_PATH="$(pwd)/data/data.sqlite"
    
    if [ -d "$DB_BROWSER_APP" ]; then
        echo -e "${GREEN}DB Browser für SQLite gefunden. Öffne Datenbank...${NC}"
        open -a "DB Browser for SQLite" "$SQLITE_DB_PATH"
    else
        echo -e "${RED}DB Browser für SQLite nicht gefunden.${NC}"
        echo -e "${BLUE}Möchten Sie DB Browser für SQLite installieren? (j/n)${NC}"
        read -n 1 INSTALL_DB_BROWSER
        
        if [[ $INSTALL_DB_BROWSER == "j" || $INSTALL_DB_BROWSER == "J" ]]; then
            echo ""
            echo -e "${BLUE}Öffne Download-Seite für DB Browser für SQLite...${NC}"
            open "https://sqlitebrowser.org/dl/"
        fi
    fi
    
    echo -e "${GREEN}Drücke eine beliebige Taste, um fortzufahren...${NC}"
    read -n 1
}

# Hauptprogramm
while true; do
    show_menu
    read -n 1 option
    echo ""
    
    case $option in
        1)
            open_db_browser
            ;;
        2)
            ./create-indexes.sh
            echo -e "${GREEN}Drücke eine beliebige Taste, um fortzufahren...${NC}"
            read -n 1
            ;;
        3)
            ./backup-bookmarks.sh
            echo -e "${GREEN}Drücke eine beliebige Taste, um fortzufahren...${NC}"
            read -n 1
            ;;
        4)
            ./find-duplicates.sh
            echo -e "${GREEN}Drücke eine beliebige Taste, um fortzufahren...${NC}"
            read -n 1
            ;;
        5)
            ./show-db-entries.sh
            echo -e "${GREEN}Drücke eine beliebige Taste, um fortzufahren...${NC}"
            read -n 1
            ;;
        6)
            echo -e "${GREEN}Auf Wiedersehen!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Ungültige Option. Bitte wähle 1-6.${NC}"
            sleep 2
            ;;
    esac
done 