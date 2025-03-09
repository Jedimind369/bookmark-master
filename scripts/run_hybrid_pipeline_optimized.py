#!/usr/bin/env python3
"""
Optimierte Version des run_hybrid_pipeline.py Skripts.

Orchestriert einen Testlauf mit dem hybriden Scraper und anschließender KI-Veredelung.
Verwendet den Chunk-Prozessor für optimierte Speichernutzung und Parallelverarbeitung.

Der Prozess umfasst:
1. Extraktion des Kerninhalts mit dem optimierten hybriden Scraper
2. KI-basierte Generierung von hochwertigen Beschreibungen mit optimierter Verarbeitung
3. Semantische Analyse mit Embeddings und Clustering
4. Generierung eines HTML-Berichts mit optimierter Verarbeitung
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
    
    logger.info("Verzeichnisse erstellt")

def run_command(command, description):
    """
    Führt einen Befehl aus und gibt zurück, ob er erfolgreich war.
    
    Args:
        command: Auszuführender Befehl
        description: Beschreibung des Befehls für Logging
        
    Returns:
        bool: True, wenn der Befehl erfolgreich war, sonst False
    """
    logger.info(f"Führe aus: {description}")
    logger.debug(f"Befehl: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"{description} erfolgreich abgeschlossen")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"{description} fehlgeschlagen: {e}")
        logger.error(f"Ausgabe: {e.stdout}")
        logger.error(f"Fehler: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"{description} fehlgeschlagen mit unerwarteter Ausnahme: {str(e)}")
        return False

def check_scraping_success(output_file):
    """
    Überprüft, ob das Scraping erfolgreich war, indem die Ausgabedatei geprüft wird.
    
    Args:
        output_file: Pfad zur Ausgabedatei
        
    Returns:
        bool: True, wenn das Scraping erfolgreich war, sonst False
    """
    try:
        # Prüfe, ob die Datei existiert
        if not os.path.exists(output_file):
            logger.error(f"Ausgabedatei nicht gefunden: {output_file}")
            return False
        
        # Prüfe, ob die Datei Inhalt hat
        if os.path.getsize(output_file) == 0:
            logger.error(f"Ausgabedatei ist leer: {output_file}")
            return False
        
        # Prüfe, ob die Datei gültiges JSON enthält
        try:
            if output_file.endswith('.gz'):
                with gzip.open(output_file, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Prüfe, ob Daten vorhanden sind
            if not data:
                logger.error(f"Keine Daten in der Ausgabedatei: {output_file}")
                return False
            
            # Prüfe, ob die Daten das erwartete Format haben
            if not isinstance(data, list):
                logger.error(f"Unerwartetes Datenformat in der Ausgabedatei: {output_file}")
                return False
            
            # Prüfe, ob mindestens ein Eintrag vorhanden ist
            if len(data) == 0:
                logger.error(f"Keine Einträge in der Ausgabedatei: {output_file}")
                return False
            
            # Prüfe, ob die Einträge die erwarteten Felder haben
            for entry in data:
                if not isinstance(entry, dict):
                    logger.error(f"Unerwartetes Eintragsformat in der Ausgabedatei: {output_file}")
                    return False
                
                if 'url' not in entry or 'content' not in entry:
                    logger.error(f"Fehlende Felder in der Ausgabedatei: {output_file}")
                    return False
            
            logger.info(f"Ausgabedatei erfolgreich validiert: {output_file} ({len(data)} Einträge)")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Ungültiges JSON in der Ausgabedatei: {output_file} - {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"Fehler bei der Überprüfung der Ausgabedatei: {output_file} - {str(e)}")
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
        # Verwende den optimierten hybriden Scraper
        hybrid_command = (
            f"python scripts/scraping/hybrid_scraper_optimized.py --input {args.input_file} "
            f"--output {hybrid_output_file} --limit {args.limit} --max-workers {args.max_workers} "
            f"--max-text-length {args.max_text_length} --dynamic-threshold {args.dynamic_threshold} "
            f"--min-chunk-size {args.min_chunk_size} --max-chunk-size {args.max_chunk_size} "
            f"--memory-target {args.memory_target}"
        )
        
        if args.scrapingbee_key:
            hybrid_command += f" --scrapingbee-key {args.scrapingbee_key}"
        
        if args.smartproxy_url:
            hybrid_command += f" --smartproxy-url {args.smartproxy_url}"
        
        hybrid_success = run_command(hybrid_command, "Optimierter Hybrider Scraper")
        
        # Überprüfe, ob das Scraping tatsächlich erfolgreich war
        if hybrid_success and os.path.exists(hybrid_output_file):
            hybrid_success = check_scraping_success(hybrid_output_file)
        
        if not hybrid_success:
            logger.error("Optimierter Hybrider Scraper fehlgeschlagen")
            return False
    
    # Schritt 2: KI-basierte Generierung von hochwertigen Beschreibungen
    logger.info("SCHRITT 2: KI-basierte Generierung von hochwertigen Beschreibungen")
    
    ai_output_file = "data/enriched/hybrid_fully_enhanced.json.gz"
    ai_command = (
        f"python scripts/ai/enhanced_descriptions_optimized.py {hybrid_output_file} "
        f"--output-file {ai_output_file} --max-workers {args.max_workers} "
        f"--min-chunk-size {args.min_chunk_size} --max-chunk-size {args.max_chunk_size} "
        f"--memory-target {args.memory_target}"
    )
    
    if not run_command(ai_command, "Optimierte KI-Beschreibungsgenerierung"):
        logger.error("Optimierte KI-Beschreibungsgenerierung fehlgeschlagen")
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
    report_command = (
        f"python scripts/export/simple_html_report_optimized.py {ai_output_file} {report_file} "
        f"--max-workers {args.max_workers} --min-chunk-size {args.min_chunk_size} "
        f"--max-chunk-size {args.max_chunk_size} --memory-target {args.memory_target}"
    )
    
    if not run_command(report_command, "Optimierte Generierung des HTML-Berichts"):
        logger.error("Optimierte Generierung des HTML-Berichts fehlgeschlagen")
        return False
    
    # Schritt 5: Generierung eines semantischen HTML-Berichts
    logger.info("SCHRITT 5: Generierung eines semantischen HTML-Berichts")
    
    semantic_report_file = "data/reports/hybrid_semantic_report.html"
    semantic_report_command = f"python scripts/export/generate_semantic_html_report.py {ai_output_file} data/embeddings/hybrid_run {semantic_report_file}"
    
    if not run_command(semantic_report_command, "Generierung des semantischen HTML-Berichts"):
        logger.error("Generierung des semantischen HTML-Berichts fehlgeschlagen")
        return False
    
    logger.info("Pipeline erfolgreich abgeschlossen")
    logger.info(f"Ergebnisse:")
    logger.info(f"- Angereicherte Daten: {hybrid_output_file}")
    logger.info(f"- Vollständig angereicherte Daten: {ai_output_file}")
    logger.info(f"- Embeddings und Clustering: data/embeddings/hybrid_run")
    logger.info(f"- HTML-Bericht: {report_file}")
    logger.info(f"- Semantischer HTML-Bericht: {semantic_report_file}")
    
    return True

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Optimierte Hybrid-Pipeline für Lesezeichen")
    parser.add_argument("--input-file", required=True, help="Pfad zur Eingabedatei mit URLs")
    parser.add_argument("--limit", type=int, default=10, help="Maximale Anzahl zu verarbeitender URLs")
    parser.add_argument("--max-workers", type=int, default=2, help="Maximale Anzahl paralleler Worker-Threads")
    parser.add_argument("--max-text-length", type=int, default=10000, help="Maximale Länge des extrahierten Textes")
    parser.add_argument("--dynamic-threshold", type=float, default=0.7, help="Schwellenwert für die Erkennung dynamischer Inhalte")
    parser.add_argument("--num-clusters", type=int, default=5, help="Anzahl der Cluster für die semantische Analyse")
    parser.add_argument("--skip-scraping", action="store_true", help="Überspringe das Scraping und verwende vorhandene Daten")
    parser.add_argument("--existing-enriched", help="Pfad zu vorhandenen angereicherten Daten (nur mit --skip-scraping)")
    parser.add_argument("--scrapingbee-key", help="API-Schlüssel für ScrapingBee")
    parser.add_argument("--smartproxy-url", help="URL für Smartproxy")
    parser.add_argument("--min-chunk-size", type=int, default=50, help="Minimale Chunk-Größe in KB")
    parser.add_argument("--max-chunk-size", type=int, default=10000, help="Maximale Chunk-Größe in KB")
    parser.add_argument("--memory-target", type=float, default=0.7, help="Ziel-Speicherauslastung (0.0-1.0)")
    args = parser.parse_args()
    
    # Validiere Argumente
    if args.skip_scraping and not args.existing_enriched:
        parser.error("--existing-enriched ist erforderlich, wenn --skip-scraping angegeben ist")
    
    # Führe die Pipeline aus
    success = run_hybrid_pipeline(args)
    
    # Beende mit entsprechendem Exit-Code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 