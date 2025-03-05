#!/bin/bash

# Variablen
DATE=$(date +%Y-%m-%d)
DB_PATH="$(pwd)/data/data.sqlite"
BACKUP_DIR="$(pwd)/backups"
CSV_DIR="${BACKUP_DIR}/csv"
DB_BACKUP="${BACKUP_DIR}/db_backup_${DATE}.sqlite"
CSV_BACKUP="${CSV_DIR}/bookmarks_${DATE}.csv"

# Verzeichnisse erstellen falls nicht vorhanden
mkdir -p "${BACKUP_DIR}"
mkdir -p "${CSV_DIR}"

# 1. Datenbank-Backup erstellen
cp "${DB_PATH}" "${DB_BACKUP}"
echo "Datenbank gesichert: ${DB_BACKUP}"

# 2. CSV-Export der Bookmarks
sqlite3 "${DB_PATH}" <<EOF
.headers on
.mode csv
.output "${CSV_BACKUP}"
SELECT * FROM bookmarks;
.quit
EOF

echo "CSV-Export erstellt: ${CSV_BACKUP}"
echo "Backup abgeschlossen!" 