#!/usr/bin/env python3

"""
batch_processor.py

Dieses Skript verarbeitet Lesezeichen-URLs in Batches und verwendet die Zyte API
oder andere Scraping-Methoden, um Inhalt und Metadaten zu extrahieren. Es unterstützt
parallele Anfragen, Retry-Logik und detaillierte Fehlerbehandlung.
"""

import os
import re
import json
import time
import random
import logging
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Set
import aiohttp
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import hashlib

# Versuche, Zyte API Client zu importieren, falls verfügbar
try:
    from zyte_api import AsyncClient as ZyteClient
    ZYTE_AVAILABLE = True
except ImportError:
    ZYTE_AVAILABLE = False

# Konfiguration
DEFAULT_BATCH_SIZE = 10
DEFAULT_MAX_CONCURRENT = 5
DEFAULT_TIMEOUT = 60  # Sekunden
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 5  # Sekunden
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Standardpfade für Dateien
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "../../data/scraping"
LOGS_DIR = SCRIPT_DIR / "../../logs/scraping"

# Stelle sicher, dass die Verzeichnisse existieren
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Konfiguriere Logging
log_file = LOGS_DIR / f"scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("batch_processor")

class BatchProcessor:
    """Verarbeitet URLs in Batches zum Scraping von Inhalten."""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 batch_size: int = DEFAULT_BATCH_SIZE, 
                 max_concurrent: int = DEFAULT_MAX_CONCURRENT,
                 timeout: int = DEFAULT_TIMEOUT,
                 retry_count: int = DEFAULT_RETRY_COUNT,
                 retry_delay: int = DEFAULT_RETRY_DELAY,
                 use_zyte: bool = False):
        """
        Initialisiert den BatchProcessor.
        
        Args:
            api_key: Zyte API-Schlüssel, falls vorhanden.
            batch_size: Größe der zu verarbeitenden Batches.
            max_concurrent: Maximale Anzahl gleichzeitiger Anfragen.
            timeout: Zeitlimit für Anfragen in Sekunden.
            retry_count: Anzahl der Wiederholungen bei Fehlern.
            retry_delay: Verzögerung zwischen Wiederholungen in Sekunden.
            use_zyte: Ob die Zyte API verwendet werden soll.
        """
        self.api_key = api_key
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.use_zyte = use_zyte and ZYTE_AVAILABLE
        
        # Statistiken
        self.stats = {
            "total_urls": 0,
            "successful": 0,
            "failed": 0,
            "retries": 0,
            "start_time": None,
            "end_time": None,
            "errors": {}
        }
        
        # Cache für bereits verarbeitete URLs
        self.processed_urls = set()
        
        # Semaphore für Begrenzung gleichzeitiger Anfragen
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.info(f"BatchProcessor initialisiert: batch_size={batch_size}, max_concurrent={max_concurrent}")
        if self.use_zyte:
            logger.info("Verwende Zyte API für Scraping")
        else:
            logger.info("Verwende Standard HTTP-Client für Scraping")
    
    async def process_urls(self, urls: List[Dict[str, Any]], output_dir: Union[str, Path]) -> Dict[str, Any]:
        """
        Verarbeitet eine Liste von URLs in Batches.
        
        Args:
            urls: Liste von URL-Dictionaries mit mindestens den Schlüsseln 'url' und 'id'.
            output_dir: Verzeichnis für die Ausgabedateien.
            
        Returns:
            Ein Dictionary mit Statistiken über den Scraping-Prozess.
        """
        # Initialisiere Statistiken
        self.stats["total_urls"] = len(urls)
        self.stats["start_time"] = datetime.now().isoformat()
        
        # Stelle sicher, dass das Ausgabeverzeichnis existiert
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Erstelle Batches
        batches = [urls[i:i + self.batch_size] for i in range(0, len(urls), self.batch_size)]
        logger.info(f"Verarbeite {len(urls)} URLs in {len(batches)} Batches")
        
        # Verarbeite jeden Batch
        for i, batch in enumerate(batches):
            logger.info(f"Verarbeite Batch {i+1}/{len(batches)} mit {len(batch)} URLs")
            
            # Erstelle Tasks für gleichzeitige Verarbeitung
            tasks = []
            for url_item in batch:
                # Prüfe, ob wir diese URL bereits verarbeitet haben
                url = url_item.get('url')
                if url in self.processed_urls:
                    logger.info(f"Überspringe bereits verarbeitete URL: {url}")
                    continue
                
                tasks.append(self.process_url(url_item, output_dir))
            
            # Führe die Tasks aus
            await asyncio.gather(*tasks)
            
            # Zeige Fortschritt
            completed = self.stats["successful"] + self.stats["failed"]
            progress = (completed / self.stats["total_urls"]) * 100
            logger.info(f"Fortschritt: {completed}/{self.stats['total_urls']} URLs verarbeitet ({progress:.1f}%)")
        
        # Aktualisiere Endzeit
        self.stats["end_time"] = datetime.now().isoformat()
        
        # Berechne zusätzliche Statistiken
        self._calculate_additional_stats()
        
        return self.stats
    
    async def process_url(self, url_item: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """
        Verarbeitet eine einzelne URL mit Retry-Logik.
        
        Args:
            url_item: Dictionary mit mindestens den Schlüsseln 'url' und 'id'.
            output_dir: Verzeichnis für die Ausgabedateien.
            
        Returns:
            Die extrahierten Daten für die URL.
        """
        url = url_item.get('url')
        if not url:
            logger.warning(f"Überspringe Eintrag ohne URL: {url_item}")
            self.stats["failed"] += 1
            return {}
        
        url_id = url_item.get('id')
        if not url_id:
            # Erstelle eine ID basierend auf der URL
            url_id = f"url_{hashlib.md5(url.encode()).hexdigest()}"
        
        # Markiere die URL als verarbeitet
        self.processed_urls.add(url)
        
        # Verwende Semaphore zur Begrenzung gleichzeitiger Anfragen
        async with self.semaphore:
            # Versuche es mehrmals mit Retry-Logik
            for attempt in range(self.retry_count + 1):
                try:
                    if attempt > 0:
                        # Warte vor dem erneuten Versuch
                        delay = self.retry_delay * (1 + random.random())
                        logger.info(f"Warte {delay:.1f}s vor erneutem Versuch {attempt}/{self.retry_count} für URL: {url}")
                        await asyncio.sleep(delay)
                        self.stats["retries"] += 1
                    
                    # Extrahiere Daten
                    if self.use_zyte:
                        result = await self._extract_with_zyte(url)
                    else:
                        result = await self._extract_with_http(url)
                    
                    # Füge Metadaten hinzu
                    result.update({
                        "id": url_id,
                        "original_url": url,
                        "timestamp": datetime.now().isoformat(),
                        "source": url_item
                    })
                    
                    # Speichere das Ergebnis
                    await self._save_result(result, output_dir)
                    
                    # Aktualisiere Statistiken
                    self.stats["successful"] += 1
                    
                    return result
                    
                except Exception as e:
                    error_type = type(e).__name__
                    if error_type not in self.stats["errors"]:
                        self.stats["errors"][error_type] = 0
                    self.stats["errors"][error_type] += 1
                    
                    logger.error(f"Fehler beim Verarbeiten von URL {url} (Versuch {attempt+1}/{self.retry_count+1}): {str(e)}")
                    
                    # Wenn dies der letzte Versuch war, zähle es als fehlgeschlagen
                    if attempt == self.retry_count:
                        self.stats["failed"] += 1
                        
                        # Speichere Fehlerinformationen
                        error_result = {
                            "id": url_id,
                            "original_url": url,
                            "timestamp": datetime.now().isoformat(),
                            "error": {
                                "type": error_type,
                                "message": str(e),
                                "attempts": attempt + 1
                            },
                            "source": url_item
                        }
                        
                        await self._save_result(error_result, output_dir, is_error=True)
                        
                        return error_result
        
        return {}
    
    async def _extract_with_zyte(self, url: str) -> Dict[str, Any]:
        """
        Extrahiert Daten mit der Zyte API.
        
        Args:
            url: Die zu scrapende URL.
            
        Returns:
            Ein Dictionary mit den extrahierten Daten.
        """
        if not self.api_key:
            raise ValueError("Zyte API-Schlüssel ist erforderlich")
        
        async with ZyteClient(self.api_key) as client:
            response = await client.extract(
                url=url,
                browserHtml=True,
                article=True,
                httpResponseHeaders=True,
                screenshot=True
            )
            
            result = {
                "url": response.get("url", url),
                "title": response.get("article", {}).get("headline"),
                "text": response.get("article", {}).get("body"),
                "html": response.get("browserHtml"),
                "headers": response.get("httpResponseHeaders"),
                "status_code": 200,  # Zyte API liefert keinen Statuscode, nehmen wir 200 an
                "screenshot": response.get("screenshot")
            }
            
            return result
    
    async def _extract_with_http(self, url: str) -> Dict[str, Any]:
        """
        Extrahiert Daten mit einem Standard HTTP-Client.
        
        Args:
            url: Die zu scrapende URL.
            
        Returns:
            Ein Dictionary mit den extrahierten Daten.
        """
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, ssl=False) as response:
                html = await response.text()
                
                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extrahiere Titel
                title = soup.title.string if soup.title else None
                
                # Extrahiere Metadaten
                meta_description = soup.find('meta', attrs={'name': 'description'})
                description = meta_description.get('content') if meta_description else None
                
                # Extrahiere Hauptinhalt
                main_content = self._extract_main_content(soup)
                
                # Extrahiere alle Links
                links = [a.get('href') for a in soup.find_all('a', href=True)]
                absolute_links = [urljoin(url, link) for link in links]
                
                result = {
                    "url": str(response.url),
                    "status_code": response.status,
                    "title": title,
                    "description": description,
                    "text": main_content,
                    "html": html,
                    "headers": dict(response.headers),
                    "links": absolute_links
                }
                
                return result
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extrahiert den Hauptinhalt einer Webseite.
        
        Args:
            soup: BeautifulSoup-Objekt der Webseite.
            
        Returns:
            Der extrahierte Hauptinhalt als Text.
        """
        # Versuche, Artikelinhalt zu finden
        article = soup.find('article')
        if article:
            return article.get_text(separator="\n", strip=True)
        
        # Versuche, Hauptinhalt über häufige IDs zu finden
        for content_id in ['content', 'main', 'main-content', 'article', 'post']:
            content = soup.find(id=content_id) or soup.find(class_=content_id)
            if content:
                return content.get_text(separator="\n", strip=True)
        
        # Entferne Header, Footer, Navigation, etc.
        for tag in soup(['header', 'footer', 'nav', 'aside', 'script', 'style']):
            tag.decompose()
        
        # Verwende den Body als Fallback
        body = soup.find('body')
        if body:
            return body.get_text(separator="\n", strip=True)
        
        # Fallback: Ganzer Text
        return soup.get_text(separator="\n", strip=True)
    
    async def _save_result(self, result: Dict[str, Any], output_dir: Path, is_error: bool = False) -> None:
        """
        Speichert das Scraping-Ergebnis in einer JSON-Datei.
        
        Args:
            result: Die zu speichernden Daten.
            output_dir: Verzeichnis für die Ausgabedateien.
            is_error: Ob es sich um einen Fehler handelt.
        """
        url_id = result.get("id")
        if not url_id:
            return
        
        # Erstelle Dateinamen
        if is_error:
            filename = f"error_{url_id}.json"
            file_path = output_dir / "errors" / filename
        else:
            filename = f"result_{url_id}.json"
            file_path = output_dir / "results" / filename
        
        # Stelle sicher, dass das Unterverzeichnis existiert
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Speichere die Daten
            await asyncio.to_thread(self._write_json_file, result, file_path)
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Ergebnisses für URL-ID {url_id}: {str(e)}")
    
    def _write_json_file(self, data: Dict[str, Any], file_path: Path) -> None:
        """
        Schreibt Daten in eine JSON-Datei (synchron).
        
        Args:
            data: Die zu speichernden Daten.
            file_path: Pfad zur Ausgabedatei.
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _calculate_additional_stats(self) -> None:
        """Berechnet zusätzliche Statistiken über den Scraping-Prozess."""
        if self.stats["start_time"] and self.stats["end_time"]:
            start = datetime.fromisoformat(self.stats["start_time"])
            end = datetime.fromisoformat(self.stats["end_time"])
            duration = (end - start).total_seconds()
            self.stats["duration_seconds"] = duration
            
            if self.stats["total_urls"] > 0:
                self.stats["average_time_per_url"] = duration / self.stats["total_urls"]
                self.stats["success_rate"] = (self.stats["successful"] / self.stats["total_urls"]) * 100
            
            logger.info(f"Scraping abgeschlossen in {duration:.1f} Sekunden")
            logger.info(f"Erfolgsrate: {self.stats.get('success_rate', 0):.1f}% ({self.stats['successful']}/{self.stats['total_urls']})")
            
            if self.stats["errors"]:
                logger.info("Fehlerstatistiken:")
                for error_type, count in self.stats["errors"].items():
                    logger.info(f"  - {error_type}: {count}")

async def load_urls_from_file(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    Lädt URLs aus einer Datei.
    
    Args:
        file_path: Pfad zur Datei mit URLs.
        
    Returns:
        Eine Liste von URL-Dictionaries.
    """
    file_path = Path(file_path)
    
    if file_path.suffix == '.json':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Überprüfe verschiedene Formate
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'urls' in data:
                return data['urls']
            elif isinstance(data, dict) and 'bookmarks' in data:
                # Extrahiere URLs aus Lesezeichen-Hierarchie
                try:
                    from scripts.scraping.bookmark_parser import BookmarkParser
                    parser = BookmarkParser()
                    return parser.extract_urls(data)
                except ImportError:
                    logger.error("BookmarkParser konnte nicht importiert werden.")
                    return []
    else:
        # Nimm an, dass es sich um eine einfache Textdatei mit einer URL pro Zeile handelt
        urls = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                url = line.strip()
                if url and not url.startswith('#'):
                    urls.append({
                        "id": f"url_{i+1}",
                        "url": url,
                        "source": "text_file"
                    })
        return urls
    
    return []

async def main():
    """Hauptfunktion zum Verarbeiten von URLs in Batches."""
    parser = argparse.ArgumentParser(description="Verarbeite URLs in Batches für Scraping")
    parser.add_argument("input_file", help="Pfad zur Datei mit URLs (Text oder JSON)")
    parser.add_argument("--output-dir", "-o", default=None,
                      help="Ausgabeverzeichnis für Ergebnisse (Standard: data/scraping/YYYY-MM-DD)")
    parser.add_argument("--batch-size", "-b", type=int, default=DEFAULT_BATCH_SIZE,
                      help=f"Größe der Batches (Standard: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--max-concurrent", "-m", type=int, default=DEFAULT_MAX_CONCURRENT,
                      help=f"Maximale Anzahl gleichzeitiger Anfragen (Standard: {DEFAULT_MAX_CONCURRENT})")
    parser.add_argument("--timeout", "-t", type=int, default=DEFAULT_TIMEOUT,
                      help=f"Zeitlimit für Anfragen in Sekunden (Standard: {DEFAULT_TIMEOUT})")
    parser.add_argument("--retry-count", "-r", type=int, default=DEFAULT_RETRY_COUNT,
                      help=f"Anzahl der Wiederholungen bei Fehlern (Standard: {DEFAULT_RETRY_COUNT})")
    parser.add_argument("--api-key", "-k", help="Zyte API-Schlüssel")
    parser.add_argument("--use-zyte", "-z", action="store_true", help="Verwende Zyte API")
    parser.add_argument("--test", action="store_true", help="Testmodus: Verarbeite nur die ersten 10 URLs")
    
    args = parser.parse_args()
    
    # Lade URLs
    urls = await load_urls_from_file(args.input_file)
    logger.info(f"Geladen: {len(urls)} URLs aus {args.input_file}")
    
    if args.test:
        # Im Testmodus nur die ersten 10 URLs verwenden
        test_count = min(10, len(urls))
        urls = urls[:test_count]
        logger.info(f"Testmodus: Verwende nur die ersten {test_count} URLs")
    
    # Setze Ausgabeverzeichnis
    if not args.output_dir:
        date_str = datetime.now().strftime("%Y-%m-%d")
        args.output_dir = DATA_DIR / date_str
    
    # Erstelle den Processor
    processor = BatchProcessor(
        api_key=args.api_key,
        batch_size=args.batch_size,
        max_concurrent=args.max_concurrent,
        timeout=args.timeout,
        retry_count=args.retry_count,
        use_zyte=args.use_zyte
    )
    
    # Verarbeite URLs
    stats = await processor.process_urls(urls, args.output_dir)
    
    # Speichere Statistiken
    stats_file = Path(args.output_dir) / "scraping_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Scraping abgeschlossen. Statistiken in {stats_file} gespeichert.")
    logger.info(f"Verarbeitet: {stats['total_urls']} URLs, Erfolgreich: {stats['successful']}, Fehlgeschlagen: {stats['failed']}")
    
    # Zeige Zusammenfassung
    success_rate = stats.get("success_rate", 0)
    logger.info(f"Erfolgsrate: {success_rate:.1f}%")
    logger.info(f"Dauer: {stats.get('duration_seconds', 0):.1f} Sekunden")
    
    # Empfehlung für Optimierungen
    if success_rate < 80:
        logger.warning("Die Erfolgsrate ist niedrig. Erwäge folgende Optimierungen:")
        logger.warning("1. Erhöhe den Timeout-Wert mit --timeout")
        logger.warning("2. Erhöhe die Anzahl der Wiederholungen mit --retry-count")
        logger.warning("3. Verwende die Zyte API für bessere Ergebnisse mit --use-zyte")
    
    if stats.get("average_time_per_url", 0) > 10:
        logger.warning("Die durchschnittliche Verarbeitungszeit pro URL ist hoch.")
        logger.warning("1. Verringere max-concurrent für stabilere Ergebnisse")
        logger.warning("2. Erhöhe batch-size für mehr Durchsatz (erfordert möglicherweise mehr Ressourcen)")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scraping-Prozess durch Benutzer unterbrochen")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {str(e)}", exc_info=True) 