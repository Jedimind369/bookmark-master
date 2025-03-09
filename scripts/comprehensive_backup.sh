#!/bin/bash
# Umfassendes Backup-Skript für den Bookmark Manager
# Dieses Skript führt sowohl lokale als auch GitHub-Backups durch

# Konfiguration
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="backups"
DB_PATH="data/database/bookmarks.db"
REPO_PATH=$(pwd)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
BACKUP_BRANCH="backup-${TIMESTAMP}"
LOG_FILE="logs/backup_${TIMESTAMP}.log"

# Logging-Funktion
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Verzeichnis für Logs erstellen, falls es nicht existiert
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$BACKUP_DIR"

log_message "Starte umfassendes Backup"
log_message "Aktueller Branch: $BRANCH"

# 1. SQLite-Datenbank-Backup
log_message "Führe SQLite-Datenbank-Backup durch..."
if [ -f "$DB_PATH" ]; then
    # Integritätsprüfung
    INTEGRITY_CHECK=$(sqlite3 $DB_PATH "PRAGMA integrity_check;")
    if [ "$INTEGRITY_CHECK" != "ok" ]; then
        log_message "WARNUNG: Integritätsprüfung fehlgeschlagen: $INTEGRITY_CHECK"
    else
        log_message "Integritätsprüfung erfolgreich."
        
        # Backup erstellen
        DB_BACKUP_FILE="$BACKUP_DIR/bookmarks_${TIMESTAMP}.db"
        sqlite3 $DB_PATH ".backup $DB_BACKUP_FILE"
        
        # Komprimieren
        gzip -f $DB_BACKUP_FILE
        COMPRESSED_FILE="${DB_BACKUP_FILE}.gz"
        
        # Prüfsumme erstellen
        sha256sum $COMPRESSED_FILE > "${COMPRESSED_FILE}.sha256"
        
        log_message "Datenbank-Backup erstellt: $COMPRESSED_FILE"
    fi
else
    log_message "FEHLER: Datenbank-Datei nicht gefunden: $DB_PATH"
fi

# 2. Code-Backup auf GitHub
log_message "Führe Code-Backup auf GitHub durch..."

# Aktuellen Branch speichern
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Ungespeicherte Änderungen prüfen
if [[ -n $(git status --porcelain) ]]; then
    log_message "Ungespeicherte Änderungen gefunden"
    
    # Änderungen stagen
    git add .
    
    # Commit erstellen
    COMMIT_MSG="Automatischer Backup-Commit: ${TIMESTAMP}"
    git commit -m "$COMMIT_MSG"
    
    log_message "Änderungen committed: $COMMIT_MSG"
fi

# Neuen Backup-Branch erstellen
git checkout -b $BACKUP_BRANCH
log_message "Backup-Branch erstellt: $BACKUP_BRANCH"

# Zum Remote-Repository pushen
git push -u origin $BACKUP_BRANCH
if [[ $? -eq 0 ]]; then
    log_message "Push erfolgreich durchgeführt"
else
    log_message "FEHLER: Push fehlgeschlagen"
fi

# Zurück zum ursprünglichen Branch
git checkout $CURRENT_BRANCH
log_message "Zurück zum Branch: $CURRENT_BRANCH"

# 3. Alte Backups bereinigen (älter als 30 Tage)
log_message "Bereinige alte Backups..."
find $BACKUP_DIR -name "bookmarks_*.db.gz" -type f -mtime +30 -delete
find $BACKUP_DIR -name "bookmarks_*.db.gz.sha256" -type f -mtime +30 -delete

# 4. Alte Backup-Branches bereinigen (optional)
# Hier könnte man alte Backup-Branches löschen, wenn gewünscht

log_message "Umfassendes Backup abgeschlossen"
echo "Backup abgeschlossen. Siehe Log-Datei für Details: $LOG_FILE" 