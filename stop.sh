#!/bin/bash
# Skript zum Stoppen des Bookmark-Manager-Systems

# Farbdefinitionen
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funktion zum Anzeigen von Nachrichten
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Prüfen, ob Docker Compose installiert ist
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose ist nicht installiert. Bitte installieren Sie Docker Compose und versuchen Sie es erneut."
    exit 1
fi

# Fragen, ob Daten beibehalten werden sollen
read -p "Möchten Sie die Daten beibehalten? (j/n): " keep_data

if [[ $keep_data =~ ^[Jj]$ ]]; then
    print_message "Stoppe das System und behalte die Daten..."
    docker-compose down
else
    print_warning "Stoppe das System und lösche alle Container und Volumes..."
    print_warning "ACHTUNG: Alle Daten werden gelöscht!"
    read -p "Sind Sie sicher? (j/n): " confirm
    
    if [[ $confirm =~ ^[Jj]$ ]]; then
        docker-compose down -v
        print_message "System wurde gestoppt und alle Daten wurden gelöscht."
    else
        docker-compose down
        print_message "System wurde gestoppt und Daten wurden beibehalten."
    fi
fi

print_message "System-Stopp abgeschlossen!" 