#!/usr/bin/env python3
"""
api_monitor_integration.py

Integriert den Chunk-Prozessor mit dem API-Monitoring-System.
Demonstriert die Verwendung des Chunk-Prozessors für die Verarbeitung großer API-Logs.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

# Füge das übergeordnete Verzeichnis zum Pfad hinzu, um die Module zu importieren
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processing.chunk_processor import ChunkProcessor
from monitoring.api_monitor import APIMonitor

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/api_monitor_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api_monitor_integration")

class APILogProcessor:
    """
    Verarbeitet API-Logs mit dem Chunk-Prozessor und integriert mit dem API-Monitor.
    """
    
    def __init__(self, api_monitor=None):
        """
        Initialisiert den API-Log-Prozessor.
        
        Args:
            api_monitor: Optionale Instanz des API-Monitors
        """
        # Erstelle API-Monitor, falls nicht übergeben
        self.api_monitor = api_monitor or APIMonitor()
        
        # Erstelle Chunk-Prozessor
        self.processor = ChunkProcessor(
            callback_progress=self.update_progress,
            callback_status=self.update_status,
            callback_error=self.handle_error,
            callback_complete=self.handle_complete,
            max_workers=2,
            min_chunk_size=50,
            max_chunk_size=5000
        )
        
        # Status-Tracking
        self.current_file = None
        self.start_time = None
        self.processed_entries = 0
        self.total_cost = 0.0
    
    def update_progress(self, progress, stats):
        """Callback für Fortschrittsupdates."""
        if self.current_file:
            logger.info(f"Verarbeite {self.current_file}: {progress:.1%} abgeschlossen")
    
    def update_status(self, status, stats):
        """Callback für Statusupdates."""
        logger.info(f"Status: {status}")
    
    def handle_error(self, message, exception):
        """Callback für Fehlerbehandlung."""
        logger.error(f"Fehler: {message} - {str(exception)}")
    
    def handle_complete(self, stats):
        """Callback für Abschluss der Verarbeitung."""
        duration = stats["end_time"] - stats["start_time"]
        logger.info(f"Verarbeitung von {self.current_file} abgeschlossen in {duration:.2f} Sekunden")
        logger.info(f"Verarbeitete Einträge: {self.processed_entries}")
        logger.info(f"Gesamtkosten: ${self.total_cost:.2f}")
        
        # Speichere Kontext-Informationen im API-Monitor
        self.api_monitor.store_context_information(
            f"log_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            {
                "file": self.current_file,
                "duration": duration,
                "processed_entries": self.processed_entries,
                "total_cost": self.total_cost,
                "peak_memory_usage": stats["peak_memory_usage"],
                "avg_chunk_processing_time": stats["avg_chunk_processing_time"]
            }
        )
    
    def process_log_file(self, file_path):
        """
        Verarbeitet eine API-Log-Datei in Chunks.
        
        Args:
            file_path: Pfad zur Log-Datei
            
        Returns:
            Dictionary mit Verarbeitungsstatistiken
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"Datei nicht gefunden: {file_path}")
            return {"success": False, "error": "Datei nicht gefunden"}
        
        # Setze Status
        self.current_file = str(file_path)
        self.start_time = time.time()
        self.processed_entries = 0
        self.total_cost = 0.0
        
        logger.info(f"Starte Verarbeitung von {file_path}")
        
        # Bestimme Dateityp
        if file_path.suffix.lower() == '.json':
            # JSON-Datei: Verarbeite als Text
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            result = self.processor.process_text(content, self._process_json_chunk)
            
        else:
            # Textdatei: Verarbeite zeilenweise
            result = self.processor.process_file(file_path, self._process_log_chunk)
        
        return result
    
    def _process_json_chunk(self, chunk):
        """
        Verarbeitet einen JSON-Chunk.
        
        Args:
            chunk: JSON-Text als String
            
        Returns:
            Anzahl der verarbeiteten Einträge und Gesamtkosten
        """
        try:
            # Versuche, den Chunk als JSON zu parsen
            # Wenn der Chunk kein vollständiges JSON-Objekt enthält, füge Klammern hinzu
            if not chunk.strip().startswith('{') and not chunk.strip().startswith('['):
                chunk = '{' + chunk + '}'
            
            data = json.loads(chunk)
            
            # Verarbeite je nach JSON-Struktur
            if isinstance(data, dict):
                # Einzelner Eintrag
                return self._process_api_entry(data)
            elif isinstance(data, list):
                # Liste von Einträgen
                results = [self._process_api_entry(entry) for entry in data]
                return {
                    "entries": len(results),
                    "cost": sum(result.get("cost", 0) for result in results)
                }
            else:
                logger.warning(f"Unbekanntes JSON-Format: {type(data)}")
                return {"entries": 0, "cost": 0}
                
        except json.JSONDecodeError as e:
            logger.warning(f"Fehler beim Parsen des JSON-Chunks: {str(e)}")
            # Versuche, einzelne Zeilen zu verarbeiten
            lines = chunk.strip().split('\n')
            results = []
            
            for line in lines:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        results.append(self._process_api_entry(entry))
                    except json.JSONDecodeError:
                        pass
            
            return {
                "entries": len(results),
                "cost": sum(result.get("cost", 0) for result in results)
            }
    
    def _process_log_chunk(self, chunk):
        """
        Verarbeitet einen Log-Chunk.
        
        Args:
            chunk: Bytes-Objekt mit Log-Daten
            
        Returns:
            Anzahl der verarbeiteten Einträge und Gesamtkosten
        """
        # Konvertiere Bytes zu Text
        text = chunk.decode('utf-8', errors='replace')
        
        # Verarbeite Zeilen
        lines = text.split('\n')
        results = []
        
        for line in lines:
            if line.strip():
                try:
                    # Versuche, die Zeile als JSON zu parsen
                    entry = json.loads(line)
                    results.append(self._process_api_entry(entry))
                except json.JSONDecodeError:
                    # Keine JSON-Zeile, versuche reguläres Log-Format
                    result = self._process_log_line(line)
                    if result:
                        results.append(result)
        
        return {
            "entries": len(results),
            "cost": sum(result.get("cost", 0) for result in results)
        }
    
    def _process_api_entry(self, entry):
        """
        Verarbeitet einen API-Eintrag.
        
        Args:
            entry: Dictionary mit API-Eintrag
            
        Returns:
            Verarbeitungsergebnis
        """
        # Extrahiere relevante Informationen
        model = entry.get("model", "unknown")
        tokens_in = entry.get("prompt_tokens", 0) or entry.get("input_tokens", 0)
        tokens_out = entry.get("completion_tokens", 0) or entry.get("output_tokens", 0)
        cost = entry.get("cost", 0)
        
        # Wenn keine Kosten angegeben sind, berechne sie
        if cost == 0 and (tokens_in > 0 or tokens_out > 0):
            # Versuche, Kosten zu berechnen
            try:
                cost = self.api_monitor.calculate_cost(model, tokens_in, tokens_out)
            except Exception as e:
                logger.warning(f"Fehler bei der Kostenberechnung: {str(e)}")
        
        # Aktualisiere Statistiken
        self.processed_entries += 1
        self.total_cost += cost
        
        # Zeichne API-Aufruf auf, wenn Modell und Kosten bekannt sind
        if model != "unknown" and cost > 0:
            self.api_monitor.record_api_call(
                model=model,
                cost=cost,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                task="log_processing"
            )
        
        return {
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost": cost
        }
    
    def _process_log_line(self, line):
        """
        Verarbeitet eine Log-Zeile.
        
        Args:
            line: Log-Zeile als String
            
        Returns:
            Verarbeitungsergebnis oder None, wenn die Zeile nicht relevant ist
        """
        # Einfache Heuristik zur Erkennung von API-Aufrufen in Logs
        if "api" in line.lower() and ("tokens" in line.lower() or "cost" in line.lower()):
            # Versuche, Modell zu extrahieren
            model = "unknown"
            for model_name in ["gpt-4", "gpt-3.5", "claude", "llama", "mistral", "gemini"]:
                if model_name in line.lower():
                    model = model_name
                    break
            
            # Versuche, Token-Zahlen zu extrahieren
            import re
            tokens_in = 0
            tokens_out = 0
            cost = 0
            
            # Suche nach Token-Zahlen
            input_match = re.search(r"input[_\s]*tokens:?\s*(\d+)", line, re.IGNORECASE)
            if input_match:
                tokens_in = int(input_match.group(1))
            
            output_match = re.search(r"output[_\s]*tokens:?\s*(\d+)", line, re.IGNORECASE)
            if output_match:
                tokens_out = int(output_match.group(1))
            
            # Suche nach Kosten
            cost_match = re.search(r"cost:?\s*\$?(\d+\.\d+)", line, re.IGNORECASE)
            if cost_match:
                cost = float(cost_match.group(1))
            
            # Aktualisiere Statistiken
            self.processed_entries += 1
            self.total_cost += cost
            
            # Zeichne API-Aufruf auf, wenn Kosten bekannt sind
            if cost > 0:
                self.api_monitor.record_api_call(
                    model=model,
                    cost=cost,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    task="log_processing"
                )
            
            return {
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost": cost
            }
        
        return None
    
    def shutdown(self):
        """Fährt den Prozessor herunter."""
        self.processor.shutdown()


def main():
    """Hauptfunktion."""
    import argparse
    
    # Parse Kommandozeilenargumente
    parser = argparse.ArgumentParser(description="Verarbeitet API-Logs mit dem Chunk-Prozessor.")
    parser.add_argument("file", help="Pfad zur Log-Datei")
    parser.add_argument("--workers", type=int, default=2, help="Anzahl der Worker-Threads")
    parser.add_argument("--min-chunk", type=int, default=50, help="Minimale Chunk-Größe in KB")
    parser.add_argument("--max-chunk", type=int, default=5000, help="Maximale Chunk-Größe in KB")
    args = parser.parse_args()
    
    # Erstelle API-Monitor
    api_monitor = APIMonitor()
    
    # Erstelle API-Log-Prozessor
    processor = APILogProcessor(api_monitor)
    
    # Aktualisiere Prozessor-Konfiguration
    processor.processor.max_workers = args.workers
    processor.processor.min_chunk_size = args.min_chunk
    processor.processor.max_chunk_size = args.max_chunk
    
    try:
        # Verarbeite Log-Datei
        result = processor.process_log_file(args.file)
        
        if result["success"]:
            logger.info("Verarbeitung erfolgreich abgeschlossen")
            
            # Zeige Nutzungsstatistiken
            api_monitor.show_usage(detailed=True)
        else:
            logger.error(f"Fehler bei der Verarbeitung: {result.get('error', 'Unbekannter Fehler')}")
    
    finally:
        # Fahre Prozessor herunter
        processor.shutdown()


if __name__ == "__main__":
    main() 