#!/usr/bin/env python3
"""
Orchestriert einen Testlauf mit 200 URLs und anschließender KI-Veredelung.
Der Prozess umfasst:
1. Extraktion des Kerninhalts mit Zyte API
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

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/test_pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_pipeline")

def setup_directories():
    """Erstellt alle notwendigen Verzeichnisse."""
    directories = [
        "data/enriched",
        "data/embeddings/test_run",
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

def check_zyte_scraping_success(output_file):
    """
    Überprüft, ob das Zyte-Scraping erfolgreich war, indem die Ausgabedatei analysiert wird.
    
    Args:
        output_file: Pfad zur Ausgabedatei des Zyte-Scrapings
        
    Returns:
        bool: True, wenn das Scraping erfolgreich war, sonst False
    """
    try:
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
        logger.error(f"Fehler beim Überprüfen der Zyte-Scraping-Ergebnisse: {str(e)}")
        return False

def run_test_pipeline(args):
    """
    Führt den Testlauf der Pipeline aus.
    
    Args:
        args: Befehlszeilenargumente
    
    Returns:
        bool: True, wenn alle Schritte erfolgreich waren, sonst False
    """
    setup_directories()
    
    # Schritt 1: Extraktion des Kerninhalts mit Zyte API
    logger.info("SCHRITT 1: Extraktion des Kerninhalts mit Zyte API")
    
    # Definiere die Pfade für die angereicherten Daten
    zyte_output_file = "data/enriched/zyte_test_enriched.json"
    
    if args.skip_scraping:
        logger.info("Scraping übersprungen (--skip-scraping)")
        # Wenn Scraping übersprungen wird, verwenden wir die vorhandenen angereicherten Daten
        if os.path.exists(args.existing_enriched):
            logger.info(f"Verwende vorhandene angereicherte Daten: {args.existing_enriched}")
            # Kopiere die vorhandenen Daten in die erwartete Position
            copy_command = f"cp {args.existing_enriched} {zyte_output_file}"
            if not run_command(copy_command, "Kopieren der vorhandenen angereicherten Daten"):
                logger.error("Kopieren der vorhandenen angereicherten Daten fehlgeschlagen")
                return False
        else:
            logger.error(f"Vorhandene angereicherte Daten nicht gefunden: {args.existing_enriched}")
            return False
    else:
        # Versuche zuerst die Zyte API
        zyte_command = f"python scripts/scraping/optimized_zyte_scraper.py {args.input_file} --output-file {zyte_output_file} --limit {args.limit} --max-workers {args.max_workers} --max-text-length {args.max_text_length}"
        
        zyte_success = run_command(zyte_command, "Zyte API-Scraping")
        
        # Überprüfe, ob das Zyte-Scraping tatsächlich erfolgreich war
        if zyte_success and os.path.exists(zyte_output_file):
            zyte_success = check_zyte_scraping_success(zyte_output_file)
        
        # Wenn die Zyte API fehlschlägt, verwende den Fallback-Scraper
        if not zyte_success:
            logger.warning("Zyte API-Scraping fehlgeschlagen, verwende Fallback-Scraper")
            fallback_command = f"python scripts/scraping/fallback_scraper.py {args.input_file} --output-file {zyte_output_file} --limit {args.limit} --max-workers {args.max_workers} --max-text-length {args.max_text_length}"
            
            if not run_command(fallback_command, "Fallback-Scraping"):
                logger.error("Fallback-Scraping fehlgeschlagen")
                return False
    
    # Schritt 2: KI-basierte Generierung von hochwertigen Beschreibungen
    logger.info("SCHRITT 2: KI-basierte Generierung von hochwertigen Beschreibungen")
    
    if args.skip_ai:
        logger.info("KI-Generierung übersprungen (--skip-ai)")
    else:
        # Wir geben die Zyte-Ergebnisse an den KI-Beschreibungsgenerator weiter
        ai_command = f"python scripts/ai/enhanced_descriptions.py data/enriched/zyte_test_enriched.json --output-file data/enriched/test_fully_enhanced.json"
        
        if not run_command(ai_command, "KI-Beschreibungsgenerierung"):
            logger.error("KI-Beschreibungsgenerierung fehlgeschlagen")
            return False
    
    # Schritt 3: Semantische Analyse mit Embeddings und Clustering
    logger.info("SCHRITT 3: Semantische Analyse mit Embeddings und Clustering")
    
    if args.skip_embeddings:
        logger.info("Semantische Analyse übersprungen (--skip-embeddings)")
    else:
        embeddings_command = f"python scripts/semantic/generate_embeddings.py data/enriched/test_fully_enhanced.json --model {args.model} --output-dir data/embeddings/test_run --num-clusters {args.num_clusters}"
        
        if not run_command(embeddings_command, "Generierung von Embeddings und Clustering"):
            logger.error("Generierung von Embeddings und Clustering fehlgeschlagen")
            return False
    
    # Schritt 4: Generierung eines HTML-Berichts
    logger.info("SCHRITT 4: Generierung eines HTML-Berichts")
    
    if args.skip_report:
        logger.info("Berichtgenerierung übersprungen (--skip-report)")
    else:
        report_command = f"python scripts/export/simple_html_report.py data/enriched/test_fully_enhanced.json data/reports/test_report.html"
        
        if not run_command(report_command, "Generierung des HTML-Berichts"):
            logger.error("Generierung des HTML-Berichts fehlgeschlagen")
            return False
    
    # Schritt 5: Dashboard starten
    logger.info("SCHRITT 5: Dashboard starten")
    
    if args.skip_dashboard:
        logger.info("Dashboard-Start übersprungen (--skip-dashboard)")
    else:
        # Aktualisiere das Dashboard, um die Testdaten anzuzeigen
        update_dashboard_command = f"""python -c "
import json

# Lade die Dashboard-Konfiguration
with open('scripts/monitoring/simple_dashboard.py', 'r') as f:
    content = f.read()

# Aktualisiere die Pfade
content = content.replace('value=\"data/enriched/fully_enhanced.json\"', 'value=\"data/enriched/test_fully_enhanced.json\"')
content = content.replace('value=\"data/embeddings/enhanced/bookmark_embeddings.pkl\"', 'value=\"data/embeddings/test_run/bookmark_embeddings.pkl\"')

# Speichere die aktualisierte Konfiguration
with open('scripts/monitoring/simple_dashboard.py', 'w') as f:
    f.write(content)

print('Dashboard-Konfiguration aktualisiert')
"
        """
        
        if not run_command(update_dashboard_command, "Aktualisierung der Dashboard-Konfiguration"):
            logger.error("Aktualisierung der Dashboard-Konfiguration fehlgeschlagen")
            return False
        
        # Starte das Dashboard im Hintergrund
        dashboard_command = f"python -m streamlit run scripts/monitoring/simple_dashboard.py --server.port {args.dashboard_port} --server.address 0.0.0.0 > logs/dashboard.log 2>&1 &"
        
        if not run_command(dashboard_command, "Start des Dashboards"):
            logger.error("Start des Dashboards fehlgeschlagen")
            return False
        
        logger.info(f"Dashboard gestartet unter http://localhost:{args.dashboard_port}")
        logger.info(f"Log-Datei: logs/dashboard.log")
    
    # Erfolgreiche Ausführung
    logger.info("Testlauf erfolgreich abgeschlossen!")
    logger.info(f"Verarbeitete URLs: {args.limit}")
    logger.info(f"Benutze http://localhost:{args.dashboard_port} für das Dashboard")
    logger.info(f"HTML-Bericht: data/reports/test_report.html")
    
    return True

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Führt einen Testlauf der Bookmark-Pipeline aus")
    
    # Eingabedatei
    parser.add_argument("input_file", help="Pfad zur JSON-Datei mit URLs oder Lesezeichen")
    
    # Allgemeine Optionen
    parser.add_argument("--limit", type=int, default=200,
                        help="Anzahl der zu verarbeitenden URLs")
    parser.add_argument("--existing-enriched", default="data/enriched/fully_enhanced.json",
                        help="Pfad zu vorhandenen angereicherten Daten (wenn --skip-scraping verwendet wird)")
    
    # Optionen zum Überspringen von Schritten
    parser.add_argument("--skip-scraping", action="store_true",
                        help="Überspringe das Scraping mit der Zyte API")
    parser.add_argument("--skip-ai", action="store_true",
                        help="Überspringe die KI-Beschreibungsgenerierung")
    parser.add_argument("--skip-embeddings", action="store_true",
                        help="Überspringe die Generierung von Embeddings und Clustering")
    parser.add_argument("--skip-report", action="store_true",
                        help="Überspringe die Generierung des HTML-Berichts")
    parser.add_argument("--skip-dashboard", action="store_true",
                        help="Überspringe den Start des Dashboards")
    
    # Zyte API-Optionen
    parser.add_argument("--max-workers", type=int, default=3,
                        help="Maximale Anzahl gleichzeitiger Worker für das Scraping")
    parser.add_argument("--max-text-length", type=int, default=5000,
                        help="Maximale Länge des extrahierten Textes")
    
    # Embedding-Optionen
    parser.add_argument("--model", default="all-MiniLM-L6-v2",
                        help="Name des Embedding-Modells")
    parser.add_argument("--num-clusters", type=int, default=20,
                        help="Anzahl der zu generierenden Cluster")
    
    # Dashboard-Optionen
    parser.add_argument("--dashboard-port", type=int, default=8502,
                        help="Port für das Streamlit-Dashboard")
    
    args = parser.parse_args()
    
    # Führe den Testlauf aus
    if run_test_pipeline(args):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 