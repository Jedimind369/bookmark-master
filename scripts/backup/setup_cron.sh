#!/bin/bash
# Skript zum Einrichten des SQLite-Backup-Skripts als Cron-Job

# Pfad zum Backup-Skript
BACKUP_SCRIPT_PATH="$(pwd)/scripts/backup/sqlite_backup.sh"

# Prüfen, ob das Backup-Skript existiert
if [ ! -f "$BACKUP_SCRIPT_PATH" ]; then
    echo "Fehler: Backup-Skript nicht gefunden unter $BACKUP_SCRIPT_PATH"
    exit 1
fi

# Ausführbar machen
chmod +x "$BACKUP_SCRIPT_PATH"

# Cron-Job-Eintrag erstellen (täglich um 3:00 Uhr)
CRON_ENTRY="0 3 * * * $BACKUP_SCRIPT_PATH > /dev/null 2>&1"

# Temporäre Crontab-Datei erstellen
TEMP_CRONTAB=$(mktemp)
crontab -l > "$TEMP_CRONTAB" 2>/dev/null || true

# Prüfen, ob der Job bereits existiert
if grep -q "$BACKUP_SCRIPT_PATH" "$TEMP_CRONTAB"; then
    echo "Cron-Job existiert bereits."
else
    # Job hinzufügen
    echo "$CRON_ENTRY" >> "$TEMP_CRONTAB"
    crontab "$TEMP_CRONTAB"
    echo "Cron-Job wurde erfolgreich eingerichtet. Backup wird täglich um 3:00 Uhr ausgeführt."
fi

# Temporäre Datei löschen
rm "$TEMP_CRONTAB"

echo "Aktuelle Cron-Jobs:"
crontab -l 