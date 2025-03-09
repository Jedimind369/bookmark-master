#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hybrid-Pipeline mit SQLite-Datenbankunterstützung.

Kombiniert den Hybrid-Scraper mit der SQLite-Datenbank und generiert AI-Beschreibungen,
Embeddings und Berichte.
"""

import os
import sys
import json
import gzip
import time
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Konfiguriere Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/hybrid_pipeline_db.log")
    ]
)
logger = logging.getLogger("hybrid_pipeline_db")

def ensure_directories():
    """Erstellt die notwendigen Verzeichnisse, falls sie nicht existieren."""
    directories = [
        "data/enriched",
        "data/database",
        "data/embeddings/hybrid_run",
        "data/reports",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    logger.info(f"Verzeichnisse erstellt: {', '.join(directories)}")

def run_command(command, description):
    """
    Führt einen Befehl aus und loggt das Ergebnis.
    
    Args:
        command: Auszuführender Befehl
        description: Beschreibung des Befehls
        
    Returns:
        bool: True, wenn erfolgreich, sonst False
    """
    start_time = time.time()
    logger.info(f"Ausführung: {description}")
    logger.info(f"Befehl: {command}")
    
    try:
        # Führe den Befehl aus
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'
        )
        
        # Berechne die Ausführungszeit
        execution_time = time.time() - start_time
        
        logger.info(f"Erfolgreich abgeschlossen in {execution_time:.1f} Sekunden")
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Fehler beim Ausführen des Befehls: {e}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        return False

def extract_content(input_file, db_path, limit=None, max_workers=3, max_text_length=5000):
    """
    Extrahiert den Inhalt von Webseiten mit dem Hybrid-Scraper und speichert in der Datenbank.
    
    Args:
        input_file: Pfad zur Eingabedatei mit URLs oder Bookmarks
        db_path: Pfad zur SQLite-Datenbank
        limit: Maximale Anzahl zu verarbeitender URLs
        max_workers: Maximale Anzahl an Worker-Threads
        max_text_length: Maximale Länge des extrahierten Textes
        
    Returns:
        bool: True, wenn erfolgreich, sonst False
    """
    logger.info("SCHRITT 1: Extraktion des Kerninhalts mit dem hybriden Scraper")
    
    # Baue den Befehl
    command = f"python scripts/database/hybrid_scraper_db.py --input {input_file} --db-path {db_path}"
    
    # Füge optionale Parameter hinzu
    if limit:
        command += f" --limit {limit}"
    
    command += f" --max-workers {max_workers}"
    command += f" --max-text-length {max_text_length}"
    command += f" --dynamic-threshold 0.2"
    
    # Führe den Befehl aus
    success = run_command(command, "Hybrider Scraper mit Datenbankunterstützung")
    
    # Berechne die Anzahl der Einträge in der Datenbank
    if success:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pages")
        count = cursor.fetchone()[0]
        conn.close()
        
        logger.info(f"Erfolgreiche Einträge in der Datenbank: {count}")
    
    return success

def generate_descriptions(db_path):
    """
    Generiert Beschreibungen für Webseiten mit AI-Technologie.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        
    Returns:
        bool: True, wenn erfolgreich, sonst False
    """
    logger.info("SCHRITT 2: KI-basierte Generierung von hochwertigen Beschreibungen")
    
    # Baue den Befehl
    command = f"python scripts/ai/enhanced_descriptions_db.py --db-path {db_path}"
    
    # Führe den Befehl aus
    return run_command(command, "KI-Beschreibungsgenerierung für Datenbankeinträge")

def generate_embeddings(db_path, model="all-MiniLM-L6-v2", num_clusters=20):
    """
    Generiert Embeddings und führt Clustering durch.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        model: Name des zu verwendenden Embedding-Modells
        num_clusters: Anzahl der Cluster
        
    Returns:
        bool: True, wenn erfolgreich, sonst False
    """
    logger.info("SCHRITT 3: Semantische Analyse mit Embeddings und Clustering")
    
    # Baue den Befehl
    command = f"python scripts/semantic/generate_embeddings_db.py --db-path {db_path} --model {model} --num-clusters {num_clusters}"
    
    # Führe den Befehl aus
    return run_command(command, "Generierung von Embeddings und Clustering für Datenbankeinträge")

def generate_report(db_path, output_file="data/reports/hybrid_report_db.html"):
    """
    Generiert einen HTML-Bericht aus den Datenbankdaten.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        output_file: Pfad zur Ausgabedatei
        
    Returns:
        bool: True, wenn erfolgreich, sonst False
    """
    logger.info("SCHRITT 4: Generierung eines HTML-Berichts")
    
    # Baue den Befehl
    command = f"python scripts/export/html_report_db.py --db-path {db_path} --output {output_file}"
    
    # Führe den Befehl aus
    return run_command(command, "Generierung des HTML-Berichts aus Datenbankdaten")

def update_dashboard_config(db_path):
    """
    Aktualisiert die Dashboard-Konfiguration.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        
    Returns:
        bool: True, wenn erfolgreich, sonst False
    """
    logger.info("SCHRITT 5: Dashboard starten")
    
    # Baue den Python-Code für die Konfiguration
    python_code = f"""
import json

# Lade die Dashboard-Konfiguration
with open('scripts/monitoring/db_dashboard.py', 'r') as f:
    content = f.read()

# Aktualisiere die Pfade
content = content.replace('DB_PATH = "data/database/bookmarks.db"', 'DB_PATH = "{db_path}"')

# Speichere die aktualisierte Konfiguration
with open('scripts/monitoring/db_dashboard.py', 'w') as f:
    f.write(content)

print('Dashboard-Konfiguration aktualisiert')
"""
    
    # Schreibe den Python-Code in eine temporäre Datei
    with open("temp_update_config.py", "w") as f:
        f.write(python_code)
    
    # Führe den Python-Code aus
    success = run_command("python temp_update_config.py", "Aktualisierung der Dashboard-Konfiguration")
    
    # Lösche die temporäre Datei
    os.remove("temp_update_config.py")
    
    return success

def start_dashboard():
    """
    Startet das Dashboard.
    
    Returns:
        bool: True, wenn erfolgreich, sonst False
    """
    # Baue den Befehl
    command = "python -m streamlit run scripts/monitoring/db_dashboard.py --server.port 8502 --server.address 0.0.0.0 > logs/dashboard.log 2>&1 &"
    
    # Führe den Befehl aus
    success = run_command(command, "Start des Dashboards")
    
    if success:
        logger.info("Dashboard gestartet unter http://localhost:8502")
        logger.info("Log-Datei: logs/dashboard.log")
    
    return success

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Hybrid-Pipeline mit SQLite-Datenbankunterstützung")
    parser.add_argument("input_file", help="Eingabe-JSON-Datei mit URLs oder Bookmarks")
    parser.add_argument("--db-path", default="data/database/bookmarks.db", help="Pfad zur SQLite-Datenbank")
    parser.add_argument("--limit", type=int, help="Maximale Anzahl zu verarbeitender URLs")
    parser.add_argument("--max-workers", type=int, default=3, help="Maximale Anzahl an Worker-Threads")
    parser.add_argument("--max-text-length", type=int, default=5000, help="Maximale Länge des extrahierten Textes")
    parser.add_argument("--skip-steps", type=str, help="Zu überspringende Schritte (kommagetrennt, z. B. '1,3')")
    args = parser.parse_args()
    
    # Erstelle die notwendigen Verzeichnisse
    ensure_directories()
    
    # Bestimme die zu überspringenden Schritte
    skip_steps = []
    if args.skip_steps:
        skip_steps = [int(step) for step in args.skip_steps.split(",")]
    
    # Schritt 1: Extraktion des Kerninhalts
    if 1 not in skip_steps:
        if not extract_content(args.input_file, args.db_path, args.limit, args.max_workers, args.max_text_length):
            logger.error("Fehler bei der Extraktion des Kerninhalts. Pipeline wird abgebrochen.")
            return False
    else:
        logger.info("SCHRITT 1: Extraktion des Kerninhalts wird übersprungen")
    
    # Schritt 2: Generierung von Beschreibungen
    if 2 not in skip_steps:
        if not generate_descriptions(args.db_path):
            logger.error("Fehler bei der Generierung von Beschreibungen. Pipeline wird abgebrochen.")
            return False
    else:
        logger.info("SCHRITT 2: Generierung von Beschreibungen wird übersprungen")
    
    # Schritt 3: Generierung von Embeddings
    if 3 not in skip_steps:
        if not generate_embeddings(args.db_path):
            logger.error("Fehler bei der Generierung von Embeddings. Pipeline wird abgebrochen.")
            return False
    else:
        logger.info("SCHRITT 3: Generierung von Embeddings wird übersprungen")
    
    # Schritt 4: Generierung eines HTML-Berichts
    if 4 not in skip_steps:
        if not generate_report(args.db_path):
            logger.error("Fehler bei der Generierung des HTML-Berichts. Pipeline wird abgebrochen.")
            return False
    else:
        logger.info("SCHRITT 4: Generierung des HTML-Berichts wird übersprungen")
    
    # Schritt 5: Dashboard starten
    if 5 not in skip_steps:
        if not update_dashboard_config(args.db_path):
            logger.error("Fehler bei der Aktualisierung der Dashboard-Konfiguration. Pipeline wird abgebrochen.")
            return False
        
        if not start_dashboard():
            logger.error("Fehler beim Start des Dashboards. Pipeline wird abgebrochen.")
            return False
    else:
        logger.info("SCHRITT 5: Dashboard wird nicht gestartet")
    
    logger.info("Testlauf erfolgreich abgeschlossen!")
    
    # Berechne die Anzahl der verarbeiteten URLs
    import sqlite3
    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pages")
    count = cursor.fetchone()[0]
    conn.close()
    
    logger.info(f"Verarbeitete URLs: {count}")
    logger.info("Benutze http://localhost:8502 für das Dashboard")
    logger.info("HTML-Bericht: data/reports/hybrid_report_db.html")
    
    return True

if __name__ == "__main__":
    main() 