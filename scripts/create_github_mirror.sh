#!/bin/bash
# Skript zum Erstellen eines exakten Spiegels des GitHub-Repositories
# Dieses Skript erstellt eine vollständige Kopie des Repositories inklusive aller Branches und Tags

# Konfiguration
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MIRROR_DIR="mirror_backup_${TIMESTAMP}"
REPO_URL="https://github.com/Jedimind369/bookmark-master.git"
LOG_FILE="logs/mirror_backup_${TIMESTAMP}.log"

# Logging-Funktion
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Verzeichnis für Logs erstellen, falls es nicht existiert
mkdir -p "$(dirname "$LOG_FILE")"

log_message "Starte Erstellung eines Repository-Spiegels"
log_message "Repository-URL: $REPO_URL"
log_message "Zielverzeichnis: $MIRROR_DIR"

# 1. Repository mit --mirror klonen
log_message "Klone Repository mit --mirror Option..."
git clone --mirror $REPO_URL $MIRROR_DIR
if [[ $? -eq 0 ]]; then
    log_message "Repository erfolgreich geklont"
else
    log_message "FEHLER: Repository konnte nicht geklont werden"
    exit 1
fi

# 2. In das Verzeichnis wechseln
cd $MIRROR_DIR || exit 1

# 3. Git LFS-Objekte abrufen (falls Git LFS verwendet wird)
log_message "Rufe Git LFS-Objekte ab..."
git lfs fetch --all
if [[ $? -eq 0 ]]; then
    log_message "Git LFS-Objekte erfolgreich abgerufen"
else
    log_message "WARNUNG: Git LFS-Objekte konnten nicht abgerufen werden oder Git LFS wird nicht verwendet"
fi

# 4. Zurück zum ursprünglichen Verzeichnis
cd ..

# 5. Repository archivieren
log_message "Archiviere Repository-Spiegel..."
tar -czf "${MIRROR_DIR}.tar.gz" $MIRROR_DIR
if [[ $? -eq 0 ]]; then
    log_message "Repository-Spiegel erfolgreich archiviert: ${MIRROR_DIR}.tar.gz"
    
    # Prüfsumme erstellen
    sha256sum "${MIRROR_DIR}.tar.gz" > "${MIRROR_DIR}.tar.gz.sha256"
    log_message "Prüfsumme erstellt: ${MIRROR_DIR}.tar.gz.sha256"
    
    # Temporäres Verzeichnis entfernen
    rm -rf $MIRROR_DIR
    log_message "Temporäres Verzeichnis entfernt"
else
    log_message "FEHLER: Repository-Spiegel konnte nicht archiviert werden"
fi

log_message "Repository-Spiegel-Erstellung abgeschlossen"
echo "Repository-Spiegel erstellt: ${MIRROR_DIR}.tar.gz"
echo "Siehe Log-Datei für Details: $LOG_FILE"

# Anleitung zur Wiederherstellung
echo ""
echo "Anleitung zur Wiederherstellung des Repository-Spiegels:"
echo "1. Entpacken Sie das Archiv: tar -xzf ${MIRROR_DIR}.tar.gz"
echo "2. Wechseln Sie in das Verzeichnis: cd $MIRROR_DIR"
echo "3. Klonen Sie das Repository: git clone $MIRROR_DIR neues_verzeichnis"
echo "   Oder fügen Sie es als Remote hinzu: git remote add mirror $MIRROR_DIR" 