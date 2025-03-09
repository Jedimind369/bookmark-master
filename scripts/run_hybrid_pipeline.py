#!/usr/bin/env python3
"""
Orchestriert einen Testlauf mit dem hybriden Scraper und anschließender KI-Veredelung.
Der Prozess umfasst:
1. Extraktion des Kerninhalts mit dem hybriden Scraper (ScrapingBee + Smartproxy)
2. KI-basierte Generierung von hochwertigen Beschreibungen
3. Semantische Analyse mit Embeddings und Clustering
4. Generierung eines HTML-Berichts
"""

import os
import sys
import json
import time
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime
import gzip
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env-Datei
load_dotenv()

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/hybrid_pipeline.log')
    ]
)
logger = logging.getLogger("hybrid_pipeline")

def setup_directories():
    """
    Erstellt die notwendigen Verzeichnisse.
    """
    directories = [
        "data/enriched",
        "data/embeddings/hybrid_run",
        "data/reports",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    logger.info(f"Verzeichnisse erstellt: {', '.join(directories)}")

def run_command(command, description):
    """
    Führt einen Befehl aus und gibt zurück, ob er erfolgreich war.
    
    Args:
        command: Auszuführender Befehl
        description: Beschreibung des Befehls für Logging
        
    Returns:
        bool: True, wenn der Befehl erfolgreich war, sonst False
    """
    logger.info(f"Ausführung: {description}")
    logger.info(f"Befehl: {command}")
    
    start_time = time.time()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    duration = time.time() - start_time
    
    if process.returncode == 0:
        logger.info(f"Erfolgreich abgeschlossen in {duration:.1f} Sekunden")
        return True
    else:
        logger.error(f"Fehler bei der Ausführung von '{description}'")
        logger.error(f"Fehlercode: {process.returncode}")
        logger.error(f"Fehlerausgabe: {stderr.decode('utf-8')}")
        return False

def check_scraping_success(output_file):
    """
    Überprüft, ob das Scraping erfolgreich war, indem die Ausgabedatei analysiert wird.
    
    Args:
        output_file: Pfad zur Ausgabedatei des Scrapings
        
    Returns:
        bool: True, wenn das Scraping erfolgreich war, sonst False
    """
    try:
        # Prüfe, ob die Datei eine .gz-Endung hat
        if output_file.endswith('.gz'):
            with gzip.open(output_file, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        else:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # Überprüfe, ob alle Einträge Fehler enthalten
        all_errors = all("error" in item for item in data)
        
        if all_errors:
            logger.warning(f"Alle Einträge in {output_file} enthalten Fehler")
            return False
        
        # Überprüfe, ob mindestens ein Eintrag erfolgreich war
        success_count = sum(1 for item in data if "error" not in item)
        logger.info(f"Erfolgreiche Einträge: {success_count}/{len(data)}")
        
        return success_count > 0
    
    except Exception as e:
        logger.error(f"Fehler beim Überprüfen der Scraping-Ergebnisse: {str(e)}")
        return False

def run_hybrid_pipeline(args):
    """
    Führt die Pipeline mit dem hybriden Scraper aus.
    
    Args:
        args: Kommandozeilenargumente
        
    Returns:
        bool: True, wenn die Pipeline erfolgreich war, sonst False
    """
    # Erstelle die notwendigen Verzeichnisse
    setup_directories()
    
    # Schritt 1: Extraktion des Kerninhalts mit dem hybriden Scraper
    logger.info("SCHRITT 1: Extraktion des Kerninhalts mit dem hybriden Scraper")
    
    # Definiere die Pfade für die angereicherten Daten
    hybrid_output_file = "data/enriched/hybrid_enriched.json.gz"
    
    if args.skip_scraping:
        logger.info("Scraping übersprungen (--skip-scraping)")
        # Wenn Scraping übersprungen wird, verwenden wir die vorhandenen angereicherten Daten
        if os.path.exists(args.existing_enriched):
            logger.info(f"Verwende vorhandene angereicherte Daten: {args.existing_enriched}")
            # Kopiere die vorhandenen Daten in die erwartete Position
            copy_command = f"cp {args.existing_enriched} {hybrid_output_file}"
            if not run_command(copy_command, "Kopieren der vorhandenen angereicherten Daten"):
                logger.error("Kopieren der vorhandenen angereicherten Daten fehlgeschlagen")
                return False
        else:
            logger.error(f"Vorhandene angereicherte Daten nicht gefunden: {args.existing_enriched}")
            return False
    else:
        # Verwende den hybriden Scraper
        hybrid_command = (
            f"python scripts/scraping/hybrid_scraper.py --input {args.input_file} "
            f"--output {hybrid_output_file} --limit {args.limit} --max-workers {args.max_workers} "
            f"--max-text-length {args.max_text_length} --dynamic-threshold {args.dynamic_threshold}"
        )
        
        if args.scrapingbee_key:
            hybrid_command += f" --scrapingbee-key {args.scrapingbee_key}"
        
        if args.smartproxy_url:
            hybrid_command += f" --smartproxy-url {args.smartproxy_url}"
        
        hybrid_success = run_command(hybrid_command, "Hybrider Scraper")
        
        # Überprüfe, ob das Scraping tatsächlich erfolgreich war
        if hybrid_success and os.path.exists(hybrid_output_file):
            hybrid_success = check_scraping_success(hybrid_output_file)
        
        if not hybrid_success:
            logger.error("Hybrider Scraper fehlgeschlagen")
            return False
    
    # Schritt 2: KI-basierte Generierung von hochwertigen Beschreibungen
    logger.info("SCHRITT 2: KI-basierte Generierung von hochwertigen Beschreibungen")
    
    ai_output_file = "data/enriched/hybrid_fully_enhanced.json.gz"
    ai_command = f"python scripts/ai/enhanced_descriptions.py {hybrid_output_file} --output-file {ai_output_file}"
    
    if not run_command(ai_command, "KI-Beschreibungsgenerierung"):
        logger.error("KI-Beschreibungsgenerierung fehlgeschlagen")
        return False
    
    # Schritt 3: Semantische Analyse mit Embeddings und Clustering
    logger.info("SCHRITT 3: Semantische Analyse mit Embeddings und Clustering")
    
    embedding_command = (
        f"python scripts/semantic/generate_embeddings.py {ai_output_file} "
        f"--model all-MiniLM-L6-v2 --output-dir data/embeddings/hybrid_run --num-clusters {args.num_clusters}"
    )
    
    if not run_command(embedding_command, "Generierung von Embeddings und Clustering"):
        logger.error("Generierung von Embeddings und Clustering fehlgeschlagen")
        return False
    
    # Schritt 4: Generierung eines HTML-Berichts
    logger.info("SCHRITT 4: Generierung eines HTML-Berichts")
    
    report_file = "data/reports/hybrid_report.html"
    report_command = f"python scripts/export/simple_html_report.py {ai_output_file} {report_file}"
    
    if not run_command(report_command, "Generierung des HTML-Berichts"):
        logger.error("Generierung des HTML-Berichts fehlgeschlagen")
        return False
    
    # Schritt 5: Dashboard starten
    logger.info("SCHRITT 5: Dashboard starten")
    
    # Aktualisiere die Dashboard-Konfiguration
    dashboard_config_command = f"""
python -c "
import json

# Lade die Dashboard-Konfiguration
with open('scripts/monitoring/simple_dashboard.py', 'r') as f:
    content = f.read()

# Aktualisiere die Pfade
content = content.replace('value=\"data/enriched/fully_enhanced.json\"', 'value=\"{ai_output_file}\"')
content = content.replace('value=\"data/embeddings/enhanced/bookmark_embeddings.pkl\"', 'value=\"data/embeddings/hybrid_run/bookmark_embeddings.pkl\"')

# Speichere die aktualisierte Konfiguration
with open('scripts/monitoring/simple_dashboard.py', 'w') as f:
    f.write(content)

print('Dashboard-Konfiguration aktualisiert')
"
        """
    
    if not run_command(dashboard_config_command, "Aktualisierung der Dashboard-Konfiguration"):
        logger.error("Aktualisierung der Dashboard-Konfiguration fehlgeschlagen")
        return False
    
    # Starte das Dashboard
    dashboard_command = "python -m streamlit run scripts/monitoring/simple_dashboard.py --server.port 8502 --server.address 0.0.0.0 > logs/dashboard.log 2>&1 &"
    
    if not run_command(dashboard_command, "Start des Dashboards"):
        logger.error("Start des Dashboards fehlgeschlagen")
        return False
    
    logger.info("Dashboard gestartet unter http://localhost:8502")
    logger.info("Log-Datei: logs/dashboard.log")
    
    # Pipeline erfolgreich abgeschlossen
    logger.info("Testlauf erfolgreich abgeschlossen!")
    logger.info(f"Verarbeitete URLs: {args.limit}")
    logger.info("Benutze http://localhost:8502 für das Dashboard")
    logger.info(f"HTML-Bericht: {report_file}")
    
    return True

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Führt einen Testlauf der Bookmark-Pipeline mit dem hybriden Scraper aus")
    
    # Eingabedatei
    parser.add_argument("input_file", help="Pfad zur JSON-Datei mit URLs oder Lesezeichen")
    
    # Allgemeine Optionen
    parser.add_argument("--limit", type=int, default=200,
                        help="Anzahl der zu verarbeitenden URLs")
    parser.add_argument("--existing-enriched", default="data/enriched/fully_enhanced.json",
                        help="Pfad zu vorhandenen angereicherten Daten (wenn --skip-scraping verwendet wird)")
    
    # Optionen zum Überspringen von Schritten
    parser.add_argument("--skip-scraping", action="store_true",
                        help="Überspringt das Scraping und verwendet vorhandene angereicherte Daten")
    
    # Scraping-Optionen
    parser.add_argument("--max-workers", type=int, default=3,
                        help="Maximale Anzahl gleichzeitiger Worker")
    parser.add_argument("--max-text-length", type=int, default=5000,
                        help="Maximale Länge des extrahierten Textes")
    parser.add_argument("--dynamic-threshold", type=float, default=0.2,
                        help="Schwellenwert für die Verwendung von ScrapingBee (0.0-1.0)")
    
    # API-Schlüssel
    parser.add_argument("--scrapingbee-key", 
                        help="ScrapingBee API-Schlüssel (überschreibt Umgebungsvariable)")
    parser.add_argument("--smartproxy-url", 
                        help="Smartproxy URL (überschreibt Umgebungsvariable)")
    
    # Clustering-Optionen
    parser.add_argument("--num-clusters", type=int, default=20,
                        help="Anzahl der Cluster für die semantische Analyse")
    
    args = parser.parse_args()
    
    # Führe die Pipeline aus
    success = run_hybrid_pipeline(args)
    
    # Beende das Programm mit dem entsprechenden Exit-Code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 