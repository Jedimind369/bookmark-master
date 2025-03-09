#!/bin/bash
# Skript zum Ausführen aller Backup-Skripte in einer bestimmten Reihenfolge
# Dieses Skript führt alle Backup-Skripte aus und erstellt einen Gesamtbericht

# Konfiguration
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/all_backups_${TIMESTAMP}.log"
BACKUP_DIR="backups"
REPORT_FILE="$BACKUP_DIR/backup_report_${TIMESTAMP}.txt"

# Logging-Funktion
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Verzeichnis für Logs und Backups erstellen, falls nicht vorhanden
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$BACKUP_DIR"

log_message "Starte Ausführung aller Backup-Skripte"
echo "Starte Ausführung aller Backup-Skripte..."

# Bericht-Header
echo "=== Backup-Bericht: $(date '+%Y-%m-%d %H:%M:%S') ===" > "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 1. Datenbank-Backup
log_message "Führe Datenbank-Backup aus..."
echo "1. Datenbank-Backup"
echo "-------------------" >> "$REPORT_FILE"
if [[ -f "scripts/backup/sqlite_backup.sh" ]]; then
    ./scripts/backup/sqlite_backup.sh | tee -a "$REPORT_FILE"
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_message "Datenbank-Backup erfolgreich"
        echo "Status: Erfolgreich" >> "$REPORT_FILE"
    else
        log_message "FEHLER: Datenbank-Backup fehlgeschlagen"
        echo "Status: FEHLER" >> "$REPORT_FILE"
    fi
else
    log_message "FEHLER: Datenbank-Backup-Skript nicht gefunden"
    echo "Status: FEHLER - Skript nicht gefunden" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 2. Unversionierte Dateien hinzufügen
log_message "Füge unversionierte Dateien hinzu..."
echo "2. Unversionierte Dateien"
echo "------------------------" >> "$REPORT_FILE"
if [[ -f "scripts/add_unversioned_files.sh" ]]; then
    # Automatische Bestätigung für das Skript
    echo "j" | ./scripts/add_unversioned_files.sh | tee -a "$REPORT_FILE"
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_message "Unversionierte Dateien erfolgreich hinzugefügt"
        echo "Status: Erfolgreich" >> "$REPORT_FILE"
    else
        log_message "FEHLER: Hinzufügen unversionierter Dateien fehlgeschlagen"
        echo "Status: FEHLER" >> "$REPORT_FILE"
    fi
else
    log_message "FEHLER: Skript zum Hinzufügen unversionierter Dateien nicht gefunden"
    echo "Status: FEHLER - Skript nicht gefunden" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 3. Repository-Spiegel erstellen
log_message "Erstelle Repository-Spiegel..."
echo "3. Repository-Spiegel"
echo "--------------------" >> "$REPORT_FILE"
if [[ -f "scripts/create_github_mirror.sh" ]]; then
    ./scripts/create_github_mirror.sh | tee -a "$REPORT_FILE"
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_message "Repository-Spiegel erfolgreich erstellt"
        echo "Status: Erfolgreich" >> "$REPORT_FILE"
    else
        log_message "FEHLER: Erstellung des Repository-Spiegels fehlgeschlagen"
        echo "Status: FEHLER" >> "$REPORT_FILE"
    fi
else
    log_message "FEHLER: Skript zur Erstellung des Repository-Spiegels nicht gefunden"
    echo "Status: FEHLER - Skript nicht gefunden" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 4. Umfassendes Backup
log_message "Führe umfassendes Backup aus..."
echo "4. Umfassendes Backup"
echo "--------------------" >> "$REPORT_FILE"
if [[ -f "scripts/comprehensive_backup.sh" ]]; then
    ./scripts/comprehensive_backup.sh | tee -a "$REPORT_FILE"
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_message "Umfassendes Backup erfolgreich durchgeführt"
        echo "Status: Erfolgreich" >> "$REPORT_FILE"
    else
        log_message "FEHLER: Umfassendes Backup fehlgeschlagen"
        echo "Status: FEHLER" >> "$REPORT_FILE"
    fi
else
    log_message "FEHLER: Skript für umfassendes Backup nicht gefunden"
    echo "Status: FEHLER - Skript nicht gefunden" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# 5. Backup-Status überprüfen
log_message "Überprüfe Backup-Status..."
echo "5. Backup-Status"
echo "---------------" >> "$REPORT_FILE"
if [[ -f "scripts/check_backup_status.sh" ]]; then
    ./scripts/check_backup_status.sh | tee -a "$REPORT_FILE"
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_message "Backup-Status erfolgreich überprüft"
        echo "Status: Erfolgreich" >> "$REPORT_FILE"
    else
        log_message "FEHLER: Überprüfung des Backup-Status fehlgeschlagen"
        echo "Status: FEHLER" >> "$REPORT_FILE"
    fi
else
    log_message "FEHLER: Skript zur Überprüfung des Backup-Status nicht gefunden"
    echo "Status: FEHLER - Skript nicht gefunden" >> "$REPORT_FILE"
fi

# Abschluss
log_message "Alle Backup-Skripte wurden ausgeführt"
echo ""
echo "Alle Backup-Skripte wurden ausgeführt"
echo "Backup-Bericht: $REPORT_FILE"
echo "Log-Datei: $LOG_FILE" 