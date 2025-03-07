#!/usr/bin/env python3

"""
settings.py

Konfigurationseinstellungen für den Scraping-Prozess mit der Zyte API.
"""

import os
from pathlib import Path

# Hauptverzeichnis
BASE_DIR = Path(__file__).parent.parent.parent

# Zyte API-Konfiguration
ZYTE_API_KEY = os.environ.get("ZYTE_API_KEY", "")
ZYTE_API_ENDPOINT = "https://api.zyte.com/v1/extract"

# Erweiterte Einstellungen für die Zyte API
ZYTE_API_SETTINGS = {
    # Browser-Rendering aktivieren, um JavaScript-basierte Seiten zu verarbeiten
    "browserHtml": True,
    
    # Erweiterte Extraktion aktivieren
    "article": True,  # Extrahiert Hauptartikelinhalt
    "product": True,  # Extrahiert Produktinformationen, falls vorhanden
    
    # Metadaten extrahieren
    "metadata": True,
    
    # JavaScript ausführen und warten, bis die Seite vollständig geladen ist
    "javascript": True,
    "wait": 2,  # Wartezeit in Sekunden nach dem Laden der Seite
    
    # Anti-Bot-Maßnahmen umgehen
    "geolocation": "us",  # Geografischer Standort
    "customHttpRequestHeaders": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    },
    
    # Fehlerbehandlung und Wiederholungsversuche
    "httpResponseTimeout": 30,  # Timeout in Sekunden
    "retryOnHttpErrors": True,  # Wiederholung bei HTTP-Fehlern
    "maxHttpRetries": 3,  # Maximale Anzahl von Wiederholungsversuchen
}

# Batch-Verarbeitung
BATCH_SIZE = 100  # Anzahl der URLs pro Batch
MAX_CONCURRENT_REQUESTS = 10  # Maximale Anzahl gleichzeitiger Anfragen

# Dateipfade
DATA_DIR = BASE_DIR / "data" / "scraped"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = BASE_DIR / "logs" / "scraping"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Dateinamen
SUCCESS_LOG = LOG_DIR / "success.log"
ERROR_LOG = LOG_DIR / "error.log"
RETRY_LOG = LOG_DIR / "retry.log"

# Speicherzeitraum für Protokolle (in Tagen)
LOG_RETENTION_DAYS = 30 