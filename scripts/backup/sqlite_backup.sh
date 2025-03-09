#!/bin/bash
# Erweitertes SQLite-Backup-Skript mit Integritätsprüfung

# Konfiguration
DB_PATH="data/database/bookmarks.db"
BACKUP_DIR="backups"
CLOUD_BACKUP_DIR="s3://my-bookmark-backups" # Oder ein anderer Cloud-Speicher
RETENTION_DAYS=30
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/bookmarks_$TIMESTAMP.db"
LOG_FILE="$BACKUP_DIR/backup_log.txt"

# Logging-Funktion
log_message() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# Backup-Verzeichnis erstellen, falls nicht vorhanden
mkdir -p $BACKUP_DIR

# Integritätsprüfung vor dem Backup
log_message "Starte Integritätsprüfung der Datenbank..."
INTEGRITY_CHECK=$(sqlite3 $DB_PATH "PRAGMA integrity_check;")
if [ "$INTEGRITY_CHECK" != "ok" ]; then
    log_message "WARNUNG: Integritätsprüfung fehlgeschlagen: $INTEGRITY_CHECK"
    # Optional: E-Mail-Benachrichtigung senden
else
    log_message "Integritätsprüfung erfolgreich."
fi

# Konsistente Kopie mit SQLite-Backup-API erstellen
log_message "Erstelle Backup..."
sqlite3 $DB_PATH ".backup $BACKUP_FILE"

# Komprimieren des Backups
log_message "Komprimiere Backup..."
gzip -f $BACKUP_FILE
COMPRESSED_FILE="${BACKUP_FILE}.gz"

# Prüfsumme erstellen
log_message "Erstelle Prüfsumme..."
sha256sum $COMPRESSED_FILE > "${COMPRESSED_FILE}.sha256"

# In Cloud-Speicher kopieren (wenn konfiguriert)
if [ -n "$CLOUD_BACKUP_DIR" ]; then
    log_message "Kopiere Backup in Cloud-Speicher..."
    # Hier je nach Cloud-Provider den entsprechenden Befehl verwenden
    # Beispiel für AWS S3:
    # aws s3 cp $COMPRESSED_FILE $CLOUD_BACKUP_DIR/
    # aws s3 cp "${COMPRESSED_FILE}.sha256" $CLOUD_BACKUP_DIR/
fi

# Alte Backups bereinigen (älter als RETENTION_DAYS)
log_message "Bereinige alte Backups..."
find $BACKUP_DIR -name "bookmarks_*.db.gz" -type f -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "bookmarks_*.db.gz.sha256" -type f -mtime +$RETENTION_DAYS -delete

log_message "Backup abgeschlossen: ${COMPRESSED_FILE}" 