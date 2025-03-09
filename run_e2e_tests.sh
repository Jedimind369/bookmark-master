#!/bin/bash
# Skript zum Ausführen der E2E-Tests lokal

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

# Prüfen, ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    print_error "Docker ist nicht installiert. Bitte installieren Sie Docker und versuchen Sie es erneut."
    exit 1
fi

# Prüfen, ob Docker Compose installiert ist
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose ist nicht installiert. Bitte installieren Sie Docker Compose und versuchen Sie es erneut."
    exit 1
fi

# Verzeichnisse erstellen
print_message "Erstelle notwendige Verzeichnisse..."
mkdir -p test-data
mkdir -p cypress-results/screenshots
mkdir -p cypress-results/videos

# Testdaten erstellen
print_message "Erstelle Testdaten..."
if [ ! -f "test-data/sample_bookmarks.json" ]; then
    cat > test-data/sample_bookmarks.json << EOF
[
  {"url": "https://example.com", "title": "Example Website"},
  {"url": "https://test.org", "title": "Test Organization"}
]
EOF
fi

# Fragen, ob bestehende Container gestoppt werden sollen
read -p "Möchten Sie bestehende Container stoppen? (j/n): " stop_containers
if [[ $stop_containers =~ ^[Jj]$ ]]; then
    print_message "Stoppe bestehende Container..."
    docker-compose down
fi

# Fragen, ob im UI-Modus oder Headless-Modus ausgeführt werden soll
read -p "Möchten Sie die Tests im UI-Modus ausführen? (j/n): " ui_mode
if [[ $ui_mode =~ ^[Jj]$ ]]; then
    print_message "Starte E2E-Tests im UI-Modus..."
    
    # Starte die Anwendung
    print_message "Starte die Anwendung..."
    docker-compose -f docker-compose.e2e.yml up -d webapp processor database redis
    
    # Warte, bis die Anwendung bereit ist
    print_message "Warte, bis die Anwendung bereit ist..."
    sleep 10
    
    # Starte Cypress im UI-Modus
    print_message "Starte Cypress im UI-Modus..."
    cd webapp && npx cypress open
else
    print_message "Starte E2E-Tests im Headless-Modus..."
    
    # Starte die Tests mit Docker Compose
    docker-compose -f docker-compose.e2e.yml up --build --exit-code-from e2e
    
    # Prüfe, ob die Tests erfolgreich waren
    if [ $? -eq 0 ]; then
        print_message "E2E-Tests erfolgreich abgeschlossen!"
    else
        print_error "E2E-Tests fehlgeschlagen!"
    fi
fi

# Fragen, ob Container gestoppt werden sollen
read -p "Möchten Sie die Container stoppen? (j/n): " stop_after
if [[ $stop_after =~ ^[Jj]$ ]]; then
    print_message "Stoppe Container..."
    docker-compose -f docker-compose.e2e.yml down
fi

print_message "Testergebnisse sind verfügbar unter:"
print_message "- Screenshots: cypress-results/screenshots"
print_message "- Videos: cypress-results/videos" 