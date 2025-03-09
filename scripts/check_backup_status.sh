#!/bin/bash
# Skript zur Überprüfung des Backup-Status
# Dieses Skript überprüft den Status aller Backups und gibt einen Bericht aus

# Konfiguration
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/backup_status_${TIMESTAMP}.log"
BACKUP_DIR="backups"
DB_PATH="data/database/bookmarks.db"
MIRROR_BACKUPS=$(find . -name "mirror_backup_*.tar.gz" | sort -r)
DB_BACKUPS=$(find $BACKUP_DIR -name "bookmarks_*.db.gz" | sort -r)

# Logging-Funktion
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Verzeichnis für Logs erstellen, falls es nicht existiert
mkdir -p "$(dirname "$LOG_FILE")"

log_message "Starte Überprüfung des Backup-Status"

# 1. Git-Repository-Status
log_message "Überprüfe Git-Repository-Status..."
echo "=== Git-Repository-Status ==="
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Aktueller Branch: $CURRENT_BRANCH"
log_message "Aktueller Branch: $CURRENT_BRANCH"

# Ungespeicherte Änderungen
UNCOMMITTED_CHANGES=$(git status --porcelain)
if [[ -n "$UNCOMMITTED_CHANGES" ]]; then
    echo "WARNUNG: Es gibt ungespeicherte Änderungen:"
    echo "$UNCOMMITTED_CHANGES"
    log_message "WARNUNG: Es gibt ungespeicherte Änderungen"
else
    echo "Keine ungespeicherten Änderungen"
    log_message "Keine ungespeicherten Änderungen"
fi

# Remote-Status
git fetch --all > /dev/null 2>&1
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "@{u}" 2>/dev/null)
BASE=$(git merge-base @ "@{u}" 2>/dev/null)

if [[ -z "$REMOTE" ]]; then
    echo "WARNUNG: Kein Upstream-Branch konfiguriert"
    log_message "WARNUNG: Kein Upstream-Branch konfiguriert"
elif [[ $LOCAL = $REMOTE ]]; then
    echo "Repository ist aktuell"
    log_message "Repository ist aktuell"
elif [[ $LOCAL = $BASE ]]; then
    echo "WARNUNG: Repository ist nicht aktuell, Pull erforderlich"
    log_message "WARNUNG: Repository ist nicht aktuell, Pull erforderlich"
elif [[ $REMOTE = $BASE ]]; then
    echo "WARNUNG: Lokale Änderungen müssen gepusht werden"
    log_message "WARNUNG: Lokale Änderungen müssen gepusht werden"
else
    echo "WARNUNG: Repository hat divergierende Änderungen"
    log_message "WARNUNG: Repository hat divergierende Änderungen"
fi

echo ""

# 2. Datenbank-Backup-Status
log_message "Überprüfe Datenbank-Backup-Status..."
echo "=== Datenbank-Backup-Status ==="

if [[ ! -f "$DB_PATH" ]]; then
    echo "FEHLER: Datenbank-Datei nicht gefunden: $DB_PATH"
    log_message "FEHLER: Datenbank-Datei nicht gefunden: $DB_PATH"
else
    echo "Datenbank-Datei gefunden: $DB_PATH"
    log_message "Datenbank-Datei gefunden: $DB_PATH"
    
    # Datenbank-Größe
    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    echo "Datenbank-Größe: $DB_SIZE"
    log_message "Datenbank-Größe: $DB_SIZE"
    
    # Datenbank-Integrität
    INTEGRITY_CHECK=$(sqlite3 $DB_PATH "PRAGMA integrity_check;" 2>/dev/null)
    if [[ "$INTEGRITY_CHECK" == "ok" ]]; then
        echo "Datenbank-Integrität: OK"
        log_message "Datenbank-Integrität: OK"
    else
        echo "WARNUNG: Datenbank-Integrität: $INTEGRITY_CHECK"
        log_message "WARNUNG: Datenbank-Integrität: $INTEGRITY_CHECK"
    fi
fi

# Datenbank-Backups
if [[ -z "$DB_BACKUPS" ]]; then
    echo "WARNUNG: Keine Datenbank-Backups gefunden"
    log_message "WARNUNG: Keine Datenbank-Backups gefunden"
else
    LATEST_DB_BACKUP=$(echo "$DB_BACKUPS" | head -n1)
    BACKUP_COUNT=$(echo "$DB_BACKUPS" | wc -l | tr -d ' ')
    LATEST_BACKUP_DATE=$(date -r "$LATEST_DB_BACKUP" "+%Y-%m-%d %H:%M:%S")
    
    echo "Anzahl der Datenbank-Backups: $BACKUP_COUNT"
    echo "Letztes Backup: $LATEST_DB_BACKUP ($LATEST_BACKUP_DATE)"
    
    log_message "Anzahl der Datenbank-Backups: $BACKUP_COUNT"
    log_message "Letztes Backup: $LATEST_DB_BACKUP ($LATEST_BACKUP_DATE)"
    
    # Prüfen, ob das letzte Backup älter als 24 Stunden ist
    BACKUP_AGE=$(( $(date +%s) - $(date -r "$LATEST_DB_BACKUP" +%s) ))
    if [[ $BACKUP_AGE -gt 86400 ]]; then
        echo "WARNUNG: Letztes Backup ist älter als 24 Stunden"
        log_message "WARNUNG: Letztes Backup ist älter als 24 Stunden"
    fi
fi

echo ""

# 3. Repository-Spiegel-Status
log_message "Überprüfe Repository-Spiegel-Status..."
echo "=== Repository-Spiegel-Status ==="

if [[ -z "$MIRROR_BACKUPS" ]]; then
    echo "WARNUNG: Keine Repository-Spiegel gefunden"
    log_message "WARNUNG: Keine Repository-Spiegel gefunden"
else
    LATEST_MIRROR=$(echo "$MIRROR_BACKUPS" | head -n1)
    MIRROR_COUNT=$(echo "$MIRROR_BACKUPS" | wc -l | tr -d ' ')
    LATEST_MIRROR_DATE=$(date -r "$LATEST_MIRROR" "+%Y-%m-%d %H:%M:%S")
    
    echo "Anzahl der Repository-Spiegel: $MIRROR_COUNT"
    echo "Letzter Spiegel: $LATEST_MIRROR ($LATEST_MIRROR_DATE)"
    
    log_message "Anzahl der Repository-Spiegel: $MIRROR_COUNT"
    log_message "Letzter Spiegel: $LATEST_MIRROR ($LATEST_MIRROR_DATE)"
    
    # Prüfen, ob der letzte Spiegel älter als 7 Tage ist
    MIRROR_AGE=$(( $(date +%s) - $(date -r "$LATEST_MIRROR" +%s) ))
    if [[ $MIRROR_AGE -gt 604800 ]]; then
        echo "WARNUNG: Letzter Repository-Spiegel ist älter als 7 Tage"
        log_message "WARNUNG: Letzter Repository-Spiegel ist älter als 7 Tage"
    fi
fi

echo ""

# 4. Empfehlungen
log_message "Generiere Empfehlungen..."
echo "=== Empfehlungen ==="

if [[ -n "$UNCOMMITTED_CHANGES" ]]; then
    echo "- Führen Sie 'scripts/add_unversioned_files.sh' aus, um ungespeicherte Änderungen zu committen"
fi

if [[ -z "$DB_BACKUPS" || $BACKUP_AGE -gt 86400 ]]; then
    echo "- Führen Sie 'scripts/backup/sqlite_backup.sh' aus, um ein aktuelles Datenbank-Backup zu erstellen"
fi

if [[ -z "$MIRROR_BACKUPS" || $MIRROR_AGE -gt 604800 ]]; then
    echo "- Führen Sie 'scripts/create_github_mirror.sh' aus, um einen aktuellen Repository-Spiegel zu erstellen"
fi

if [[ $LOCAL != $REMOTE && $REMOTE = $BASE ]]; then
    echo "- Führen Sie 'git push' aus, um lokale Änderungen zu GitHub zu pushen"
fi

if [[ $LOCAL != $REMOTE && $LOCAL = $BASE ]]; then
    echo "- Führen Sie 'git pull' aus, um Änderungen von GitHub zu holen"
fi

if [[ $LOCAL != $REMOTE && $LOCAL != $BASE && $REMOTE != $BASE ]]; then
    echo "- Führen Sie 'git pull --rebase' aus, um divergierende Änderungen zu beheben"
fi

echo ""
echo "Backup-Status-Überprüfung abgeschlossen"
echo "Siehe Log-Datei für Details: $LOG_FILE"

log_message "Backup-Status-Überprüfung abgeschlossen" 