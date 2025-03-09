#!/usr/bin/env python3
"""
Fallback-Scraper für den Fall, dass die Zyte API nicht verfügbar ist.
Verwendet Requests und BeautifulSoup für einfaches Scraping.
"""

import json
import logging
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/fallback_scraper.log')
    ]
)
logger = logging.getLogger("fallback_scraper")

class FallbackScraper:
    """
    Einfacher Fallback-Scraper, der Requests und BeautifulSoup verwendet.
    """
    
    def __init__(self, max_workers=3, delay_min=1, delay_max=3, max_text_length=5000):
        """
        Initialisiert den Scraper.
        
        Args:
            max_workers: Maximale Anzahl gleichzeitiger Worker
            delay_min: Minimale Verzögerung zwischen Anfragen in Sekunden
            delay_max: Maximale Verzögerung zwischen Anfragen in Sekunden
            max_text_length: Maximale Länge des extrahierten Textes
        """
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
        Extrahiert den Kerninhalt einer Webseite mit Requests und BeautifulSoup.
        
        Args:
            url: URL der Webseite
            
        Returns:
            dict: Extrahierte Daten
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Anfrage an die Webseite
            response = requests.get(url, headers=headers, timeout=30)
            
            # Überprüfe den Status der Anfrage
            response.raise_for_status()
            
            # Parse HTML mit BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrahiere Titel
            title = soup.title.string if soup.title else ""
            
            # Extrahiere Meta-Beschreibung
            meta_description = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and "content" in meta_tag.attrs:
                meta_description = meta_tag["content"]
            
            # Extrahiere Keywords
            keywords = []
            keywords_tag = soup.find("meta", attrs={"name": "keywords"})
            if keywords_tag and "content" in keywords_tag.attrs:
                keywords = [k.strip() for k in keywords_tag["content"].split(",")]
            
            # Extrahiere Open Graph Daten
            og_data = {}
            for og_tag in soup.find_all("meta", property=lambda x: x and x.startswith("og:")):
                if "content" in og_tag.attrs:
                    og_property = og_tag["property"][3:]  # Entferne "og:"
                    og_data[og_property] = og_tag["content"]
            
            # Extrahiere Twitter Card Daten
            twitter_data = {}
            for twitter_tag in soup.find_all("meta", attrs={"name": lambda x: x and x.startswith("twitter:")}):
                if "content" in twitter_tag.attrs:
                    twitter_property = twitter_tag["name"][8:]  # Entferne "twitter:"
                    twitter_data[twitter_property] = twitter_tag["content"]
            
            # Extrahiere Hauptinhalt
            article_text = ""
            
            # Versuche, den Hauptartikel zu finden
            article = soup.find("article")
            if article:
                article_text = article.get_text(separator=" ", strip=True)
            else:
                # Fallback: Suche nach dem Hauptinhalt basierend auf gängigen Klassen/IDs
                content_candidates = [
                    soup.find("div", class_="content"),
                    soup.find("div", id="content"),
                    soup.find("div", class_="main"),
                    soup.find("div", id="main"),
                    soup.find("main")
                ]
                
                for candidate in content_candidates:
                    if candidate:
                        article_text = candidate.get_text(separator=" ", strip=True)
                        break
                
                # Wenn immer noch kein Inhalt gefunden wurde, verwende den Body
                if not article_text:
                    article_text = soup.body.get_text(separator=" ", strip=True) if soup.body else ""
            
            # Begrenze die Länge des Textes
            article_text = article_text[:self.max_text_length]
            
            # Extrahiere die relevanten Daten
            extracted_data = {
                "url": url,
                "title": title,
                "description": meta_description,
                "article_text": article_text,
                "open_graph": og_data,
                "twitter_card": twitter_data,
                "keywords": keywords,
                "jsonld": [],  # Nicht implementiert im Fallback-Scraper
                "scrape_time": datetime.now().isoformat()
            }
            
            return extracted_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Fehler bei der Anfrage an {url}: {str(e)}")
            self.stats['retry'] += 1
            raise
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei der Extraktion für {url}: {str(e)}")
            raise
    
    def scrape_url(self, url):
        """
        Scrapt eine einzelne URL.
        
        Args:
            url: URL zum Scrapen
            
        Returns:
            dict: Extrahierte Daten oder Fehlermeldung
        """
        try:
            logger.info(f"Scrape URL: {url}")
            result = self._extract_content(url)
            self.stats['success'] += 1
            return result
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
        Verarbeitet eine Liste von URLs parallel.
        
        Args:
            urls: Liste von URLs zum Scrapen
            output_file: Pfad zur Ausgabedatei (optional)
            limit: Maximale Anzahl zu verarbeitender URLs (optional)
            
        Returns:
            list: Liste der extrahierten Daten
        """
        if limit and limit > 0:
            urls = urls[:limit]
        
        logger.info(f"Verarbeite {len(urls)} URLs mit {self.max_workers} Workern")
        
        self.stats['start_time'] = datetime.now()
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Erstelle Future-Objekte für alle URLs
            future_to_url = {executor.submit(self.scrape_url, url): url for url in urls}
            
            # Verarbeite die Ergebnisse, sobald sie verfügbar sind
            for future in tqdm(as_completed(future_to_url), total=len(urls), desc="Scraping URLs"):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Zufällige Verzögerung zwischen Anfragen
                    time.sleep(random.uniform(self.delay_min, self.delay_max))
                except Exception as e:
                    logger.error(f"Fehler beim Verarbeiten von {url}: {str(e)}")
                    results.append({
                        "url": url,
                        "error": str(e),
                        "scrape_time": datetime.now().isoformat()
                    })
        
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info(f"Scraping abgeschlossen in {duration:.1f} Sekunden")
        logger.info(f"Erfolgsrate: {self.stats['success'] / len(urls) * 100:.1f}% ({self.stats['success']}/{len(urls)})")
        logger.info(f"Verarbeitet: {len(urls)} URLs, Erfolgreich: {self.stats['success']}, Fehlgeschlagen: {self.stats['error']}")
        
        # Speichere die Ergebnisse in einer Datei, falls angegeben
        if output_file:
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Ergebnisse gespeichert in {output_file}")
        
        return results

def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fallback-Scraper für Webseiten")
    
    # Eingabedatei
    parser.add_argument("input_file", help="Pfad zur JSON-Datei mit URLs oder Lesezeichen")
    
    # Ausgabedatei
    parser.add_argument("--output-file", "-o", default="data/enriched/fallback_enriched.json",
                        help="Pfad zur Ausgabedatei")
    
    # Optionen
    parser.add_argument("--limit", "-l", type=int, default=None,
                        help="Maximale Anzahl zu verarbeitender URLs")
    parser.add_argument("--max-workers", "-w", type=int, default=3,
                        help="Maximale Anzahl gleichzeitiger Worker")
    parser.add_argument("--delay-min", type=float, default=1.0,
                        help="Minimale Verzögerung zwischen Anfragen in Sekunden")
    parser.add_argument("--delay-max", type=float, default=3.0,
                        help="Maximale Verzögerung zwischen Anfragen in Sekunden")
    parser.add_argument("--max-text-length", type=int, default=5000,
                        help="Maximale Länge des extrahierten Textes")
    
    args = parser.parse_args()
    
    # Lade URLs aus der Eingabedatei
    with open(args.input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extrahiere URLs aus den Daten
    urls = []
    if isinstance(data, list):
        if all(isinstance(item, str) for item in data):
            # Liste von URLs
            urls = data
        elif all(isinstance(item, dict) for item in data):
            # Liste von Objekten mit URL-Feld
            for item in data:
                if "url" in item:
                    urls.append(item["url"])
    
    if not urls:
        logger.error(f"Keine URLs in der Eingabedatei {args.input_file} gefunden")
        sys.exit(1)
    
    logger.info(f"Gefunden: {len(urls)} URLs in {args.input_file}")
    
    # Initialisiere den Scraper
    scraper = FallbackScraper(
        max_workers=args.max_workers,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        max_text_length=args.max_text_length
    )
    
    # Verarbeite die URLs
    scraper.process_urls(urls, output_file=args.output_file, limit=args.limit)

if __name__ == "__main__":
    main() 