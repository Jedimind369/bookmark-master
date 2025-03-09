#!/bin/bash

# Setup-Skript für die CI-Umgebung
# Dieses Skript richtet die Umgebung für die CI-Tests ein

# Erstelle Verzeichnisse
mkdir -p data/monitoring/backups
mkdir -p logs

# Erstelle Konfigurationsdatei
cat > data/monitoring/config.json << EOF
{
  "budget_limit": 100,
  "warning_thresholds": [50, 80, 90]
}
EOF

# Erstelle API-Nutzungsdatei
cat > data/monitoring/api_usage.json << EOF
{
  "budget_limit": 20.0,
  "total_cost": 0.0,
  "usage": {},
  "last_update": "2025-03-09T00:00:00",
  "context": {}
}
EOF

# Erstelle Backup-Metadaten
cat > data/monitoring/backups/backup_metadata.json << EOF
{
  "backups": [],
  "last_full_backup": null,
  "last_incremental_backup": null
}
EOF

# Erstelle Log-Datei
touch logs/api_monitoring.log

# Erstelle ein Mock-Backup für Tests
cat > data/monitoring/backups/api_usage_backup_test.json << EOF
{
  "budget_limit": 20.0,
  "total_cost": 5.0,
  "usage": {
    "2025-03-08": {
      "qwq": {"input_tokens": 1000, "output_tokens": 500, "cost": 1.0},
      "claude_sonnet": {"input_tokens": 500, "output_tokens": 200, "cost": 4.0}
    }
  },
  "last_update": "2025-03-08T12:00:00",
  "context": {}
}
EOF

# Erstelle MD5-Prüfsumme für das Backup
md5sum data/monitoring/backups/api_usage_backup_test.json > data/monitoring/backups/api_usage_backup_test.json.md5

echo "CI-Umgebung erfolgreich eingerichtet" 