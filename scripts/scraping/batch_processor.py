#!/usr/bin/env python3

"""
batch_processor.py

Unterstützt das Batch-Processing von URLs für das Scraping und die KI-basierte Inhaltsanalyse.
Optimiert für große URL-Listen (>10.000) mit Fortsetzungsmöglichkeit und umfangreicher Fortschrittsverfolgung.
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set, Optional, Tuple

# Pfad zur Hauptanwendung hinzufügen, damit wir auf andere Module zugreifen können
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import der benötigten Klassen und Einstellungen
from .zyte_scraper import ZyteScraper
from .content_analyzer import ContentAnalyzer
from .settings import DATA_DIR, LOG_DIR, PROGRESS_DIR

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "batch_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("batch_processor")

class BatchProcessor:
    """
    Verarbeitet URLs in Batches, mit Wiederaufnahme und Fortschrittsverfolgung.
    Optimiert für die Verarbeitung großer URL-Listen mit Neustartfähigkeit.
    """
    
    def __init__(self, 
                 batch_size: int = 100, 
                 max_concurrent: int = 10, 
                 max_retries: int = 3,
                 retry_delay: int = 5,
                 zyte_api_key: Optional[str] = None,
                 output_dir: str = str(DATA_DIR)):
        """
        Initialisiert den BatchProcessor.
        
        Args:
            batch_size: Anzahl der URLs pro Batch
            max_concurrent: Maximale Anzahl gleichzeitiger Anfragen
            max_retries: Maximale Anzahl von Wiederholungsversuchen bei Fehlern
            retry_delay: Verzögerung zwischen Wiederholungsversuchen in Sekunden
            zyte_api_key: API-Schlüssel für Zyte (optional, sonst aus Umgebungsvariable)
            output_dir: Verzeichnis für die Ausgabe der gescrapten Daten
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Initialisiere den Zyte-Scraper
        self.scraper = ZyteScraper(api_key=zyte_api_key, output_dir=output_dir)
        
        # Initialisiere den Content-Analyzer mit allen verfügbaren Modellen
        self.analyzer = ContentAnalyzer()
        
        # Statistiken
        self.stats = {
            "total_urls": 0,
            "processed_urls": 0,
            "successful_urls": 0,
            "failed_urls": 0,
            "retry_count": 0,
            "start_time": None,
            "end_time": None,
            "estimated_completion_time": None,
            "model_usage": {}
        }
        
        # Fortschrittsverfolgung
        self.processed_urls: Set[str] = set()
        self.successful_urls: Set[str] = set()
        self.failed_urls: Dict[str, str] = {}  # URL -> Fehlergrund
        
        # Verwende einen eindeutigen Namen für die Fortschrittsdatei
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.progress_file = PROGRESS_DIR / f"progress_{timestamp}.json"
        
        # Stelle sicher, dass Verzeichnisse existieren
        PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _save_progress(self):
        """Speichert den aktuellen Fortschritt in einer Datei."""
        progress_data = {
            "stats": self.stats,
            "processed_urls": list(self.processed_urls),
            "successful_urls": list(self.successful_urls),
            "failed_urls": self.failed_urls,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Fortschritt gespeichert: {self.progress_file}")
    
    def _load_progress(self, progress_file: Path) -> bool:
        """
        Lädt den Fortschritt aus einer bestehenden Datei.
        
        Args:
            progress_file: Pfad zur Fortschrittsdatei
            
        Returns:
            bool: True, wenn der Fortschritt erfolgreich geladen wurde
        """
        try:
            if not progress_file.exists():
                logger.warning(f"Fortschrittsdatei {progress_file} existiert nicht.")
                return False
            
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            self.stats = progress_data.get("stats", self.stats)
            self.processed_urls = set(progress_data.get("processed_urls", []))
            self.successful_urls = set(progress_data.get("successful_urls", []))
            self.failed_urls = progress_data.get("failed_urls", {})
            
            # Aktualisiere die Fortschrittsdatei für diese Sitzung
            self.progress_file = progress_file
            
            logger.info(f"Fortschritt geladen: {len(self.processed_urls)} verarbeitete URLs, "
                       f"{len(self.successful_urls)} erfolgreiche URLs, "
                       f"{len(self.failed_urls)} fehlgeschlagene URLs.")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Laden des Fortschritts: {str(e)}")
            return False
    
    def _log_progress(self, batch_index: int, total_batches: int):
        """
        Loggt den aktuellen Fortschritt und schätzt die verbleibende Zeit.
        
        Args:
            batch_index: Index des aktuellen Batches
            total_batches: Gesamtanzahl der Batches
        """
        if self.stats["start_time"] is None or self.stats["processed_urls"] == 0:
            return
        
        # Berechne die verstrichene Zeit
        now = datetime.now()
        elapsed_seconds = (now - self.stats["start_time"]).total_seconds()
        
        # Berechne die Rate (URLs pro Sekunde)
        if elapsed_seconds > 0:
            urls_per_second = self.stats["processed_urls"] / elapsed_seconds
            
            # Schätze die verbleibende Zeit
            remaining_urls = self.stats["total_urls"] - self.stats["processed_urls"]
            if urls_per_second > 0:
                remaining_seconds = remaining_urls / urls_per_second
                estimated_completion = now + timedelta(seconds=remaining_seconds)
                self.stats["estimated_completion_time"] = estimated_completion.isoformat()
                
                # Formatiere für das Logging
                if remaining_seconds < 60:
                    time_str = f"{int(remaining_seconds)} Sekunden"
                elif remaining_seconds < 3600:
                    time_str = f"{int(remaining_seconds / 60)} Minuten"
                else:
                    time_str = f"{remaining_seconds / 3600:.1f} Stunden"
                
                # Bereite den Fortschrittsbalken vor
                progress_pct = (self.stats["processed_urls"] / self.stats["total_urls"]) * 100
                bar_length = 30
                filled_length = int(bar_length * self.stats["processed_urls"] // self.stats["total_urls"])
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                
                logger.info(f"Fortschritt: [{bar}] {progress_pct:.1f}% | "
                           f"Batch {batch_index}/{total_batches} | "
                           f"URLs: {self.stats['processed_urls']}/{self.stats['total_urls']} | "
                           f"Rate: {urls_per_second:.2f} URLs/s | "
                           f"Geschätzte verbleibende Zeit: {time_str}")
                
                # Modellnutzung loggen
                model_stats = self.analyzer.get_model_usage_stats()
                self.stats["model_usage"] = model_stats
                
                # Log nur, wenn Modelle verwendet wurden
                if model_stats["total_uses"] > 0:
                    logger.info(f"Modellnutzung: Gesamt: {model_stats['total_uses']} Aufrufe, "
                               f"Kosten: ${model_stats['total_cost']:.4f}")
                    for model_id, usage in model_stats["models"].items():
                        if usage["uses"] > 0:
                            logger.info(f"  - {model_id}: {usage['uses']} Aufrufe, ${usage['total_cost']:.4f}")
    
    def _split_urls_into_batches(self, urls: List[str]) -> List[List[str]]:
        """
        Teilt die URLs in Batches auf.
        
        Args:
            urls: Liste der zu verarbeitenden URLs
            
        Returns:
            Liste von URL-Batches
        """
        batches = []
        for i in range(0, len(urls), self.batch_size):
            batches.append(urls[i:i + self.batch_size])
        return batches
    
    async def _process_batch(self, batch: List[str]) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        Verarbeitet einen Batch von URLs.
        
        Args:
            batch: Liste von URLs für den Batch
            
        Returns:
            Tuple von (erfolgreiche URLs, fehlgeschlagene URLs mit Fehlergrund)
        """
        # Filtere URLs, die bereits verarbeitet wurden
        new_urls = [url for url in batch if url not in self.processed_urls]
        
        if not new_urls:
            logger.info("Alle URLs in diesem Batch wurden bereits verarbeitet.")
            return [], []
        
        logger.info(f"Verarbeite Batch mit {len(new_urls)} URLs...")
        
        # Verwende den Zyte-Scraper für den Batch
        results = await self.scraper.fetch_urls(new_urls, self.max_concurrent)
        
        successful = []
        failed = []
        
        for url, result in results.items():
            self.processed_urls.add(url)
            self.stats["processed_urls"] += 1
            
            if result.get("success", False):
                self.successful_urls.add(url)
                self.stats["successful_urls"] += 1
                successful.append(url)
            else:
                error = result.get("error", "Unbekannter Fehler")
                self.failed_urls[url] = error
                self.stats["failed_urls"] += 1
                failed.append((url, error))
        
        return successful, failed
    
    async def _retry_failed_urls(self, max_retries: int = None) -> int:
        """
        Versucht, fehlgeschlagene URLs erneut zu verarbeiten.
        
        Args:
            max_retries: Maximale Anzahl von Wiederholungsversuchen (optional)
            
        Returns:
            Anzahl der erfolgreich wiederholten URLs
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        retried_urls = list(self.failed_urls.keys())
        if not retried_urls:
            logger.info("Keine fehlgeschlagenen URLs für Wiederholungsversuch.")
            return 0
        
        logger.info(f"Wiederhole {len(retried_urls)} fehlgeschlagene URLs...")
        
        # Versuche ein weiteres Mal
        retry_count = 0
        recovered_count = 0
        
        for _ in range(max_retries):
            if not retried_urls:
                break
                
            retry_count += 1
            self.stats["retry_count"] += 1
            
            # Warte vor dem Wiederholungsversuch
            await asyncio.sleep(self.retry_delay)
            
            # Versuche erneut, Batches zu scrapen
            batches = self._split_urls_into_batches(retried_urls)
            still_failed = []
            
            for batch in batches:
                results = await self.scraper.fetch_urls(batch, self.max_concurrent)
                
                for url, result in results.items():
                    if result.get("success", False):
                        # URL war diesmal erfolgreich
                        self.successful_urls.add(url)
                        self.stats["successful_urls"] += 1
                        self.stats["failed_urls"] -= 1
                        del self.failed_urls[url]
                        recovered_count += 1
                    else:
                        # Immer noch fehlgeschlagen
                        error = result.get("error", "Unbekannter Fehler")
                        self.failed_urls[url] = error
                        still_failed.append(url)
            
            retried_urls = still_failed
            logger.info(f"Wiederholungsversuch {retry_count}: {recovered_count} URLs wiederhergestellt, "
                       f"{len(still_failed)} noch fehlgeschlagen.")
        
        return recovered_count
    
    async def _analyze_content(self, urls: List[str]) -> Dict[str, Any]:
        """
        Analysiert den Inhalt der gescrapten URLs mit KI-Modellen.
        
        Args:
            urls: Liste der URLs für die Analyse
            
        Returns:
            Dict mit den Analyseergebnissen
        """
        if not urls:
            logger.info("Keine URLs für die Inhaltsanalyse.")
            return {}
        
        logger.info(f"Analysiere Inhalt für {len(urls)} URLs...")
        
        results = {}
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def analyze_with_semaphore(url: str):
            async with semaphore:
                try:
                    # Lade die gescrapten Daten
                    scraped_file = self.scraper.output_dir / f"{self.scraper._get_safe_filename(url)}.json"
                    
                    if not scraped_file.exists():
                        logger.warning(f"Gescrapte Datei für {url} nicht gefunden: {scraped_file}")
                        return url, {"success": False, "error": "Gescrapte Datei nicht gefunden"}
                    
                    with open(scraped_file, 'r', encoding='utf-8') as f:
                        scraped_data = json.load(f)
                    
                    # Analysiere den Inhalt
                    analyzed_data = await self.analyzer.analyze_content(url, scraped_data)
                    
                    return url, analyzed_data
                    
                except Exception as e:
                    logger.error(f"Fehler bei der Analyse von {url}: {str(e)}")
                    return url, {"success": False, "error": str(e)}
        
        # Analysiere alle URLs parallel
        tasks = [analyze_with_semaphore(url) for url in urls]
        results_list = await asyncio.gather(*tasks)
        
        # Sammle die Ergebnisse
        for url, result in results_list:
            results[url] = result
        
        # Aktualisiere Modellnutzungsdaten in den Statistiken
        self.stats["model_usage"] = self.analyzer.get_model_usage_stats()
        
        return results
    
    async def process_urls(self, urls: List[str], perform_analysis: bool = True) -> Dict[str, Any]:
        """
        Verarbeitet eine Liste von URLs mit Batching, Wiederholungen und Fortschrittsverfolgung.
        
        Args:
            urls: Liste der zu verarbeitenden URLs
            perform_analysis: Ob eine Inhaltsanalyse durchgeführt werden soll
            
        Returns:
            Statistiken über den Verarbeitungsprozess
        """
        try:
            # Initialisiere Statistiken
            self.stats["total_urls"] = len(urls)
            self.stats["start_time"] = datetime.now()
            
            logger.info(f"Starte Verarbeitung von {len(urls)} URLs mit Batch-Größe {self.batch_size} "
                       f"und maximal {self.max_concurrent} gleichzeitigen Anfragen.")
            
            # Teile URLs in Batches auf
            batches = self._split_urls_into_batches(urls)
            total_batches = len(batches)
            logger.info(f"URLs in {total_batches} Batches aufgeteilt.")
            
            all_successful_urls = []
            
            # Verarbeite jeden Batch
            for i, batch in enumerate(batches):
                # Verarbeite den Batch
                successful, failed = await self._process_batch(batch)
                all_successful_urls.extend(successful)
                
                # Logge den Fortschritt
                self._log_progress(i + 1, total_batches)
                
                # Speichere den Fortschritt regelmäßig
                if i % 5 == 0 or i == total_batches - 1:
                    self._save_progress()
            
            # Versuche, fehlgeschlagene URLs erneut zu verarbeiten
            if self.failed_urls:
                logger.info(f"Versuche, {len(self.failed_urls)} fehlgeschlagene URLs erneut zu verarbeiten...")
                recovered = await self._retry_failed_urls()
                logger.info(f"{recovered} URLs erfolgreich wiederhergestellt.")
                
                # Aktualisiere die Liste der erfolgreichen URLs
                all_successful_urls = list(self.successful_urls)
            
            # Führe die Inhaltsanalyse durch, wenn gewünscht
            if perform_analysis and all_successful_urls:
                logger.info(f"Beginne Inhaltsanalyse für {len(all_successful_urls)} erfolgreich gescrapte URLs...")
                analysis_results = await self._analyze_content(all_successful_urls)
                
                # Logge Modellnutzungsstatistiken
                model_stats = self.analyzer.get_model_usage_stats()
                logger.info(f"Inhaltsanalyse abgeschlossen. Gesamtkosten: ${model_stats['total_cost']:.4f}")
            
            # Aktualisiere abschließende Statistiken
            self.stats["end_time"] = datetime.now()
            elapsed = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            
            logger.info(f"Verarbeitung abgeschlossen. Dauer: {elapsed:.1f} Sekunden.")
            logger.info(f"Erfolgreich: {self.stats['successful_urls']}/{self.stats['total_urls']} URLs "
                       f"({self.stats['successful_urls'] / max(1, self.stats['total_urls']) * 100:.1f}%).")
            
            # Speichere den finalen Fortschritt
            self._save_progress()
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Fehler bei der URL-Verarbeitung: {str(e)}")
            self.stats["error"] = str(e)
            self._save_progress()
            raise
        
        finally:
            # Stelle sicher, dass der Fortschritt in jedem Fall gespeichert wird
            self._save_progress()

# Funktion zum Lesen von URLs aus einer Datei
async def process_large_url_list(url_file: str, 
                                batch_size: int = 100, 
                                max_concurrent: int = 10, 
                                perform_analysis: bool = True,
                                zyte_api_key: Optional[str] = None,
                                continue_from: Optional[str] = None) -> Dict[str, Any]:
    """
    Verarbeitet eine große Liste von URLs aus einer Datei.
    
    Args:
        url_file: Pfad zur Datei mit den URLs (eine URL pro Zeile)
        batch_size: Anzahl der URLs pro Batch
        max_concurrent: Maximale Anzahl gleichzeitiger Anfragen
        perform_analysis: Ob eine Inhaltsanalyse durchgeführt werden soll
        zyte_api_key: API-Schlüssel für Zyte (optional)
        continue_from: Pfad zur Fortschrittsdatei für die Fortsetzung (optional)
    
    Returns:
        Statistiken über den Verarbeitungsprozess
    """
    # Prüfe, ob die Datei existiert
    if not os.path.exists(url_file):
        logger.error(f"URL-Datei {url_file} nicht gefunden.")
        return {"error": f"URL-Datei {url_file} nicht gefunden."}
    
    try:
        # Lade URLs aus der Datei
        with open(url_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        logger.info(f"{len(urls)} URLs aus {url_file} geladen.")
        
        # Initialisiere den BatchProcessor
        processor = BatchProcessor(
            batch_size=batch_size,
            max_concurrent=max_concurrent,
            zyte_api_key=zyte_api_key
        )
        
        # Lade den vorherigen Fortschritt, wenn angegeben
        if continue_from:
            progress_file = Path(continue_from)
            if processor._load_progress(progress_file):
                logger.info(f"Fortschritt aus {continue_from} geladen. "
                          f"Fortfahren mit {len(processor.processed_urls)} bereits verarbeiteten URLs.")
        
        # Verarbeite die URLs
        result = await processor.process_urls(urls, perform_analysis)
        return result
        
    except Exception as e:
        logger.error(f"Fehler bei der Verarbeitung von {url_file}: {str(e)}")
        return {"error": str(e)}

# Hauptfunktion für die CLI-Verwendung
async def main():
    parser = argparse.ArgumentParser(description="Verarbeitet eine große Liste von URLs mit Batch-Processing.")
    parser.add_argument("url_file", help="Pfad zur Datei mit den URLs (eine URL pro Zeile)")
    parser.add_argument("--batch-size", type=int, default=100, help="Anzahl der URLs pro Batch")
    parser.add_argument("--max-concurrent", type=int, default=10, help="Maximale Anzahl gleichzeitiger Anfragen")
    parser.add_argument("--no-analysis", action="store_true", help="Keine Inhaltsanalyse durchführen")
    parser.add_argument("--continue-from", help="Pfad zur Fortschrittsdatei für die Fortsetzung")
    parser.add_argument("--zyte-api-key", help="API-Schlüssel für Zyte (optional, sonst aus Umgebungsvariable)")
    
    args = parser.parse_args()
    
    result = await process_large_url_list(
        url_file=args.url_file,
        batch_size=args.batch_size,
        max_concurrent=args.max_concurrent,
        perform_analysis=not args.no_analysis,
        zyte_api_key=args.zyte_api_key,
        continue_from=args.continue_from
    )
    
    # Gib eine Zusammenfassung aus
    if "error" in result:
        print(f"Fehler: {result['error']}")
        return 1
    
    print("\nVerarbeitung abgeschlossen!")
    print(f"Gesamt: {result['total_urls']} URLs")
    print(f"Erfolgreich: {result['successful_urls']} URLs")
    print(f"Fehlgeschlagen: {result['failed_urls']} URLs")
    
    if "model_usage" in result and "total_cost" in result["model_usage"]:
        print(f"Gesamtkosten der KI-Modelle: ${result['model_usage']['total_cost']:.4f}")
    
    return 0

if __name__ == "__main__":
    asyncio.run(main()) 