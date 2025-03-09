#!/bin/bash
# Skript zum Hinzufügen aller unversionierten Dateien zu Git
# Dieses Skript fügt alle unversionierten Dateien zu Git hinzu und erstellt einen Commit

# Konfiguration
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/add_unversioned_${TIMESTAMP}.log"
COMMIT_MSG="Hinzufügen aller unversionierten Dateien: ${TIMESTAMP}"

# Logging-Funktion
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Verzeichnis für Logs erstellen, falls es nicht existiert
mkdir -p "$(dirname "$LOG_FILE")"

log_message "Starte Hinzufügen unversionierter Dateien"

# 1. Unversionierte Dateien auflisten
UNVERSIONED_FILES=$(git ls-files --others --exclude-standard)
if [[ -z "$UNVERSIONED_FILES" ]]; then
    log_message "Keine unversionierten Dateien gefunden"
    echo "Keine unversionierten Dateien gefunden"
    exit 0
fi

# 2. Unversionierte Dateien anzeigen
log_message "Unversionierte Dateien gefunden:"
echo "Folgende unversionierte Dateien wurden gefunden:"
echo "$UNVERSIONED_FILES" | tee -a "$LOG_FILE"
echo ""

# 3. Bestätigung vom Benutzer einholen
read -p "Möchten Sie diese Dateien zu Git hinzufügen? (j/n): " CONFIRM
if [[ "$CONFIRM" != "j" && "$CONFIRM" != "J" ]]; then
    log_message "Vorgang abgebrochen"
    echo "Vorgang abgebrochen"
    exit 0
fi

# 4. Dateien zu Git hinzufügen
log_message "Füge Dateien zu Git hinzu..."
git add $UNVERSIONED_FILES
if [[ $? -eq 0 ]]; then
    log_message "Dateien erfolgreich hinzugefügt"
else
    log_message "FEHLER: Dateien konnten nicht hinzugefügt werden"
    echo "FEHLER: Dateien konnten nicht hinzugefügt werden"
    exit 1
fi

# 5. Commit erstellen
log_message "Erstelle Commit..."
git commit -m "$COMMIT_MSG"
if [[ $? -eq 0 ]]; then
    log_message "Commit erfolgreich erstellt: $COMMIT_MSG"
    echo "Commit erfolgreich erstellt: $COMMIT_MSG"
else
    log_message "FEHLER: Commit konnte nicht erstellt werden"
    echo "FEHLER: Commit konnte nicht erstellt werden"
    exit 1
fi

# 6. Push anbieten
read -p "Möchten Sie die Änderungen zu GitHub pushen? (j/n): " PUSH_CONFIRM
if [[ "$PUSH_CONFIRM" == "j" || "$PUSH_CONFIRM" == "J" ]]; then
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    log_message "Pushe Änderungen zu GitHub (Branch: $BRANCH)..."
    git push origin $BRANCH
    if [[ $? -eq 0 ]]; then
        log_message "Push erfolgreich durchgeführt"
        echo "Push erfolgreich durchgeführt"
    else
        log_message "FEHLER: Push fehlgeschlagen"
        echo "FEHLER: Push fehlgeschlagen"
        exit 1
    fi
else
    log_message "Push übersprungen"
    echo "Push übersprungen"
fi

log_message "Hinzufügen unversionierter Dateien abgeschlossen"
echo "Hinzufügen unversionierter Dateien abgeschlossen"
echo "Siehe Log-Datei für Details: $LOG_FILE" 