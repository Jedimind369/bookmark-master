#!/usr/bin/env python3
import os
import json
from pathlib import Path

def test_monitoring_setup():
    # Prüfe, ob die Verzeichnisse existieren
    assert os.path.exists("data/monitoring"), "Monitoring-Verzeichnis fehlt"
    assert os.path.exists("data/monitoring/backups"), "Backup-Verzeichnis fehlt"
    assert os.path.exists("logs"), "Log-Verzeichnis fehlt"
    
    # Prüfe, ob die Dateien existieren
    assert os.path.exists("data/monitoring/api_usage.json"), "API-Nutzungsdatei fehlt"
    assert os.path.exists("data/monitoring/config.json"), "Konfigurationsdatei fehlt"
    assert os.path.exists("data/monitoring/backups/backup_metadata.json"), "Backup-Metadaten fehlen"
    
    # Prüfe, ob die Dateien gültiges JSON enthalten
    with open("data/monitoring/api_usage.json", "r") as f:
        api_usage = json.load(f)
        assert "budget_limit" in api_usage, "Budget-Limit fehlt in API-Nutzungsdatei"
    
    with open("data/monitoring/config.json", "r") as f:
        config = json.load(f)
        assert "warning_thresholds" in config, "Warning-Thresholds fehlen in Konfigurationsdatei"
    
    with open("data/monitoring/backups/backup_metadata.json", "r") as f:
        metadata = json.load(f)
        assert "backups" in metadata, "Backups-Liste fehlt in Backup-Metadaten"
    
    print("Monitoring-Setup erfolgreich getestet")
    return True

if __name__ == "__main__":
    test_monitoring_setup() 