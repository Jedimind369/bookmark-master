#!/usr/bin/env python3

"""
zyte_scraper.py

Implementierung eines robusten Scrapers mit Zyte API, der Batch-Verarbeitung
und umfassende Fehlerbehandlung unterstützt.
"""

import os
import json
import time
import logging
import asyncio
import aiohttp
import base64
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

# Lokale Imports
from .settings import (
    ZYTE_API_KEY,
    ZYTE_API_ENDPOINT,
    ZYTE_API_SETTINGS,
    BATCH_SIZE,
    MAX_CONCURRENT_REQUESTS,
    DATA_DIR,
    LOG_DIR,
    SUCCESS_LOG,
    ERROR_LOG,
    RETRY_LOG
)

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "zyte_scraper.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("zyte_scraper")

class ZyteScraper:
    """
    Ein robuster Scraper für die Zyte API mit Unterstützung für Batch-Verarbeitung
    und umfassende Fehlerbehandlung.
    """
    
    def __init__(self, api_key: Optional[str] = None, custom_settings: Optional[Dict] = None):
        """
        Initialisiert den Scraper mit API-Schlüssel und benutzerdefinierten Einstellungen.
        
        Args:
            api_key: Zyte API-Schlüssel (falls nicht in der Umgebungsvariable definiert)
            custom_settings: Benutzerdefinierte Einstellungen, die die Standardeinstellungen überschreiben
        """
        self.api_key = api_key or ZYTE_API_KEY
        if not self.api_key:
            raise ValueError("Zyte API-Schlüssel ist erforderlich. Setze die Umgebungsvariable ZYTE_API_KEY oder übergebe den Schlüssel als Parameter.")
        
        # Basis-Auth-Header für Zyte API
        auth_string = f"{self.api_key}:"
        auth_bytes = auth_string.encode('ascii')
        self.auth_header = f"Basic {base64.b64encode(auth_bytes).decode('ascii')}"
        
        # API-Einstellungen kombinieren
        self.api_settings = ZYTE_API_SETTINGS.copy()
        if custom_settings:
            self.api_settings.update(custom_settings)
        
        # Status-Tracking
        self.successful_urls: Set[str] = set()
        self.failed_urls: Dict[str, str] = {}  # URL -> Fehlergrund
        self.retry_urls: Dict[str, int] = {}   # URL -> Anzahl der Versuche
        
        # Statistiken
        self.stats = {
            "total_urls": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "start_time": None,
            "end_time": None,
            "total_time": 0
        }
        
        # Logs initialisieren
        self._init_logs()
    
    def _init_logs(self) -> None:
        """Initialisiert die Log-Dateien."""
        # Erfolgreiche URLs
        if not SUCCESS_LOG.exists():
            with open(SUCCESS_LOG, 'w') as f:
                f.write("timestamp,url,filename\n")
        
        # Fehlgeschlagene URLs
        if not ERROR_LOG.exists():
            with open(ERROR_LOG, 'w') as f:
                f.write("timestamp,url,error\n")
        
        # URLs für Wiederholungsversuche
        if not RETRY_LOG.exists():
            with open(RETRY_LOG, 'w') as f:
                f.write("timestamp,url,attempts\n")
    
    def _log_success(self, url: str, filename: str) -> None:
        """Protokolliert eine erfolgreich gescrapte URL."""
        timestamp = datetime.now().isoformat()
        with open(SUCCESS_LOG, 'a') as f:
            f.write(f"{timestamp},{url},{filename}\n")
    
    def _log_error(self, url: str, error: str) -> None:
        """Protokolliert einen Fehler beim Scraping einer URL."""
        timestamp = datetime.now().isoformat()
        with open(ERROR_LOG, 'a') as f:
            f.write(f"{timestamp},{url},{error}\n")
    
    def _log_retry(self, url: str, attempts: int) -> None:
        """Protokolliert einen Wiederholungsversuch für eine URL."""
        timestamp = datetime.now().isoformat()
        with open(RETRY_LOG, 'a') as f:
            f.write(f"{timestamp},{url},{attempts}\n")
    
    def _generate_filename(self, url: str) -> str:
        """Generiert einen Dateinamen basierend auf der URL."""
        # Ersetzt Sonderzeichen durch Underscores und entfernt das Protokoll
        safe_url = url.replace('https://', '').replace('http://', '').replace('/', '_').replace(':', '_')
        return f"{safe_url[:100]}_{int(time.time())}.json"
    
    async def _fetch_single_url(self, session: aiohttp.ClientSession, url: str) -> Tuple[str, Optional[Dict], Optional[str]]:
        """
        Ruft eine einzelne URL ab.
        
        Args:
            session: Aiohttp-Session
            url: Die abzurufende URL
            
        Returns:
            Tuple aus URL, Response-Daten (oder None bei Fehler) und Fehlermeldung (oder None bei Erfolg)
        """
        # Bereite die Anfrage vor
        payload = {
            "url": url,
            **self.api_settings
        }
        
        # Zähle den Versuch
        self.retry_urls[url] = self.retry_urls.get(url, 0) + 1
        current_attempt = self.retry_urls[url]
        
        try:
            # Sende die Anfrage an die Zyte API
            async with session.post(
                ZYTE_API_ENDPOINT,
                json=payload,
                headers={"Authorization": self.auth_header},
                timeout=self.api_settings.get("httpResponseTimeout", 30) + 5  # Etwas größeres Timeout als in den Einstellungen
            ) as response:
                # Überprüfe den Status-Code
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Erfolgreich abgerufen: {url}")
                    self.successful_urls.add(url)
                    self.stats["successful"] += 1
                    return url, data, None
                else:
                    error_text = await response.text()
                    error_msg = f"HTTP-Fehler {response.status}: {error_text}"
                    logger.error(f"Fehler beim Abrufen von {url}: {error_msg}")
                    return url, None, error_msg
                    
        except asyncio.TimeoutError:
            error_msg = f"Timeout nach {self.api_settings.get('httpResponseTimeout', 30)} Sekunden"
            logger.error(f"Timeout beim Abrufen von {url}")
            return url, None, error_msg
            
        except aiohttp.ClientError as e:
            error_msg = f"Client-Fehler: {str(e)}"
            logger.error(f"Client-Fehler beim Abrufen von {url}: {str(e)}")
            return url, None, error_msg
            
        except Exception as e:
            error_msg = f"Unerwarteter Fehler: {str(e)}"
            logger.error(f"Unerwarteter Fehler beim Abrufen von {url}: {str(e)}")
            return url, None, error_msg
    
    async def _process_batch(self, urls: List[str], session: aiohttp.ClientSession) -> List[Tuple[str, bool]]:
        """
        Verarbeitet einen Batch von URLs parallel.
        
        Args:
            urls: Liste von URLs zum Verarbeiten
            session: Aiohttp-Session
            
        Returns:
            Liste von Tuples (URL, Erfolg)
        """
        # Erstelle Tasks für alle URLs im Batch
        tasks = [self._fetch_single_url(session, url) for url in urls]
        
        # Führe alle Tasks aus und sammle die Ergebnisse
        results = await asyncio.gather(*tasks)
        
        # Verarbeite die Ergebnisse
        processed_results = []
        for url, data, error in results:
            if data:  # Erfolgreicher Abruf
                # Speichere die Daten
                filename = self._generate_filename(url)
                filepath = DATA_DIR / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self._log_success(url, filename)
                processed_results.append((url, True))
            else:  # Fehler beim Abrufen
                self.failed_urls[url] = error
                self._log_error(url, error)
                
                # Überprüfe, ob wir es erneut versuchen sollten
                max_retries = self.api_settings.get("maxHttpRetries", 3)
                if self.retry_urls.get(url, 0) < max_retries:
                    self._log_retry(url, self.retry_urls[url])
                    self.stats["retried"] += 1
                else:
                    self.stats["failed"] += 1
                
                processed_results.append((url, False))
        
        return processed_results
    
    async def scrape_batch(self, urls: List[str]) -> Dict[str, Any]:
        """
        Scrapt einen Batch von URLs mit Fehlerbehandlung und Wiederholungsversuchen.
        
        Args:
            urls: Liste von URLs zum Scrapen
            
        Returns:
            Statistiken über den Scraping-Prozess
        """
        if not urls:
            logger.warning("Keine URLs zum Scrapen übergeben.")
            return self.stats
        
        self.stats["total_urls"] += len(urls)
        self.stats["start_time"] = datetime.now()
        
        # Teile URLs in kleinere Batches für parallele Verarbeitung
        url_batches = [urls[i:i + BATCH_SIZE] for i in range(0, len(urls), BATCH_SIZE)]
        logger.info(f"Verarbeite {len(urls)} URLs in {len(url_batches)} Batches à {BATCH_SIZE} URLs")
        
        # Verarbeite alle Batches
        async with aiohttp.ClientSession() as session:
            for i, batch in enumerate(url_batches):
                logger.info(f"Verarbeite Batch {i+1}/{len(url_batches)} mit {len(batch)} URLs")
                await self._process_batch(batch, session)
                
                # Kurze Pause zwischen Batches, um API-Limits nicht zu überschreiten
                if i < len(url_batches) - 1:
                    await asyncio.sleep(1)
        
        # Sammle Statistiken
        self.stats["end_time"] = datetime.now()
        self.stats["total_time"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        logger.info(f"Scraping abgeschlossen. Erfolgreiche URLs: {self.stats['successful']}, "
                   f"Fehlgeschlagene URLs: {self.stats['failed']}, "
                   f"Wiederholte URLs: {self.stats['retried']}")
        
        return self.stats
    
    async def scrape_urls(self, urls: List[str], max_concurrent: int = MAX_CONCURRENT_REQUESTS) -> Dict[str, Any]:
        """
        Scrapt eine Liste von URLs mit begrenzter Parallelität.
        
        Args:
            urls: Liste von URLs zum Scrapen
            max_concurrent: Maximale Anzahl gleichzeitiger Anfragen
            
        Returns:
            Statistiken über den Scraping-Prozess
        """
        if not urls:
            logger.warning("Keine URLs zum Scrapen übergeben.")
            return self.stats
        
        # Entferne Duplikate und behmetle nur einzigartige URLs
        unique_urls = list(set(urls))
        if len(unique_urls) < len(urls):
            logger.info(f"{len(urls) - len(unique_urls)} duplizierte URLs entfernt.")
        
        self.stats["total_urls"] = len(unique_urls)
        self.stats["start_time"] = datetime.now()
        
        # Erstelle Semaphore für begrenzte Parallelität
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(url: str, session: aiohttp.ClientSession) -> Tuple[str, Optional[Dict], Optional[str]]:
            """Hilfsfunktion, um das Semaphore zu verwenden."""
            async with semaphore:
                return await self._fetch_single_url(session, url)
        
        # Verarbeite alle URLs mit begrenzter Parallelität
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_with_semaphore(url, session) for url in unique_urls]
            results = await asyncio.gather(*tasks)
            
            # Verarbeite die Ergebnisse
            for url, data, error in results:
                if data:  # Erfolgreicher Abruf
                    # Speichere die Daten
                    filename = self._generate_filename(url)
                    filepath = DATA_DIR / filename
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    self._log_success(url, filename)
                    self.stats["successful"] += 1
                else:  # Fehler beim Abrufen
                    self.failed_urls[url] = error
                    self._log_error(url, error)
                    self.stats["failed"] += 1
        
        # Sammle Statistiken
        self.stats["end_time"] = datetime.now()
        self.stats["total_time"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        logger.info(f"Scraping abgeschlossen. Erfolgreiche URLs: {self.stats['successful']}, "
                   f"Fehlgeschlagene URLs: {self.stats['failed']}")
        
        return self.stats
    
    def get_failed_urls(self) -> List[str]:
        """Gibt die Liste der fehlgeschlagenen URLs zurück."""
        return list(self.failed_urls.keys())
    
    def get_successful_urls(self) -> List[str]:
        """Gibt die Liste der erfolgreichen URLs zurück."""
        return list(self.successful_urls)
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt die Statistiken des Scraping-Prozesses zurück."""
        return self.stats.copy()


# Einfache Hilfsfunktion für die synchrone Nutzung
def scrape_urls(urls: List[str], api_key: Optional[str] = None, custom_settings: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Synchrone Funktion zum Scrapen einer Liste von URLs.
    
    Args:
        urls: Liste von URLs zum Scrapen
        api_key: Zyte API-Schlüssel (falls nicht in der Umgebungsvariable definiert)
        custom_settings: Benutzerdefinierte Einstellungen, die die Standardeinstellungen überschreiben
        
    Returns:
        Statistiken über den Scraping-Prozess
    """
    scraper = ZyteScraper(api_key, custom_settings)
    return asyncio.run(scraper.scrape_urls(urls)) 