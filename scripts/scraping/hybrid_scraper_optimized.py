#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Optimierter Hybrider Scraper für Webseiten.

Diese Version verwendet den Chunk-Prozessor für optimierte Speichernutzung und Parallelverarbeitung.
Der Scraper kombiniert verschiedene Scraping-Methoden:
1. ScrapingBee für dynamische Inhalte
2. Smartproxy für statische Inhalte
3. Fallback-Scraper für einfache Inhalte

Die Auswahl des Scrapers erfolgt automatisch basierend auf der URL und dem Inhalt.
"""

import os
import sys
import json
import time
import gzip
import random
import logging
import requests
import argparse
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path
import base64
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
import hashlib

# Füge das übergeordnete Verzeichnis zum Pfad hinzu, um den Chunk-Prozessor zu importieren
sys.path.append(str(Path(__file__).parent.parent.parent))
from scripts.processing.pipeline_integration import PipelineIntegration

# Konfiguriere Logger
logger = logging.getLogger(__name__)

# Lade Umgebungsvariablen aus .env-Datei
load_dotenv()

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/hybrid_scraper.log"),
        logging.StreamHandler()
    ]
)

class HybridScraper:
    """
    Optimierter Hybrider Scraper für Webseiten.
    Verwendet den Chunk-Prozessor für optimierte Speichernutzung und Parallelverarbeitung.
    """
    
    def __init__(self, scrapingbee_key=None, smartproxy_url=None, max_workers=2, 
                 max_text_length=10000, dynamic_threshold=0.7, budget_limit=5.0,
                 min_chunk_size=50, max_chunk_size=10000, memory_target_percentage=0.7):
        """
        Initialisiert den Hybriden Scraper.
        
        Args:
            scrapingbee_key: API-Schlüssel für ScrapingBee
            smartproxy_url: URL für Smartproxy
            max_workers: Maximale Anzahl paralleler Worker-Threads
            max_text_length: Maximale Länge des extrahierten Textes
            dynamic_threshold: Schwellenwert für die Erkennung dynamischer Inhalte
            budget_limit: Budget-Limit in USD
            min_chunk_size: Minimale Chunk-Größe in KB
            max_chunk_size: Maximale Chunk-Größe in KB
            memory_target_percentage: Ziel-Speicherauslastung (0.0-1.0)
        """
        self.scrapingbee_key = scrapingbee_key or os.getenv("SCRAPINGBEE_API_KEY")
        self.smartproxy_url = smartproxy_url or os.getenv("SMARTPROXY_URL")
        self.max_workers = max_workers
        self.max_text_length = max_text_length
        self.dynamic_threshold = dynamic_threshold
        self.budget_limit = budget_limit
        
        # Erstelle Pipeline-Integration
        self.pipeline = PipelineIntegration(
            max_workers=max_workers,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
            memory_target_percentage=memory_target_percentage
        )
        
        # Setze Callbacks
        self.pipeline.set_callbacks(
            progress_callback=self._progress_callback,
            status_callback=self._status_callback,
            error_callback=self._error_callback,
            complete_callback=self._complete_callback
        )
        
        # Initialisiere Statistiken
        self.stats = {
            'start_time': None,
            'elapsed_time': 0,
            'total': 0,
            'processed': 0,
            'success': 0,
            'failed': 0,
            'scrapingbee_used': 0,
            'smartproxy_used': 0,
            'fallback_used': 0,
            'budget_limit_reached': False,
            'total_cost': 0.0
        }
        
        # Konstanten für ScrapingBee
        self.scrapingbee_credits_per_request = 10  # Durchschnittliche Anzahl Credits pro Anfrage
        self.scrapingbee_cost_per_credit = 0.001   # Kosten pro Credit in USD
        
        # Cache für bereits verarbeitete URLs
        self.cache_dir = Path("data/scraping") / datetime.now().strftime("%Y-%m-%d") / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Verzeichnis für Ergebnisse
        self.results_dir = Path("data/scraping") / datetime.now().strftime("%Y-%m-%d") / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Hybrider Scraper initialisiert mit {max_workers} Workern")
        logger.info(f"ScrapingBee API-Key: {'Vorhanden' if self.scrapingbee_key else 'Nicht vorhanden'}")
        logger.info(f"Smartproxy URL: {'Vorhanden' if self.smartproxy_url else 'Nicht vorhanden'}")
    
    def _progress_callback(self, progress, stats):
        """Callback für Fortschrittsupdates."""
        self.stats['processed'] = stats.get('processed_chunks', 0)
        logger.info(f"Fortschritt: {progress:.1%} ({self.stats['processed']}/{self.stats['total']} URLs)")
    
    def _status_callback(self, status, stats):
        """Callback für Statusupdates."""
        logger.info(f"Status: {status}")
    
    def _error_callback(self, message, exception):
        """Callback für Fehlerbehandlung."""
        logger.error(f"Fehler: {message} - {str(exception)}")
        self.stats['failed'] += 1
    
    def _complete_callback(self, stats):
        """Callback für Abschluss."""
        self.stats['elapsed_time'] = stats.get('end_time', 0) - stats.get('start_time', 0)
        logger.info(f"Verarbeitung abgeschlossen in {self.stats['elapsed_time']:.2f} Sekunden")
        logger.info(f"Erfolgreiche Extraktion: {self.stats['success']}/{self.stats['total']} URLs")
        logger.info(f"Fehlgeschlagene Extraktion: {self.stats['failed']}/{self.stats['total']} URLs")
        logger.info(f"ScrapingBee verwendet: {self.stats['scrapingbee_used']} mal")
        logger.info(f"Smartproxy verwendet: {self.stats['smartproxy_used']} mal")
        logger.info(f"Fallback verwendet: {self.stats['fallback_used']} mal")
        logger.info(f"Gesamtkosten: ${self.stats['total_cost']:.2f}")
    
    def _get_cache_path(self, url):
        """
        Generiert einen Pfad für die Cache-Datei basierend auf der URL.
        
        Args:
            url: URL
            
        Returns:
            Path: Pfad zur Cache-Datei
        """
        # Generiere einen Hash der URL für den Dateinamen
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.json"
    
    def _get_result_path(self, url_index):
        """
        Generiert einen Pfad für die Ergebnisdatei basierend auf dem URL-Index.
        
        Args:
            url_index: Index der URL
            
        Returns:
            Path: Pfad zur Ergebnisdatei
        """
        return self.results_dir / f"result_url_{url_index}.json"
    
    def _is_cached(self, url):
        """
        Prüft, ob eine URL bereits im Cache ist.
        
        Args:
            url: URL
            
        Returns:
            bool: True, wenn die URL im Cache ist, sonst False
        """
        cache_path = self._get_cache_path(url)
        return cache_path.exists()
    
    def _get_from_cache(self, url):
        """
        Holt das Ergebnis für eine URL aus dem Cache.
        
        Args:
            url: URL
            
        Returns:
            dict: Ergebnis aus dem Cache oder None, wenn nicht im Cache
        """
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Fehler beim Laden aus dem Cache für {url}: {str(e)}")
        return None
    
    def _save_to_cache(self, url, result):
        """
        Speichert das Ergebnis für eine URL im Cache.
        
        Args:
            url: URL
            result: Ergebnis
        """
        cache_path = self._get_cache_path(url)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern im Cache für {url}: {str(e)}")
    
    def _extract_with_scrapingbee(self, url):
        """
        Extrahiert den Inhalt einer Webseite mit ScrapingBee.
        
        Args:
            url: URL
            
        Returns:
            dict: Extrahierter Inhalt oder None bei Fehler
        """
        if not self.scrapingbee_key:
            logger.warning("ScrapingBee API-Key nicht vorhanden")
            return None
        
        try:
            # Prüfe Budget-Limit
            estimated_cost = self.scrapingbee_credits_per_request * self.scrapingbee_cost_per_credit
            if self.stats['total_cost'] + estimated_cost > self.budget_limit:
                logger.warning(f"Budget-Limit erreicht. Überspringe ScrapingBee für {url}")
                self.stats['budget_limit_reached'] = True
                return None
            
            # Erstelle ScrapingBee API-URL
            api_url = f"https://app.scrapingbee.com/api/v1/"
            params = {
                'api_key': self.scrapingbee_key,
                'url': url,
                'render_js': 'true',
                'premium_proxy': 'true',
                'extract_rules': json.dumps({
                    'title': 'title',
                    'body': 'body'
                })
            }
            
            # Sende Anfrage
            response = requests.get(api_url, params=params)
            
            # Aktualisiere Statistiken
            self.stats['scrapingbee_used'] += 1
            self.stats['total_cost'] += estimated_cost
            
            # Prüfe Antwort
            if response.status_code == 200:
                try:
                    data = response.json()
                    return {
                        'url': url,
                        'title': data.get('title', ''),
                        'content': data.get('body', ''),
                        'method': 'scrapingbee',
                        'status': 'success',
                        'timestamp': datetime.now().isoformat()
                    }
                except Exception as e:
                    logger.error(f"Fehler beim Parsen der ScrapingBee-Antwort für {url}: {str(e)}")
            else:
                logger.error(f"ScrapingBee-Anfrage fehlgeschlagen für {url}: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Fehler bei ScrapingBee für {url}: {str(e)}")
        
        return None
    
    def _extract_with_smartproxy(self, url):
        """
        Extrahiert den Inhalt einer Webseite mit Smartproxy.
        
        Args:
            url: URL
            
        Returns:
            dict: Extrahierter Inhalt oder None bei Fehler
        """
        if not self.smartproxy_url:
            logger.warning("Smartproxy URL nicht vorhanden")
            return None
        
        try:
            # Erstelle Smartproxy API-URL
            api_url = self.smartproxy_url
            payload = {
                'url': url,
                'parse': True
            }
            
            # Sende Anfrage
            response = requests.post(api_url, json=payload)
            
            # Aktualisiere Statistiken
            self.stats['smartproxy_used'] += 1
            
            # Prüfe Antwort
            if response.status_code == 200:
                try:
                    data = response.json()
                    return {
                        'url': url,
                        'title': data.get('title', ''),
                        'content': data.get('content', ''),
                        'method': 'smartproxy',
                        'status': 'success',
                        'timestamp': datetime.now().isoformat()
                    }
                except Exception as e:
                    logger.error(f"Fehler beim Parsen der Smartproxy-Antwort für {url}: {str(e)}")
            else:
                logger.error(f"Smartproxy-Anfrage fehlgeschlagen für {url}: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Fehler bei Smartproxy für {url}: {str(e)}")
        
        return None
    
    def _extract_with_fallback(self, url):
        """
        Extrahiert den Inhalt einer Webseite mit dem Fallback-Scraper.
        
        Args:
            url: URL
            
        Returns:
            dict: Extrahierter Inhalt oder None bei Fehler
        """
        try:
            # Sende Anfrage
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            # Aktualisiere Statistiken
            self.stats['fallback_used'] += 1
            
            # Prüfe Antwort
            if response.status_code == 200:
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extrahiere Titel
                title = soup.title.text if soup.title else ''
                
                # Extrahiere Text
                paragraphs = soup.find_all('p')
                content = ' '.join([p.text for p in paragraphs])
                
                # Begrenze Textlänge
                if len(content) > self.max_text_length:
                    content = content[:self.max_text_length] + '...'
                
                return {
                    'url': url,
                    'title': title,
                    'content': content,
                    'method': 'fallback',
                    'status': 'success',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.error(f"Fallback-Anfrage fehlgeschlagen für {url}: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Fehler bei Fallback für {url}: {str(e)}")
        
        return None
    
    def extract_content(self, url):
        """
        Extrahiert den Inhalt einer Webseite mit dem am besten geeigneten Scraper.
        
        Args:
            url: URL
            
        Returns:
            dict: Extrahierter Inhalt oder Fehlermeldung
        """
        logger.info(f"Extrahiere Inhalt von {url}")
        
        # Prüfe, ob die URL bereits im Cache ist
        if self._is_cached(url):
            logger.info(f"Verwende Cache für {url}")
            result = self._get_from_cache(url)
            if result:
                return result
        
        # Versuche, den Inhalt mit verschiedenen Scrapern zu extrahieren
        result = None
        
        # 1. Versuche ScrapingBee für dynamische Inhalte
        if self.scrapingbee_key and not self.stats['budget_limit_reached']:
            result = self._extract_with_scrapingbee(url)
        
        # 2. Versuche Smartproxy für statische Inhalte, wenn ScrapingBee fehlgeschlagen ist
        if not result and self.smartproxy_url:
            result = self._extract_with_smartproxy(url)
        
        # 3. Versuche Fallback-Scraper, wenn beide fehlgeschlagen sind
        if not result:
            result = self._extract_with_fallback(url)
        
        # Wenn alle Scraper fehlgeschlagen sind, erstelle eine Fehlermeldung
        if not result:
            result = {
                'url': url,
                'title': '',
                'content': '',
                'method': 'none',
                'status': 'failed',
                'error': 'Alle Scraper fehlgeschlagen',
                'timestamp': datetime.now().isoformat()
            }
            self.stats['failed'] += 1
        else:
            self.stats['success'] += 1
        
        # Speichere das Ergebnis im Cache
        self._save_to_cache(url, result)
        
        return result
    
    def process_urls(self, urls, output_file=None, limit=None, compress=True, batch_size=100):
        """
        Verarbeitet mehrere URLs parallel und speichert die Ergebnisse.
        Verwendet den Chunk-Prozessor für optimierte Speichernutzung und Parallelverarbeitung.
        
        Args:
            urls: Liste von URLs
            output_file: Pfad zur Ausgabedatei
            limit: Maximale Anzahl zu verarbeitender URLs
            compress: Ob die Ausgabedatei komprimiert werden soll
            batch_size: Größe der Batches für die Verarbeitung
            
        Returns:
            list: Liste der Ergebnisse
        """
        # Aktualisiere Statistiken
        self.stats['start_time'] = time.time()
        
        # Begrenze die Anzahl der URLs, wenn ein Limit angegeben wurde
        if limit and limit < len(urls):
            logger.info(f"Begrenze auf {limit} URLs (von {len(urls)})")
            urls = urls[:limit]
        
        self.stats['total'] = len(urls)
        
        # Berechne geschätzte Kosten
        estimated_cost = len(urls) * self.scrapingbee_credits_per_request * self.scrapingbee_cost_per_credit
        logger.info(f"Geschätzte Kosten für {len(urls)} URLs: ${estimated_cost:.2f}")
        
        # Prüfe Budget-Limit
        if estimated_cost > self.budget_limit:
            logger.warning(f"Geschätzte Kosten (${estimated_cost:.2f}) überschreiten das Budget-Limit (${self.budget_limit:.2f})!")
            # Berechne, wie viele URLs wir mit dem Budget verarbeiten können
            max_urls = int(self.budget_limit / (self.scrapingbee_credits_per_request * self.scrapingbee_cost_per_credit))
            logger.info(f"Begrenze auf {max_urls} URLs, um im Budget zu bleiben")
            urls = urls[:max_urls]
            self.stats['total'] = len(urls)
        
        logger.info(f"Verarbeite {len(urls)} URLs mit {self.max_workers} Workern")
        
        # Verarbeite URLs mit dem Chunk-Prozessor
        results = self.pipeline.process_url_list(
            urls=urls,
            processor_func=self.extract_content,
            output_file=output_file,
            compress=compress,
            batch_size=batch_size
        )
        
        # Aktualisiere Statistiken
        self.stats['elapsed_time'] = time.time() - self.stats['start_time']
        
        return results
    
    def shutdown(self):
        """Fährt den Scraper herunter."""
        self.pipeline.shutdown()


def load_urls(file_path):
    """
    Lädt URLs aus einer Datei.
    
    Args:
        file_path: Pfad zur Datei
        
    Returns:
        list: Liste von URLs
    """
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith('#'):
                    urls.append(url)
        logger.info(f"Geladen: {len(urls)} URLs aus {file_path}")
    except Exception as e:
        logger.error(f"Fehler beim Laden der URLs: {str(e)}")
    return urls


def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Optimierter Hybrider Scraper für Webseiten")
    parser.add_argument("--input", required=True, help="Pfad zur Eingabedatei mit URLs")
    parser.add_argument("--output", required=True, help="Pfad zur Ausgabedatei")
    parser.add_argument("--limit", type=int, default=None, help="Maximale Anzahl zu verarbeitender URLs")
    parser.add_argument("--max-workers", type=int, default=2, help="Maximale Anzahl paralleler Worker-Threads")
    parser.add_argument("--max-text-length", type=int, default=10000, help="Maximale Länge des extrahierten Textes")
    parser.add_argument("--dynamic-threshold", type=float, default=0.7, help="Schwellenwert für die Erkennung dynamischer Inhalte")
    parser.add_argument("--budget-limit", type=float, default=5.0, help="Budget-Limit in USD")
    parser.add_argument("--scrapingbee-key", help="API-Schlüssel für ScrapingBee")
    parser.add_argument("--smartproxy-url", help="URL für Smartproxy")
    parser.add_argument("--min-chunk-size", type=int, default=50, help="Minimale Chunk-Größe in KB")
    parser.add_argument("--max-chunk-size", type=int, default=10000, help="Maximale Chunk-Größe in KB")
    parser.add_argument("--memory-target", type=float, default=0.7, help="Ziel-Speicherauslastung (0.0-1.0)")
    parser.add_argument("--batch-size", type=int, default=100, help="Größe der Batches für die Verarbeitung")
    args = parser.parse_args()
    
    # Erstelle Verzeichnisse
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Lade URLs
    urls = load_urls(args.input)
    if not urls:
        logger.error("Keine URLs gefunden")
        return 1
    
    # Erstelle Scraper
    scraper = HybridScraper(
        scrapingbee_key=args.scrapingbee_key,
        smartproxy_url=args.smartproxy_url,
        max_workers=args.max_workers,
        max_text_length=args.max_text_length,
        dynamic_threshold=args.dynamic_threshold,
        budget_limit=args.budget_limit,
        min_chunk_size=args.min_chunk_size,
        max_chunk_size=args.max_chunk_size,
        memory_target_percentage=args.memory_target
    )
    
    try:
        # Verarbeite URLs
        results = scraper.process_urls(
            urls=urls,
            output_file=args.output,
            limit=args.limit,
            compress=args.output.endswith('.gz'),
            batch_size=args.batch_size
        )
        
        # Zeige Statistiken
        logger.info(f"Verarbeitung abgeschlossen in {scraper.stats['elapsed_time']:.2f} Sekunden")
        logger.info(f"Erfolgreiche Extraktion: {scraper.stats['success']}/{scraper.stats['total']} URLs")
        logger.info(f"Fehlgeschlagene Extraktion: {scraper.stats['failed']}/{scraper.stats['total']} URLs")
        logger.info(f"ScrapingBee verwendet: {scraper.stats['scrapingbee_used']} mal")
        logger.info(f"Smartproxy verwendet: {scraper.stats['smartproxy_used']} mal")
        logger.info(f"Fallback verwendet: {scraper.stats['fallback_used']} mal")
        logger.info(f"Gesamtkosten: ${scraper.stats['total_cost']:.2f}")
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("Abbruch durch Benutzer")
        return 130
    
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {str(e)}", exc_info=True)
        return 1
    
    finally:
        # Fahre Scraper herunter
        scraper.shutdown()


if __name__ == "__main__":
    sys.exit(main()) 