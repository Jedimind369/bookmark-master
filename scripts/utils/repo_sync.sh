#!/bin/bash

# Repository Sync Script
# Dieses Skript überprüft das Repository auf Änderungen und führt bei Bedarf einen Push durch

# Konfiguration
REPO_PATH=$(pwd)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
REMOTE="origin"
LOG_FILE="$REPO_PATH/logs/repo_sync.log"
IMPORTANT_DIRS=("scripts/ai" "tests" "src/core" "config")

# Logging-Funktion
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Verzeichnis für Logs erstellen, falls es nicht existiert
mkdir -p "$(dirname "$LOG_FILE")"

log_message "Starte Repository-Synchronisation"
log_message "Aktueller Branch: $BRANCH"

# Prüfen, ob es Änderungen gibt
if [[ -n $(git status --porcelain) ]]; then
    log_message "Ungespeicherte Änderungen gefunden"
    
    # Prüfen, ob wichtige Verzeichnisse betroffen sind
    IMPORTANT_CHANGES=false
    for dir in "${IMPORTANT_DIRS[@]}"; do
        if [[ -n $(git status --porcelain "$dir" 2>/dev/null) ]]; then
            log_message "Wichtige Änderungen in $dir gefunden"
            IMPORTANT_CHANGES=true
            break
        fi
    done
    
    if [[ "$IMPORTANT_CHANGES" = true ]]; then
        log_message "Führe Commit und Push für wichtige Änderungen durch"
        
        # Änderungen stagen
        git add .
        
        # Commit erstellen
        COMMIT_MSG="Automatischer Commit: Wichtige Änderungen in $(date '+%Y-%m-%d %H:%M:%S')"
        git commit -m "$COMMIT_MSG"
        
        # Push durchführen
        git push $REMOTE $BRANCH
        
        if [[ $? -eq 0 ]]; then
            log_message "Push erfolgreich durchgeführt"
        else
            log_message "FEHLER: Push fehlgeschlagen"
        fi
    else
        log_message "Keine wichtigen Änderungen gefunden, kein Commit notwendig"
    fi
else
    log_message "Keine Änderungen im Repository gefunden"
fi

# Prüfen, ob es Updates vom Remote gibt
log_message "Prüfe auf Updates vom Remote-Repository"
git fetch $REMOTE

LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "$REMOTE/$BRANCH")
BASE=$(git merge-base @ "$REMOTE/$BRANCH")

if [[ $LOCAL = $REMOTE ]]; then
    log_message "Repository ist aktuell"
elif [[ $LOCAL = $BASE ]]; then
    log_message "Repository ist nicht aktuell, führe Pull durch"
    git pull $REMOTE $BRANCH
    log_message "Pull abgeschlossen"
else
    log_message "WARNUNG: Lokale und Remote-Änderungen divergieren"
    log_message "Manuelles Eingreifen erforderlich"
fi

log_message "Repository-Synchronisation abgeschlossen" 