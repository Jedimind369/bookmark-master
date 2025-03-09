#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Angepasste Version des Hybrid-Scrapers, die Daten direkt in die SQLite-Datenbank speichert.
"""

import os
import sys
import json
import time
import gzip
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Füge das Projektverzeichnis zum Pfad hinzu
sys.path.append(str(Path(__file__).parent.parent.parent))

# Importiere den Hybrid-Scraper und die Datenbankmodule
from scripts.scraping.hybrid_scraper import HybridScraper
from scripts.database.db_operations import BookmarkDB
from scripts.database.init_db import init_database

# Konfiguriere Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DBHybridScraper(HybridScraper):
    """
    Erweiterte Version des Hybrid-Scrapers mit Datenbankunterstützung.
    """
    
    def __init__(self, db_path="data/database/bookmarks.db", **kwargs):
        """
        Initialisiert den DB-Hybrid-Scraper.
        
        Args:
            db_path: Pfad zur SQLite-Datenbank
            **kwargs: Weitere Parameter für den Hybrid-Scraper
        """
        super().__init__(**kwargs)
        
        # Initialisiere die Datenbank
        init_database(db_path)
        self.db = BookmarkDB(db_path)
        self.db_path = db_path
        
        logger.info(f"DB-Hybrid-Scraper initialisiert mit Datenbank: {db_path}")
    
    def process_urls(self, urls, output_file=None, batch_size=100, **kwargs):
        """
        Verarbeitet mehrere URLs und speichert die Ergebnisse in der Datenbank.
        
        Args:
            urls: Liste von URLs oder Liste von Bookmark-Dictionaries
            output_file: Pfad zur Ausgabedatei (optional, für Kompatibilität)
            batch_size: Größe der Batches für die Verarbeitung
            **kwargs: Weitere Parameter für process_urls des Basis-Scrapers
            
        Returns:
            list: Liste der Ergebnisse
        """
        # Extrahiere URLs aus Bookmarks, falls nötig
        processed_urls = []
        bookmark_data = {}
        
        for item in urls:
            if isinstance(item, dict) and 'url' in item:
                url = item['url']
                bookmark_data[url] = item
                processed_urls.append(url)
            else:
                processed_urls.append(item)
        
        # Verarbeite URLs mit dem Basis-Scraper
        results = super().process_urls(processed_urls, output_file, batch_size=batch_size, **kwargs)
        
        # Speichere die Ergebnisse in der Datenbank
        if results:
            saved_count = 0
            for result in results:
                url = result.get('url')
                
                # Füge Bookmark-Daten hinzu, falls vorhanden
                if url in bookmark_data:
                    for key, value in bookmark_data[url].items():
                        if key not in result and key != 'url':
                            result[key] = value
                
                # Speichere in der Datenbank
                if self.db.save_page(result):
                    saved_count += 1
            
            logger.info(f"{saved_count} von {len(results)} Ergebnissen erfolgreich in der Datenbank gespeichert")
        
        return results
    
    def extract_content(self, url):
        """
        Extrahiert den Inhalt einer Webseite und prüft zuerst in der Datenbank.
        
        Args:
            url: URL der Webseite
            
        Returns:
            dict: Extrahierte Daten oder None bei Fehler
        """
        # Prüfe, ob die URL bereits in der Datenbank ist
        page_data = self.db.get_page(url)
        if page_data:
            logger.info(f"URL {url} bereits in der Datenbank vorhanden, überspringe Scraping")
            self.stats['cached'] += 1
            return page_data
        
        # Falls nicht in der Datenbank, extrahiere den Inhalt
        result = super().extract_content(url)
        
        # Speichere das Ergebnis in der Datenbank, falls erfolgreich
        if result:
            self.db.save_page(result)
        
        return result

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Hybrid-Scraper mit Datenbankunterstützung")
    parser.add_argument("--input", required=True, help="Eingabe-JSON-Datei mit URLs")
    parser.add_argument("--output", help="Ausgabe-JSON-Datei für die Ergebnisse (optional)")
    parser.add_argument("--db-path", default="data/database/bookmarks.db", help="Pfad zur SQLite-Datenbank")
    parser.add_argument("--limit", type=int, help="Maximale Anzahl an URLs zum Scrapen")
    parser.add_argument("--max-workers", type=int, default=5, help="Maximale Anzahl an Worker-Threads")
    parser.add_argument("--max-text-length", type=int, default=5000, help="Maximale Länge des extrahierten Textes")
    parser.add_argument("--dynamic-threshold", type=float, default=0.3, help="Schwellenwert für dynamische Inhalte (0-1)")
    parser.add_argument("--scrapingbee-credits", type=int, default=10, help="Durchschnittliche Anzahl an Credits pro Anfrage")
    parser.add_argument("--scrapingbee-cost", type=float, default=0.00097, help="Kosten pro Credit in USD")
    parser.add_argument("--budget", type=float, default=20.0, help="Maximales Budget in USD")
    parser.add_argument("--cache-dir", default="data/cache", help="Verzeichnis für den Cache")
    parser.add_argument("--no-cache", action="store_true", help="Deaktiviert den Cache")
    parser.add_argument("--clear-cache", action="store_true", help="Löscht den Cache vor dem Start")
    parser.add_argument("--batch-size", type=int, default=100, help="Größe der Batches für die Verarbeitung")
    parser.add_argument("--resume", action="store_true", help="Setzt die Verarbeitung fort, wenn Batch-Dateien existieren")
    parser.add_argument("--skip-existing", action="store_true", help="Überspringe URLs, die bereits in der Datenbank sind")
    args = parser.parse_args()
    
    # Lade URLs aus der Eingabedatei
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extrahiere URLs oder Bookmark-Objekte
    items = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'url' in item:
                items.append(item)
            elif isinstance(item, str):
                items.append(item)
    elif isinstance(data, dict) and 'bookmarks' in data:
        for bookmark in data['bookmarks']:
            if isinstance(bookmark, dict) and 'url' in bookmark:
                items.append(bookmark)
    
    # Begrenze die Anzahl der Items, wenn ein Limit angegeben wurde
    if args.limit and args.limit > 0:
        items = items[:args.limit]
    
    # Cache-Verzeichnis
    cache_dir = args.cache_dir
    if args.no_cache:
        cache_dir = None
    elif args.clear_cache and os.path.exists(args.cache_dir):
        logger.info(f"Lösche Cache-Verzeichnis: {args.cache_dir}")
        import shutil
        shutil.rmtree(args.cache_dir)
        os.makedirs(args.cache_dir, exist_ok=True)
    
    # Berechne geschätzte Kosten
    estimated_cost = len(items) * args.scrapingbee_credits * args.scrapingbee_cost
    logger.info(f"Geschätzte Kosten für {len(items)} URLs: ${estimated_cost:.2f}")
    
    # Prüfe Budget
    if args.budget and estimated_cost > args.budget:
        logger.warning(f"Geschätzte Kosten (${estimated_cost:.2f}) überschreiten das Budget (${args.budget:.2f})!")
        if input("Möchten Sie trotzdem fortfahren? (j/n): ").lower() != 'j':
            logger.info("Abbruch durch Benutzer.")
            sys.exit(0)
    
    # Initialisiere den DB-Hybrid-Scraper
    scraper = DBHybridScraper(
        db_path=args.db_path,
        scrapingbee_key=os.getenv("SCRAPINGBEE_API_KEY", ""),
        smartproxy_url=os.getenv("SMARTPROXY_URL", ""),
        max_workers=args.max_workers,
        max_text_length=args.max_text_length,
        dynamic_threshold=args.dynamic_threshold,
        scrapingbee_credits_per_request=args.scrapingbee_credits,
        scrapingbee_cost_per_credit=args.scrapingbee_cost,
        budget_limit=args.budget,
        cache_dir=cache_dir
    )
    
    # Wenn skip_existing aktiviert ist, filtere URLs, die bereits in der Datenbank sind
    if args.skip_existing:
        db = BookmarkDB(args.db_path)
        filtered_items = []
        for item in items:
            url = item if isinstance(item, str) else item.get('url')
            if not db.get_page(url):
                filtered_items.append(item)
        
        logger.info(f"{len(items) - len(filtered_items)} URLs übersprungen, da bereits in der Datenbank")
        items = filtered_items
    
    # Verarbeite die URLs/Bookmarks
    results = scraper.process_urls(items, args.output, batch_size=args.batch_size)
    
    # Zeige Statistiken
    logger.info(f"Scraping abgeschlossen in {scraper.stats['elapsed_time']:.1f} Sekunden")
    logger.info(f"Erfolgsrate: {scraper.stats['success'] / max(scraper.stats['total'], 1) * 100:.1f}% ({scraper.stats['success']}/{scraper.stats['total']})")
    logger.info(f"ScrapingBee: {scraper.stats['scrapingbee_used']}, Smartproxy: {scraper.stats['smartproxy_used']}, Fallback: {scraper.stats['fallback_used']}, Cache: {scraper.stats['cached']}")
    logger.info(f"Geschätzte Kosten: ${scraper.stats['estimated_cost']:.2f}")
    
    if scraper.stats['budget_limit_reached']:
        logger.warning(f"Budget-Limit von ${args.budget:.2f} erreicht. Einige URLs wurden übersprungen.")

if __name__ == "__main__":
    main() 