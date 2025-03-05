#!/bin/bash

# Farben für die Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Pfade zu den Verzeichnissen
ROOT_DIR="$(dirname "$0")"
SERVER_DIR="$ROOT_DIR/src/server"
CLIENT_DIR="$ROOT_DIR/src/client"

echo -e "${GREEN}Starte Bookmark-Master Server...${NC}"

# Beende alle laufenden Server-Prozesse
echo -e "${BLUE}Beende alle laufenden Server-Prozesse...${NC}"
pkill -f "ts-node" || true
pkill -f "next" || true
sleep 2

# Starte den Backend-Server
echo -e "${BLUE}Starte Backend-Server...${NC}"
(cd "$SERVER_DIR" && npm run dev) &
BACKEND_PID=$!
echo -e "${GREEN}Backend-Server gestartet mit PID: $BACKEND_PID${NC}"

# Warte kurz, damit der Backend-Server Zeit hat zu starten
sleep 3

# Starte den Frontend-Server
echo -e "${BLUE}Starte Frontend-Server...${NC}"
(cd "$CLIENT_DIR" && npm run dev) &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend-Server gestartet mit PID: $FRONTEND_PID${NC}"

# Warte kurz, um zu überprüfen, ob die Server erfolgreich gestartet wurden
sleep 5

# Überprüfe, ob die Server laufen
BACKEND_RUNNING=$(ps -p $BACKEND_PID > /dev/null && echo "true" || echo "false")
FRONTEND_RUNNING=$(ps -p $FRONTEND_PID > /dev/null && echo "true" || echo "false")

if [ "$BACKEND_RUNNING" = "true" ] && [ "$FRONTEND_RUNNING" = "true" ]; then
    echo -e "${GREEN}Beide Server wurden erfolgreich gestartet!${NC}"
    echo -e "${GREEN}Backend läuft auf: http://localhost:8000${NC}"
    echo -e "${GREEN}Frontend läuft auf: http://localhost:3000 (oder dem nächsten freien Port)${NC}"
    echo -e "${BLUE}Um die Server zu beenden, führe ./stop-servers.sh aus${NC}"
else
    echo -e "${RED}Fehler beim Starten der Server!${NC}"
    if [ "$BACKEND_RUNNING" = "false" ]; then
        echo -e "${RED}Backend-Server konnte nicht gestartet werden.${NC}"
    fi
    if [ "$FRONTEND_RUNNING" = "false" ]; then
        echo -e "${RED}Frontend-Server konnte nicht gestartet werden.${NC}"
    fi
    echo -e "${BLUE}Bitte überprüfe die Logs für weitere Informationen.${NC}"
fi 