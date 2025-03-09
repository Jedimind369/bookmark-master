#!/bin/bash
# Skript zum Starten des gesamten Bookmark-Manager-Systems

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

# Prüfen, ob .env-Datei existiert, sonst aus .env.example erstellen
if [ ! -f .env ]; then
    print_warning ".env-Datei nicht gefunden. Erstelle aus .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_message ".env-Datei wurde erstellt. Bitte überprüfen und anpassen Sie die Einstellungen."
    else
        print_error ".env.example-Datei nicht gefunden. Bitte erstellen Sie eine .env-Datei manuell."
        exit 1
    fi
fi

# Verzeichnisse erstellen
print_message "Erstelle notwendige Verzeichnisse..."
mkdir -p data/bookmarks
mkdir -p data/processed
mkdir -p data/enriched
mkdir -p data/embeddings
mkdir -p logs
mkdir -p backups

# Docker-Compose ausführen
print_message "Starte das System mit Docker Compose..."
docker-compose up -d

# Prüfen, ob alle Container gestartet wurden
if [ $? -eq 0 ]; then
    print_message "Alle Container wurden erfolgreich gestartet."
    print_message "Webapp ist verfügbar unter: http://localhost:3000"
    print_message "Grafana-Dashboard ist verfügbar unter: http://localhost:3001 (Benutzername: admin, Passwort: admin)"
else
    print_error "Es gab ein Problem beim Starten der Container. Bitte überprüfen Sie die Logs mit 'docker-compose logs'."
    exit 1
fi

# Backup-Cron-Job einrichten
print_message "Richte Backup-Cron-Job ein..."
chmod +x scripts/backup/setup_cron.sh
./scripts/backup/setup_cron.sh

print_message "System-Start abgeschlossen!" 