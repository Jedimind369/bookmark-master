#!/bin/bash

# Farben für die Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Stoppe Bookmark-Master Server...${NC}"

# Beende alle laufenden Server-Prozesse
echo -e "${BLUE}Beende Backend-Server (ts-node)...${NC}"
pkill -f "ts-node" || true
echo -e "${GREEN}Backend-Server wurde beendet${NC}"

echo -e "${BLUE}Beende Frontend-Server (next)...${NC}"
pkill -f "next" || true
echo -e "${GREEN}Frontend-Server wurde beendet${NC}"

echo -e "${GREEN}Alle Server wurden gestoppt!${NC}" 