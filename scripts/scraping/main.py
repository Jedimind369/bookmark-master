#!/usr/bin/env python3

"""
main.py

Hauptskript zur Verarbeitung von URLs mit dem Zyte Scraper und dem Content Analyzer.
"""

import os
import sys
import json
import argparse
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Lokale Imports
from .zyte_scraper import ZyteScraper, scrape_urls
from .content_analyzer import ContentAnalyzer
from .settings import DATA_DIR, LOG_DIR

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "main.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("main")

async def process_urls(urls: List[str], api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Verarbeitet eine Liste von URLs: Scrapt sie mit der Zyte API und analysiert den Inhalt.
    
    Args:
        urls: Liste von URLs
        api_key: Zyte API-Schlüssel (optional)
        
    Returns:
        Statistiken über den Prozess
    """
    # Schritt 1: Scrape URLs
    logger.info(f"Starte Scraping von {len(urls)} URLs")
    scraper = ZyteScraper(api_key)
    scrape_stats = await scraper.scrape_urls(urls)
    
    logger.info(f"Scraping abgeschlossen. Erfolgreich: {scrape_stats['successful']}, Fehlgeschlagen: {scrape_stats['failed']}")
    
    # Schritt 2: Analysiere gescrapte Inhalte
    if scrape_stats['successful'] > 0:
        logger.info(f"Starte Analyse der gescrapten Inhalte")
        analyzer = ContentAnalyzer()
        analyze_stats = await asyncio.create_task(analyzer.analyze_all_scraped_files())
        
        logger.info(f"Analyse abgeschlossen. Erfolgreich: {analyze_stats['successful']}, Fehlgeschlagen: {analyze_stats['failed']}")
        
        # Gesamtstatistik
        total_stats = {
            "urls_processed": len(urls),
            "scraping": scrape_stats,
            "analysis": analyze_stats,
            "total_success_rate": (analyze_stats['successful'] / len(urls)) * 100 if len(urls) > 0 else 0,
            "total_cost": analyze_stats.get('total_cost', 0.0)
        }
        
        # Ausgabe der Statistik
        logger.info(f"Gesamtprozess abgeschlossen. Erfolgsrate: {total_stats['total_success_rate']:.1f}%")
        logger.info(f"Gesamtkosten: ${total_stats['total_cost']:.2f}")
        
        return total_stats
    else:
        logger.warning("Keine URLs erfolgreich gescrapt, überspringe Analyse.")
        return {"error": "Keine URLs erfolgreich gescrapt"}

def load_urls_from_file(filepath: Path) -> List[str]:
    """
    Lädt URLs aus einer Datei.
    
    Args:
        filepath: Pfad zur Datei mit URLs (eine URL pro Zeile)
        
    Returns:
        Liste von URLs
    """
    if not filepath.exists():
        logger.error(f"Datei nicht gefunden: {filepath}")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Geladen: {len(urls)} URLs aus {filepath}")
    return urls

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Scraping und Analyse von URLs mit Zyte API")
    
    # Definiere Argumente
    parser.add_argument("--urls", nargs="+", help="Eine oder mehrere URLs zum Verarbeiten")
    parser.add_argument("--file", help="Pfad zu einer Datei mit URLs (eine URL pro Zeile)")
    parser.add_argument("--api-key", help="Zyte API-Schlüssel (falls nicht in Umgebungsvariable)")
    parser.add_argument("--analyze-only", action="store_true", help="Nur Analyse durchführen, kein Scraping")
    
    args = parser.parse_args()
    
    # Überprüfe Argumente
    if not args.urls and not args.file and not args.analyze_only:
        parser.error("Entweder --urls oder --file oder --analyze-only muss angegeben werden")
    
    # Sammle URLs
    urls = []
    if args.urls:
        urls.extend(args.urls)
    
    if args.file:
        file_urls = load_urls_from_file(Path(args.file))
        urls.extend(file_urls)
    
    # Führe Verarbeitung durch
    if args.analyze_only:
        # Nur Analyse durchführen
        logger.info("Nur Analyse der vorhandenen gescrapten Dateien wird durchgeführt")
        analyzer = ContentAnalyzer()
        stats = analyzer.analyze_all_scraped_files()
        logger.info(f"Analyse abgeschlossen. Erfolgreich: {stats['successful']}, Fehlgeschlagen: {stats['failed']}")
    else:
        # Scraping und Analyse durchführen
        asyncio.run(process_urls(urls, args.api_key))

# Beispiel-URLs für Tests
EXAMPLE_URLS = [
    "https://www.wikipedia.org",
    "https://www.python.org",
    "https://github.com",
    "https://www.openai.com",
    "https://streamlit.io"
]

if __name__ == "__main__":
    # Wenn keine Argumente übergeben wurden, verwende Beispiel-URLs
    if len(sys.argv) == 1:
        logger.info("Keine Argumente übergeben, verwende Beispiel-URLs")
        asyncio.run(process_urls(EXAMPLE_URLS))
    else:
        main() 