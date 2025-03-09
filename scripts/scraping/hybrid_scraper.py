#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hybrider Scraper für Webseiten.

Dieser Scraper kombiniert verschiedene Scraping-Methoden:
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

# Konfiguriere Logger
logger = logging.getLogger(__name__)

# Lade Umgebungsvariablen aus .env-Datei
load_dotenv()

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Konfiguriere Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HybridScraper:
    """
    Hybrider Scraper, der verschiedene Scraping-Methoden kombiniert.
    """
    
    def __init__(self, scrapingbee_key="", smartproxy_url="", max_workers=5, 
                 max_text_length=5000, dynamic_threshold=0.3,
                 scrapingbee_credits_per_request=10, scrapingbee_cost_per_credit=0.00097,
                 budget_limit=20.0, cache_dir="data/cache"):
        """
        Initialisiert den Hybrid-Scraper.
        
        Args:
            scrapingbee_key: API-Schlüssel für ScrapingBee
            smartproxy_url: URL für Smartproxy (optional)
            max_workers: Maximale Anzahl an Worker-Threads
            max_text_length: Maximale Länge des extrahierten Textes
            dynamic_threshold: Schwellenwert für dynamische Inhalte (0-1)
            scrapingbee_credits_per_request: Durchschnittliche Anzahl an Credits pro Anfrage
            scrapingbee_cost_per_credit: Kosten pro Credit in USD
            budget_limit: Maximales Budget in USD
            cache_dir: Verzeichnis für den Cache
        """
        # Konfiguriere Logger
        self.logger = logging.getLogger(__name__)
        
        # Speichere Konfiguration
        self.scrapingbee_key = scrapingbee_key
        self.smartproxy_url = smartproxy_url
        self.max_workers = max_workers
        self.max_text_length = max_text_length
        self.dynamic_threshold = dynamic_threshold
        self.budget_limit = budget_limit
        self.cache_dir = cache_dir
        
        # Erstelle Cache-Verzeichnis, falls es nicht existiert
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Kosten pro Anfrage (in USD)
        self.scrapingbee_cost_per_credit = scrapingbee_cost_per_credit
        self.scrapingbee_credits_per_request = scrapingbee_credits_per_request
        
        # Initialisiere Statistiken
        self.stats = {
            'total': 0,
            'success': 0,
            'failure': 0,
            'retry': 0,
            'scrapingbee_used': 0,
            'smartproxy_used': 0,
            'fallback_used': 0,
            'cached': 0,
            'estimated_cost': 0.0,
            'start_time': time.time(),
            'elapsed_time': 0,
            'budget_limit_reached': False
        }
        
        # Logge Konfiguration
        self.logger.info(f"Hybrid-Scraper initialisiert mit:")
        self.logger.info(f"  ScrapingBee API-Key: {'Vorhanden' if self.scrapingbee_key else 'Nicht konfiguriert'}")
        self.logger.info(f"  Smartproxy URL: {'Vorhanden' if self.smartproxy_url else 'Nicht konfiguriert'}")
        self.logger.info(f"  Max Workers: {self.max_workers}")
        self.logger.info(f"  Max Text Length: {self.max_text_length}")
        self.logger.info(f"  ScrapingBee Credits pro Anfrage: {self.scrapingbee_credits_per_request}")
        self.logger.info(f"  ScrapingBee Kosten pro Credit: ${self.scrapingbee_cost_per_credit}")
        self.logger.info(f"  Budget-Limit: ${self.budget_limit}")
        self.logger.info(f"  Cache-Verzeichnis: {self.cache_dir}")
        
        # Kosten pro Anfrage
        self.scrapingbee_cost_per_request = 10  # Credits pro Anfrage (durchschnittlich)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_with_scrapingbee(self, url):
        """
        Extrahiert den Inhalt einer Webseite mit ScrapingBee.
        
        Args:
            url: URL der Webseite
            
        Returns:
            dict: Extrahierte Daten
        """
        try:
            self.logger.info(f"Verwende ScrapingBee für {url}")
            
            # Konfiguriere ScrapingBee-Parameter
            params = {
                'api_key': self.scrapingbee_key,
                'url': url,
                'premium_proxy': 'true',
                'country_code': 'us',
                'render_js': 'true'
            }
            
            # Anfrage an ScrapingBee
            response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, timeout=60)
            response.raise_for_status()
            
            # Aktualisiere Statistiken
            self.stats['scrapingbee_used'] += 1
            
            # Parse HTML mit BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return self._extract_content_from_soup(soup, url, scraper_name="scrapingbee")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fehler bei der Anfrage mit ScrapingBee für {url}: {str(e)}")
            self.stats['retry'] += 1
            raise
        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler bei ScrapingBee für {url}: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_with_smartproxy(self, url):
        """
        Extrahiert Inhalte mit Smartproxy.
        """
        self.logger.info(f"Verwende Smartproxy für {url}")
        
        try:
            # Parse Smartproxy URL to extract credentials
            parsed_proxy = urlparse(self.smartproxy_url)
            proxy_host = parsed_proxy.hostname
            proxy_port = parsed_proxy.port
            proxy_user = parsed_proxy.username
            proxy_pass = parsed_proxy.password
            
            # Erstelle Proxy-URL ohne Authentifizierung
            proxy_url = f"http://{proxy_host}:{proxy_port}"
            
            # Konfiguriere Proxies und Authentifizierung
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # Konfiguriere Authentifizierung
            auth = requests.auth.HTTPProxyAuth(proxy_user, proxy_pass)
            
            # Konfiguriere Headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Direkter Zugriff auf die Webseite über den Proxy
            response = requests.get(
                url,
                proxies=proxies,
                auth=auth,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()  # Raise exception for non-200 status codes
            
            # Update statistics
            self.stats['smartproxy_used'] += 1
            
            soup = BeautifulSoup(response.text, 'html.parser')
            return self._extract_content_from_soup(soup, url, scraper_name="smartproxy")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fehler bei der Anfrage mit Smartproxy für {url}: {str(e)}")
            self.stats['retry'] += 1
            raise
        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler bei Smartproxy für {url}: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_with_fallback(self, url):
        """
        Extrahiert den Inhalt einer Webseite mit dem Fallback-Scraper.
        
        Args:
            url: URL der Webseite
            
        Returns:
            dict: Extrahierte Daten
        """
        try:
            self.logger.info(f"Verwende Fallback-Scraper für {url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Anfrage an die Webseite
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Aktualisiere Statistiken
            self.stats['fallback_used'] += 1
            
            # Parse HTML mit BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            return self._extract_content_from_soup(soup, url, scraper_name="fallback")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fehler bei der Anfrage mit Fallback-Scraper für {url}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler bei Fallback-Scraper für {url}: {str(e)}")
            return None
    
    def _is_dynamic_content(self, url):
        """
        Prüft, ob eine URL dynamischen Inhalt hat.
        
        Args:
            url: URL der Webseite
            
        Returns:
            bool: True, wenn die URL dynamischen Inhalt hat, sonst False
        """
        # Liste von Domains, die typischerweise dynamischen Inhalt haben
        dynamic_domains = [
            "twitter.com", "x.com", "facebook.com", "instagram.com", 
            "linkedin.com", "youtube.com", "vimeo.com", "tiktok.com",
            "reddit.com", "quora.com", "pinterest.com", "tumblr.com",
            "medium.com", "dev.to", "hashnode.com", "substack.com",
            "producthunt.com", "indiegogo.com", "kickstarter.com",
            "shopify.com", "etsy.com", "amazon.com", "ebay.com",
            "airbnb.com", "booking.com", "expedia.com", "tripadvisor.com",
            "yelp.com", "doordash.com", "ubereats.com", "grubhub.com",
            "netflix.com", "hulu.com", "disneyplus.com", "hbomax.com",
            "spotify.com", "soundcloud.com", "apple.com", "microsoft.com",
            "google.com", "yahoo.com", "bing.com", "duckduckgo.com",
            "github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com",
            "news.ycombinator.com", "slashdot.org", "techcrunch.com",
            "theverge.com", "wired.com", "engadget.com", "mashable.com",
            "cnn.com", "bbc.com", "nytimes.com", "wsj.com", "bloomberg.com",
            "forbes.com", "economist.com", "ft.com", "reuters.com",
            "apnews.com", "npr.org", "washingtonpost.com", "latimes.com",
            "theguardian.com", "independent.co.uk", "telegraph.co.uk",
            "mail.google.com", "outlook.com", "yahoo.mail.com", "protonmail.com",
            "slack.com", "discord.com", "zoom.us", "meet.google.com",
            "teams.microsoft.com", "webex.com", "notion.so", "trello.com",
            "asana.com", "monday.com", "clickup.com", "todoist.com",
            "evernote.com", "onenote.com", "dropbox.com", "box.com",
            "drive.google.com", "onedrive.live.com", "icloud.com",
            "figma.com", "sketch.com", "adobe.com", "canva.com",
            "miro.com", "invisionapp.com", "framer.com", "webflow.com",
            "squarespace.com", "wix.com", "wordpress.com", "hubspot.com",
            "salesforce.com", "zendesk.com", "intercom.com", "drift.com",
            "stripe.com", "paypal.com", "square.com", "shopify.com",
            "coinbase.com", "binance.com", "kraken.com", "gemini.com",
            "robinhood.com", "etrade.com", "tdameritrade.com", "schwab.com",
            "fidelity.com", "vanguard.com", "chase.com", "bankofamerica.com",
            "wellsfargo.com", "citibank.com", "capitalone.com", "discover.com",
            "amex.com", "visa.com", "mastercard.com", "venmo.com",
            "cashapp.com", "zelle.com", "wise.com", "revolut.com",
            "chime.com", "ally.com", "sofi.com", "marcus.com",
            "betterment.com", "wealthfront.com", "acorns.com", "stash.com",
            "mint.com", "ynab.com", "personalcapital.com", "creditkarma.com",
            "experian.com", "equifax.com", "transunion.com", "annualcreditreport.com"
        ]
        
        # Liste von Dateiendungen, die typischerweise statischen Inhalt haben
        static_extensions = [
            ".html", ".htm", ".xml", ".pdf", ".txt", ".md", ".csv", 
            ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", 
            ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp", 
            ".mp3", ".wav", ".ogg", ".mp4", ".webm", ".avi", ".mov", 
            ".zip", ".tar", ".gz", ".rar", ".7z", ".doc", ".docx", 
            ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp"
        ]
        
        # Prüfe, ob die URL eine statische Dateiendung hat
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        for ext in static_extensions:
            if path.endswith(ext):
                return False
        
        # Prüfe, ob die Domain in der Liste der dynamischen Domains ist
        domain = parsed_url.netloc.lower()
        for dynamic_domain in dynamic_domains:
            if dynamic_domain in domain:
                return True
        
        # Wenn wir nicht sicher sind, verwenden wir den Schwellenwert
        # Je höher der Schwellenwert, desto mehr URLs werden als dynamisch eingestuft
        return random.random() < self.dynamic_threshold
    
    def _get_cache_path(self, url):
        """
        Generiert einen Cache-Pfad für eine URL.
        
        Args:
            url: URL der Webseite
            
        Returns:
            str: Pfad zur Cache-Datei
        """
        # Generiere einen eindeutigen Dateinamen basierend auf der URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")
    
    def _is_cached(self, url):
        """
        Prüft, ob eine URL im Cache ist.
        
        Args:
            url: URL der Webseite
            
        Returns:
            bool: True, wenn die URL im Cache ist, sonst False
        """
        cache_path = self._get_cache_path(url)
        return os.path.exists(cache_path)
    
    def _get_from_cache(self, url):
        """
        Holt Daten aus dem Cache.
        
        Args:
            url: URL der Webseite
            
        Returns:
            dict: Daten aus dem Cache oder None, wenn nicht im Cache
        """
        cache_path = self._get_cache_path(url)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.stats['cached'] += 1
                self.logger.info(f"Aus Cache geladen: {url}")
                return data
            except Exception as e:
                self.logger.error(f"Fehler beim Laden aus dem Cache für {url}: {str(e)}")
        return None
    
    def _save_to_cache(self, url, data):
        """
        Speichert Daten im Cache.
        
        Args:
            url: URL der Webseite
            data: Daten zum Speichern
        """
        cache_path = self._get_cache_path(url)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            self.logger.info(f"Im Cache gespeichert: {url}")
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern im Cache für {url}: {str(e)}")
    
    def extract_content(self, url):
        """
        Extrahiert den Inhalt einer Webseite mit der am besten geeigneten Methode.
        
        Args:
            url: URL der Webseite
            
        Returns:
            dict: Extrahierte Daten oder None bei Fehler
        """
        # Prüfe Budget-Limit
        if self.stats['estimated_cost'] >= self.budget_limit:
            self.stats['budget_limit_reached'] = True
            self.logger.warning(f"Budget-Limit von ${self.budget_limit} erreicht. Überspringe {url}")
            return None
            
        try:
            # Prüfe Cache
            cached_data = self._get_from_cache(url)
            if cached_data:
                return cached_data
                
            # Primär ScrapingBee verwenden, wenn API-Schlüssel vorhanden ist
            if self.scrapingbee_key:
                try:
                    result = self.extract_with_scrapingbee(url)
                    self.stats['success'] += 1
                    # Aktualisiere die geschätzten Kosten
                    self.stats['estimated_cost'] += self.scrapingbee_cost_per_credit * self.scrapingbee_credits_per_request
                    # Speichere im Cache
                    self._save_to_cache(url, result)
                    return result
                except Exception as e:
                    self.logger.warning(f"ScrapingBee fehlgeschlagen für {url}, versuche Fallback: {str(e)}")
            
            # Fallback-Scraper als letzte Option
            result = self.extract_with_fallback(url)
            if result:
                self.stats['success'] += 1
                # Speichere im Cache
                self._save_to_cache(url, result)
                return result
            else:
                self.stats['failure'] += 1
                self.logger.error(f"Alle Scraper fehlgeschlagen für {url}")
                return None
                
        except Exception as e:
            self.stats['failure'] += 1
            self.logger.error(f"Unerwarteter Fehler beim Scraping von {url}: {str(e)}")
            return None
    
    def process_urls(self, urls, output_file=None, limit=None, compress=True, batch_size=100):
        """
        Verarbeitet mehrere URLs parallel und speichert die Ergebnisse.
        
        Args:
            urls: Liste von URLs
            output_file: Pfad zur Ausgabedatei
            limit: Maximale Anzahl zu verarbeitender URLs (wird nicht mehr verwendet, da das Limit bereits in der main-Funktion angewendet wird)
            compress: Ob die Ausgabedatei komprimiert werden soll
            batch_size: Größe der Batches für die Verarbeitung
            
        Returns:
            list: Liste der Ergebnisse
        """
        # Aktualisiere Statistiken
        self.stats['start_time'] = time.time()
        self.stats['total'] = len(urls)
        
        # Begrenze die Anzahl der URLs, wenn ein Limit angegeben wurde
        # Entfernt, da das Limit bereits in der main-Funktion angewendet wird
        
        # Berechne geschätzte Kosten
        estimated_cost = len(urls) * self.scrapingbee_credits_per_request * self.scrapingbee_cost_per_credit
        self.logger.info(f"Geschätzte Kosten für {len(urls)} URLs: ${estimated_cost:.2f}")
        
        # Prüfe Budget-Limit
        if estimated_cost > self.budget_limit:
            self.logger.warning(f"Geschätzte Kosten (${estimated_cost:.2f}) überschreiten das Budget-Limit (${self.budget_limit:.2f})!")
            # Berechne, wie viele URLs wir mit dem Budget verarbeiten können
            max_urls = int(self.budget_limit / (self.scrapingbee_credits_per_request * self.scrapingbee_cost_per_credit))
            self.logger.info(f"Begrenze auf {max_urls} URLs, um im Budget zu bleiben")
            urls = urls[:max_urls]
            self.stats['total'] = len(urls)
        
        self.logger.info(f"Verarbeite {len(urls)} URLs mit {self.max_workers} Workern")
        
        # Priorisiere URLs basierend auf Domain-Popularität und Cache-Status
        prioritized_urls = self._prioritize_urls(urls)
        
        # Verarbeite URLs in Batches
        all_results = []
        batch_count = (len(prioritized_urls) + batch_size - 1) // batch_size  # Ceiling division
        
        for batch_index in range(batch_count):
            start_idx = batch_index * batch_size
            end_idx = min(start_idx + batch_size, len(prioritized_urls))
            batch_urls = prioritized_urls[start_idx:end_idx]
            
            self.logger.info(f"Verarbeite Batch {batch_index + 1}/{batch_count} mit {len(batch_urls)} URLs")
            
            batch_results = self._process_batch(batch_urls)
            all_results.extend(batch_results)
            
            # Speichere Zwischenergebnisse, wenn eine Ausgabedatei angegeben wurde
            if output_file:
                batch_output_file = self._get_batch_output_file(output_file, batch_index)
                self._save_results(all_results, batch_output_file, compress)
                self.logger.info(f"Zwischenergebnisse gespeichert in {batch_output_file}")
            
            # Prüfe Budget-Limit
            if self.stats['budget_limit_reached']:
                self.logger.warning(f"Budget-Limit erreicht. Breche Verarbeitung ab.")
                break
        
        # Aktualisiere Statistiken
        self.stats['elapsed_time'] = time.time() - self.stats['start_time']
        
        # Speichere die Ergebnisse, wenn eine Ausgabedatei angegeben wurde
        if output_file and all_results:
            self._save_results(all_results, output_file, compress)
        
        return all_results
    
    def _process_batch(self, urls):
        """
        Verarbeitet einen Batch von URLs parallel.
        
        Args:
            urls: Liste von URLs
            
        Returns:
            list: Liste der Ergebnisse
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Erstelle Future-Objekte für alle URLs
            future_to_url = {executor.submit(self.extract_content, url): url for url in urls}
            
            # Verarbeite die Ergebnisse, sobald sie verfügbar sind
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        self.logger.info(f"Erfolgreich verarbeitet: {url} mit {result.get('scraper_used', 'unbekannt')}")
                    else:
                        self.logger.error(f"Fehler beim Verarbeiten von {url}")
                        
                    # Prüfe Budget-Limit
                    if self.stats['budget_limit_reached']:
                        self.logger.warning(f"Budget-Limit erreicht. Breche Batch-Verarbeitung ab.")
                        break
                except Exception as e:
                    self.logger.error(f"Fehler beim Verarbeiten von {url}: {str(e)}")
        
        return results
    
    def _get_batch_output_file(self, output_file, batch_index):
        """
        Generiert einen Dateinamen für Batch-Zwischenergebnisse.
        
        Args:
            output_file: Pfad zur Ausgabedatei
            batch_index: Index des Batches
            
        Returns:
            str: Pfad zur Batch-Ausgabedatei
        """
        # Berücksichtige den Batch-Start-Index aus der Umgebungsvariable
        batch_start_index = int(os.environ.get('BATCH_START_INDEX', '0'))
        batch_index = batch_start_index + batch_index
        
        # Extrahiere Dateinamen und Erweiterung
        base, ext = os.path.splitext(output_file)
        if ext == '.gz':
            base, inner_ext = os.path.splitext(base)
            return f"{base}_batch{batch_index}{inner_ext}.gz"
        else:
            return f"{base}_batch{batch_index}{ext}"
    
    def _prioritize_urls(self, urls):
        """
        Priorisiert URLs basierend auf Domain-Popularität und Cache-Status.
        
        Args:
            urls: Liste von URLs
            
        Returns:
            list: Priorisierte Liste von URLs
        """
        # Prüfe, welche URLs bereits im Cache sind
        cached_urls = [url for url in urls if self._is_cached(url)]
        non_cached_urls = [url for url in urls if url not in cached_urls]
        
        # Liste von populären Domains, die oft dynamischen Inhalt haben
        popular_domains = [
            "github.com", "stackoverflow.com", "medium.com", "dev.to", 
            "twitter.com", "linkedin.com", "facebook.com", "youtube.com",
            "reddit.com", "news.ycombinator.com", "producthunt.com"
        ]
        
        # Sortiere nicht-gecachte URLs nach Popularität
        def domain_priority(url):
            domain = urlparse(url).netloc
            for i, pop_domain in enumerate(popular_domains):
                if pop_domain in domain:
                    return i
            return len(popular_domains)
        
        sorted_non_cached = sorted(non_cached_urls, key=domain_priority)
        
        # Kombiniere gecachte und nicht-gecachte URLs
        # Gecachte URLs haben höchste Priorität, da sie keine Kosten verursachen
        return cached_urls + sorted_non_cached
    
    def _save_results(self, results, output_file, compress=True):
        """
        Speichert die Ergebnisse in einer Datei.
        
        Args:
            results: Liste der Ergebnisse
            output_file: Pfad zur Ausgabedatei
            compress: Ob die Ausgabedatei komprimiert werden soll
        """
        # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Speichere die Ergebnisse
        if compress or output_file.endswith('.gz'):
            with gzip.open(output_file, 'wt', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Ergebnisse komprimiert gespeichert in {output_file}")
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Ergebnisse gespeichert in {output_file}")

    def _extract_content_from_soup(self, soup, url, scraper_name="fallback"):
        """
        Extrahiert Inhalte aus einer BeautifulSoup-Instanz.
        
        Args:
            soup: BeautifulSoup-Instanz
            url: URL der Webseite
            scraper_name: Name des verwendeten Scrapers
            
        Returns:
            dict: Extrahierte Daten
        """
        # Extrahiere Titel
        title = soup.title.string if soup.title else ""
        
        # Extrahiere Meta-Beschreibung
        meta_description = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and "content" in meta_tag.attrs:
            meta_description = meta_tag["content"]
        
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
            "scrape_time": datetime.now().isoformat(),
            "scraper_used": scraper_name
        }
        
        return extracted_data

def main():
    """Hauptfunktion."""
    # Lade Umgebungsvariablen
    load_dotenv()
    
    # Konfiguriere Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/hybrid_scraper.log")
        ]
    )
    
    # Parse Kommandozeilenargumente
    parser = argparse.ArgumentParser(description="Hybrid-Scraper für Webseiten")
    parser.add_argument("--input", required=True, help="Eingabe-JSON-Datei mit URLs")
    parser.add_argument("--output", required=True, help="Ausgabe-JSON-Datei für die Ergebnisse")
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
    args = parser.parse_args()
    
    # Lade URLs aus der Eingabedatei
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extrahiere URLs aus den Bookmarks
    urls = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'url' in item:
                urls.append(item['url'])
    elif isinstance(data, dict) and 'bookmarks' in data:
        for bookmark in data['bookmarks']:
            if isinstance(bookmark, dict) and 'url' in bookmark:
                urls.append(bookmark['url'])
    
    # Begrenze die Anzahl der URLs, wenn ein Limit angegeben wurde
    if args.limit and args.limit > 0:
        urls = urls[:args.limit]
    
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
    estimated_cost = len(urls) * args.scrapingbee_credits * args.scrapingbee_cost
    logger.info(f"Geschätzte Kosten für {len(urls)} URLs: ${estimated_cost:.2f}")
    
    # Prüfe Budget
    if args.budget and estimated_cost > args.budget:
        logger.warning(f"Geschätzte Kosten (${estimated_cost:.2f}) überschreiten das Budget (${args.budget:.2f})!")
        if input("Möchten Sie trotzdem fortfahren? (j/n): ").lower() != 'j':
            logger.info("Abbruch durch Benutzer.")
            sys.exit(0)
    
    # Initialisiere den Scraper
    scraper = HybridScraper(
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
    
    # Prüfe, ob wir die Verarbeitung fortsetzen sollen
    if args.resume:
        # Suche nach der letzten Batch-Datei
        base, ext = os.path.splitext(args.output)
        if ext == '.gz':
            base, inner_ext = os.path.splitext(base)
            pattern = f"{base}_batch*{inner_ext}.gz"
        else:
            pattern = f"{base}_batch*{ext}"
        
        import glob
        batch_files = sorted(glob.glob(pattern))
        
        if batch_files:
            # Lade die letzte Batch-Datei
            last_batch_file = batch_files[-1]
            logger.info(f"Setze Verarbeitung fort mit {last_batch_file}")
            
            # Extrahiere Batch-Index
            import re
            match = re.search(r'_batch(\d+)', last_batch_file)
            if match:
                batch_index = int(match.group(1))
                
                # Berechne, wie viele URLs bereits verarbeitet wurden
                processed_urls = (batch_index + 1) * args.batch_size
                logger.info(f"Bereits verarbeitet: {processed_urls} URLs")
                
                # Begrenze die URLs auf die noch nicht verarbeiteten
                if processed_urls < len(urls):
                    # Setze den Batch-Index für die Fortsetzung
                    os.environ['BATCH_START_INDEX'] = str(batch_index + 1)
                    urls = urls[processed_urls:]
                    logger.info(f"Verarbeite die restlichen {len(urls)} URLs")
                else:
                    logger.info("Alle URLs wurden bereits verarbeitet.")
                    sys.exit(0)
    
    # Verarbeite die URLs
    results = scraper.process_urls(urls, args.output, limit=args.limit, batch_size=args.batch_size)
    
    # Zeige Statistiken
    logger.info(f"Scraping abgeschlossen in {scraper.stats['elapsed_time']:.1f} Sekunden")
    logger.info(f"Erfolgsrate: {scraper.stats['success'] / max(scraper.stats['total'], 1) * 100:.1f}% ({scraper.stats['success']}/{scraper.stats['total']})")
    logger.info(f"ScrapingBee: {scraper.stats['scrapingbee_used']}, Smartproxy: {scraper.stats['smartproxy_used']}, Fallback: {scraper.stats['fallback_used']}, Cache: {scraper.stats['cached']}")
    logger.info(f"Geschätzte Kosten: ${scraper.stats['estimated_cost']:.2f}")
    
    if scraper.stats['budget_limit_reached']:
        logger.warning(f"Budget-Limit von ${args.budget:.2f} erreicht. Einige URLs wurden übersprungen.")

if __name__ == "__main__":
    main() 