#!/usr/bin/env python3
"""
Optimierter Scraper, der die Zyte API für effiziente Extraktion von Kerninhalten verwendet.
Fokus liegt auf Ressourcen- und Kostenoptimierung durch gezielte Extraktion.
"""

import os
import json
import time
import random
import sys
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import requests

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/zyte_scraper.log')
    ]
)
logger = logging.getLogger("zyte_scraper")

class OptimizedZyteScraper:
    """
    Optimierter Scraper, der die Zyte API für effiziente Extraktion von Kerninhalten verwendet.
    """
    
    def __init__(self, api_key=None, max_workers=3, delay_min=1, delay_max=3, max_text_length=5000):
        """
        Initialisiert den Scraper.
        
        Args:
            api_key: Zyte API-Schlüssel (aus Umgebungsvariable, falls nicht angegeben)
            max_workers: Maximale Anzahl gleichzeitiger Worker
            delay_min: Minimale Verzögerung zwischen Anfragen in Sekunden
            delay_max: Maximale Verzögerung zwischen Anfragen in Sekunden
            max_text_length: Maximale Länge des extrahierten Textes
        """
        self.api_key = api_key or os.environ.get("ZYTE_API_KEY")
        if not self.api_key:
            logger.warning("Kein Zyte API-Schlüssel gefunden. Setze die Umgebungsvariable ZYTE_API_KEY oder übergib den Schlüssel als Parameter.")
        
        self.max_workers = max_workers
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_text_length = max_text_length
        
        # Statistiken
        self.stats = {
            'success': 0,
            'error': 0,
            'retry': 0,
            'start_time': None,
            'end_time': None
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _extract_content(self, url):
        """
        Extrahiert den Kerninhalt einer Webseite mit der Zyte API.
        
        Args:
            url: URL der Webseite
            
        Returns:
            dict: Extrahierte Daten
        """
        try:
            # Konfiguration für die Zyte API
            # Optimiert für geringe Speicher- und Netzwerknutzung
            payload = {
                "url": url,
                "browserHtml": False,  # Kein vollständiges HTML benötigt
                "article": True,       # Extrahiere den Hauptartikel
                "extractFrom": {
                    "article": {
                        "text": True,
                        "html": False, # Kein HTML benötigt, nur Text
                        "links": False # Keine Links extrahieren
                    }
                },
                "meta": True,          # Meta-Daten extrahieren
                "customData": {
                    "extractAlt": True,
                    "maxTextLength": self.max_text_length
                },
                "screenshot": False,    # Kein Screenshot benötigt
                "experimental": {
                    "jsonld": True      # JSON-LD strukturierte Daten extrahieren
                },
                # Optimierte Browser-Einstellungen für weniger Ressourcenverbrauch
                "browser": {
                    "renderJs": True,
                    "javascript": True,
                    "headers": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    },
                    "loadImages": False,    # Keine Bilder laden
                    "blockAds": True,       # Werbung blockieren
                    "blockMedia": True      # Medien blockieren
                }
            }
            
            # Anfrage an die Zyte API
            response = requests.post(
                "https://api.zyte.com/v1/extract",
                auth=(self.api_key, ""),
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Überprüfe den Status der Anfrage
            response.raise_for_status()
            
            # Verarbeite die Antwort
            result = response.json()
            
            # Extrahiere die relevanten Daten
            extracted_data = {
                "url": url,
                "title": result.get("meta", {}).get("title", ""),
                "description": result.get("meta", {}).get("description", ""),
                "article_text": result.get("article", {}).get("text", "")[:self.max_text_length] if result.get("article", {}).get("text") else "",
                "open_graph": result.get("meta", {}).get("og", {}),
                "twitter_card": result.get("meta", {}).get("twitter", {}),
                "keywords": result.get("meta", {}).get("keywords", []),
                "jsonld": result.get("experimental", {}).get("jsonld", []),
                "scrape_time": datetime.now().isoformat()
            }
            
            return extracted_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Fehler bei der Anfrage an die Zyte API für {url}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status Code: {e.response.status_code}")
                logger.error(f"Response Text: {e.response.text}")
            self.stats['retry'] += 1
            raise
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei der Extraktion für {url}: {str(e)}")
            raise
    
    def scrape_url(self, url):
        """
        Scraped eine URL mit der Zyte API.
        
        Args:
            url: URL zum Scrapen
            
        Returns:
            dict: Gescrapte Daten oder Fehlerinformation
        """
        # Zufällige Verzögerung, um Rate-Limiting zu vermeiden
        delay = random.uniform(self.delay_min, self.delay_max)
        time.sleep(delay)
        
        try:
            # Extrahiere den Inhalt
            extracted_data = self._extract_content(url)
            self.stats['success'] += 1
            return extracted_data
        except Exception as e:
            logger.error(f"Fehler beim Scrapen von {url}: {str(e)}")
            self.stats['error'] += 1
            return {
                "url": url,
                "error": str(e),
                "scrape_time": datetime.now().isoformat()
            }
    
    def process_urls(self, urls, output_file=None, limit=None):
        """
        Verarbeitet eine Liste von URLs in Batches.
        
        Args:
            urls: Liste von URLs oder Pfad zu einer JSON-Datei mit URLs
            output_file: Pfad zur Ausgabe-JSON-Datei
            limit: Maximale Anzahl von URLs zum Verarbeiten
        
        Returns:
            list: Gescrapte Daten
        """
        # Lade URLs, falls eine Datei angegeben wurde
        if isinstance(urls, str):
            try:
                with open(urls, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Unterstütze verschiedene Formate (Liste von URLs oder Liste von Objekten mit URL-Feld)
                if isinstance(data, list):
                    if len(data) > 0:
                        if isinstance(data[0], str):
                            # Liste von URLs
                            urls = data
                        elif isinstance(data[0], dict) and 'url' in data[0]:
                            # Liste von Objekten mit URL-Feld
                            urls = [item['url'] for item in data]
                        else:
                            raise ValueError("Unbekanntes Datenformat in der Eingabedatei")
                    else:
                        urls = []
                else:
                    raise ValueError("Die Eingabedatei muss eine Liste enthalten")
            except Exception as e:
                logger.error(f"Fehler beim Laden der URLs aus {urls}: {str(e)}")
                return []
        
        # Begrenze die Anzahl der URLs, falls angegeben
        if limit is not None and limit > 0:
            urls = urls[:limit]
        
        logger.info(f"Verarbeite {len(urls)} URLs mit {self.max_workers} Workern")
        
        # Starte die Zeitmessung
        self.stats['start_time'] = time.time()
        
        # Verarbeite URLs mit einem ThreadPoolExecutor
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Starte die Verarbeitung mit Progress-Bar
            for result in tqdm(executor.map(self.scrape_url, urls), total=len(urls), desc="Scraping URLs"):
                results.append(result)
        
        # Beende die Zeitmessung
        self.stats['end_time'] = time.time()
        duration = self.stats['end_time'] - self.stats['start_time']
        
        # Logge Statistiken
        logger.info(f"Scraping abgeschlossen in {duration:.1f} Sekunden")
        logger.info(f"Erfolgsrate: {self.stats['success']/len(urls)*100:.1f}% ({self.stats['success']}/{len(urls)})")
        logger.info(f"Verarbeitet: {len(urls)} URLs, Erfolgreich: {self.stats['success']}, Fehlgeschlagen: {self.stats['error']}")
        
        # Speichere die Ergebnisse, falls eine Ausgabedatei angegeben wurde
        if output_file:
            # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Ergebnisse gespeichert in {output_file}")
        
        return results

def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimierter Scraper für die Zyte API")
    parser.add_argument("input_file", help="Pfad zur JSON-Datei mit URLs oder Lesezeichen")
    parser.add_argument("--output-file", default="data/enriched/zyte_enriched.json",
                        help="Pfad zur Ausgabe-JSON-Datei")
    parser.add_argument("--max-workers", type=int, default=3,
                        help="Maximale Anzahl gleichzeitiger Worker")
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximale Anzahl von URLs zum Verarbeiten")
    parser.add_argument("--api-key", default=None,
                        help="Zyte API-Schlüssel (verwendet Umgebungsvariable ZYTE_API_KEY, falls nicht angegeben)")
    parser.add_argument("--max-text-length", type=int, default=5000,
                        help="Maximale Länge des extrahierten Textes")
    
    args = parser.parse_args()
    
    # Initialisiere den Scraper
    scraper = OptimizedZyteScraper(
        api_key=args.api_key,
        max_workers=args.max_workers,
        max_text_length=args.max_text_length
    )
    
    # Verarbeite URLs
    scraper.process_urls(args.input_file, args.output_file, args.limit)

if __name__ == "__main__":
    main() 