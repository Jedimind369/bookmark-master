#!/bin/bash

# Setup-Skript für den Repository-Monitor
# Dieses Skript richtet alle Komponenten für die automatische Repository-Synchronisation ein

# Konfiguration
REPO_PATH=$(pwd)
SERVICE_NAME="bookmark-repo-monitor"
SERVICE_FILE="$REPO_PATH/scripts/utils/bookmark-repo-monitor.service"
MONITOR_SCRIPT="$REPO_PATH/scripts/utils/mcp_repo_monitor.js"
SYNC_SCRIPT="$REPO_PATH/scripts/utils/repo_sync.sh"
GITHUB_DIR="$REPO_PATH/.github/workflows"
GITHUB_ACTION="$GITHUB_DIR/repo-sync.yml"
LOG_DIR="$REPO_PATH/logs"

# Logging-Funktion
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Prüfen, ob das Skript im Repository-Root ausgeführt wird
if [ ! -d ".git" ]; then
    log_message "FEHLER: Dieses Skript muss im Repository-Root ausgeführt werden."
    exit 1
fi

log_message "Starte Setup für Repository-Monitor..."

# Verzeichnisse erstellen
log_message "Erstelle Verzeichnisse..."
mkdir -p "$LOG_DIR"
mkdir -p "$GITHUB_DIR"

# Prüfen, ob die Skripte existieren
if [ ! -f "$MONITOR_SCRIPT" ] || [ ! -f "$SYNC_SCRIPT" ] || [ ! -f "$SERVICE_FILE" ] || [ ! -f "$GITHUB_ACTION" ]; then
    log_message "FEHLER: Erforderliche Dateien fehlen. Bitte stellen Sie sicher, dass alle Skripte erstellt wurden."
    exit 1
fi

# Skripte ausführbar machen
log_message "Mache Skripte ausführbar..."
chmod +x "$MONITOR_SCRIPT"
chmod +x "$SYNC_SCRIPT"

# Prüfen, ob wir auf einem macOS-System sind
if [[ "$OSTYPE" == "darwin"* ]]; then
    log_message "macOS erkannt, richte LaunchAgent ein..."
    
    # LaunchAgent für macOS erstellen
    LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
    LAUNCH_AGENT_FILE="$LAUNCH_AGENT_DIR/com.bookmark-master.repo-monitor.plist"
    
    mkdir -p "$LAUNCH_AGENT_DIR"
    
    cat > "$LAUNCH_AGENT_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bookmark-master.repo-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/node</string>
        <string>${MONITOR_SCRIPT}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>${REPO_PATH}</string>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/repo-monitor.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/repo-monitor-error.log</string>
</dict>
</plist>
EOF
    
    # LaunchAgent laden
    log_message "Lade LaunchAgent..."
    launchctl unload "$LAUNCH_AGENT_FILE" 2>/dev/null
    launchctl load "$LAUNCH_AGENT_FILE"
    
    log_message "LaunchAgent erfolgreich eingerichtet."
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log_message "Linux erkannt, richte Systemd-Service ein..."
    
    # Systemd-Service-Datei kopieren
    SYSTEMD_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SYSTEMD_DIR"
    cp "$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_NAME.service"
    
    # Systemd-Service aktivieren und starten
    log_message "Aktiviere und starte Systemd-Service..."
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME"
    systemctl --user start "$SERVICE_NAME"
    
    log_message "Systemd-Service erfolgreich eingerichtet."
else
    log_message "Betriebssystem nicht unterstützt. Bitte starten Sie den Monitor manuell mit 'node $MONITOR_SCRIPT'."
fi

# Git-Hook für automatische Synchronisation einrichten
log_message "Richte Git-Hook für automatische Synchronisation ein..."
HOOK_DIR="$REPO_PATH/.git/hooks"
POST_COMMIT_HOOK="$HOOK_DIR/post-commit"

mkdir -p "$HOOK_DIR"

cat > "$POST_COMMIT_HOOK" << EOF
#!/bin/bash

# Post-Commit-Hook für automatische Repository-Synchronisation
REPO_PATH="\$(git rev-parse --show-toplevel)"
SYNC_SCRIPT="\$REPO_PATH/scripts/utils/repo_sync.sh"

# Prüfen, ob das Synchronisationsskript existiert
if [ -f "\$SYNC_SCRIPT" ]; then
    echo "Führe Repository-Synchronisation nach Commit durch..."
    bash "\$SYNC_SCRIPT"
fi

exit 0
EOF

chmod +x "$POST_COMMIT_HOOK"

log_message "Git-Hook erfolgreich eingerichtet."

# Abschließende Informationen
log_message "Setup abgeschlossen. Der Repository-Monitor ist jetzt aktiv."
log_message "Logs werden in $LOG_DIR gespeichert."
log_message "GitHub Action wurde in $GITHUB_ACTION eingerichtet."
log_message "Sie können den Monitor manuell mit 'node $MONITOR_SCRIPT' starten."

exit 0 