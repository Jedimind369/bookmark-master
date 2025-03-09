#!/usr/bin/env python3
"""
chunk_processor.py

Ein System zur chunk-basierten Verarbeitung großer Dateien mit Speicheroptimierung.
Implementiert die im Fahrplan beschriebenen Optimierungen für Performance und Speicherverbrauch.
"""

import os
import sys
import time
import logging
import threading
import queue
import psutil
import json
from pathlib import Path
from typing import Callable, Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

# Konfiguration für das Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/chunk_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("chunk_processor")

class ChunkProcessor:
    """
    Verarbeitet große Dateien in Chunks, um Speicherverbrauch zu optimieren
    und UI-Blockierungen zu vermeiden.
    """
    
    def __init__(self, 
                 callback_progress: Optional[Callable[[float, Dict], None]] = None,
                 callback_status: Optional[Callable[[str, Dict], None]] = None,
                 callback_error: Optional[Callable[[str, Exception], None]] = None,
                 callback_complete: Optional[Callable[[Dict], None]] = None,
                 max_workers: int = 2,
                 min_chunk_size: int = 50,
                 max_chunk_size: int = 10000,
                 memory_target_percentage: float = 0.7):
        """
        Initialisiert den Chunk-Prozessor.
        
        Args:
            callback_progress: Callback-Funktion für Fortschrittsupdates (0.0-1.0)
            callback_status: Callback-Funktion für Statusupdates
            callback_error: Callback-Funktion für Fehlerbehandlung
            callback_complete: Callback-Funktion bei Abschluss
            max_workers: Maximale Anzahl paralleler Worker-Threads
            min_chunk_size: Minimale Chunk-Größe in KB
            max_chunk_size: Maximale Chunk-Größe in KB
            memory_target_percentage: Ziel-Speicherauslastung (0.0-1.0)
        """
        self.callback_progress = callback_progress
        self.callback_status = callback_status
        self.callback_error = callback_error
        self.callback_complete = callback_complete
        
        self.max_workers = max_workers
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.memory_target_percentage = memory_target_percentage
        
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.workers = []
        self.cancel_requested = False
        self.processing_stats = {
            "start_time": None,
            "end_time": None,
            "total_chunks": 0,
            "processed_chunks": 0,
            "total_size": 0,
            "processed_size": 0,
            "errors": 0,
            "avg_chunk_processing_time": 0,
            "peak_memory_usage": 0,
            "current_memory_usage": 0
        }
        
        # Erstelle Worker-Threads
        for i in range(max_workers):
            worker = threading.Thread(target=self._worker_thread, args=(i,), daemon=True)
            self.workers.append(worker)
            worker.start()
        
        # Thread für Statusupdates
        self.status_thread = threading.Thread(target=self._status_update_thread, daemon=True)
        self.status_thread.start()
        
        logger.info(f"Chunk-Prozessor initialisiert mit {max_workers} Worker-Threads")
    
    def _worker_thread(self, worker_id: int):
        """
        Worker-Thread zur Verarbeitung von Chunks.
        
        Args:
            worker_id: ID des Worker-Threads
        """
        logger.debug(f"Worker {worker_id} gestartet")
        
        while True:
            try:
                # Hole nächsten Task aus der Queue
                task = self.task_queue.get()
                
                # None signalisiert, dass der Thread beendet werden soll
                if task is None:
                    logger.debug(f"Worker {worker_id} wird beendet")
                    self.task_queue.task_done()
                    break
                
                # Extrahiere Task-Informationen
                chunk_id, chunk_data, processor_func, chunk_size, total_chunks = task
                
                # Überprüfe, ob Abbruch angefordert wurde
                if self.cancel_requested:
                    logger.info(f"Worker {worker_id}: Abbruch angefordert, überspringe Chunk {chunk_id}")
                    self.task_queue.task_done()
                    continue
                
                # Verarbeite den Chunk
                start_time = time.time()
                try:
                    result = processor_func(chunk_data)
                    processing_time = time.time() - start_time
                    
                    # Speichere Ergebnis
                    self.result_queue.put((chunk_id, result, processing_time, None))
                    
                except Exception as e:
                    logger.error(f"Fehler bei der Verarbeitung von Chunk {chunk_id}: {str(e)}", exc_info=True)
                    self.result_queue.put((chunk_id, None, time.time() - start_time, e))
                    
                    if self.callback_error:
                        self.callback_error(f"Fehler bei Chunk {chunk_id}", e)
                
                finally:
                    # Markiere Task als erledigt
                    self.task_queue.task_done()
                    
            except Exception as e:
                logger.error(f"Unerwarteter Fehler in Worker {worker_id}: {str(e)}", exc_info=True)
    
    def _status_update_thread(self):
        """Thread für regelmäßige Statusupdates und Speicherüberwachung."""
        logger.debug("Status-Update-Thread gestartet")
        
        while True:
            try:
                # Aktualisiere Speichernutzung
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                current_memory = memory_info.rss / (1024 * 1024)  # In MB
                
                self.processing_stats["current_memory_usage"] = current_memory
                if current_memory > self.processing_stats["peak_memory_usage"]:
                    self.processing_stats["peak_memory_usage"] = current_memory
                
                # Sende Statusupdate, wenn Callback vorhanden
                if self.callback_status and self.processing_stats["start_time"] is not None:
                    status_message = self._generate_status_message()
                    self.callback_status(status_message, self.processing_stats)
                
                # Prüfe, ob alle Worker beendet werden sollen
                if all(not worker.is_alive() for worker in self.workers):
                    logger.debug("Alle Worker beendet, Status-Thread wird beendet")
                    break
                
                # Warte kurz vor dem nächsten Update
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Fehler im Status-Update-Thread: {str(e)}", exc_info=True)
    
    def _generate_status_message(self) -> str:
        """Generiert eine Statusmeldung basierend auf den aktuellen Verarbeitungsstatistiken."""
        if self.processing_stats["total_chunks"] == 0:
            return "Warte auf Verarbeitung..."
        
        progress = self.processing_stats["processed_chunks"] / self.processing_stats["total_chunks"]
        elapsed = time.time() - self.processing_stats["start_time"]
        
        if progress > 0:
            estimated_total = elapsed / progress
            remaining = estimated_total - elapsed
            time_str = f", ca. {int(remaining)} Sekunden verbleibend"
        else:
            time_str = ""
        
        return (f"Verarbeite Chunk {self.processing_stats['processed_chunks']}/{self.processing_stats['total_chunks']} "
                f"({progress:.1%}{time_str})")
    
    def determine_chunk_size(self, file_size: int) -> int:
        """
        Bestimmt die optimale Chunk-Größe basierend auf Dateigröße und verfügbarem Speicher.
        
        Args:
            file_size: Größe der Datei in Bytes
            
        Returns:
            Optimale Chunk-Größe in Bytes
        """
        # Verfügbarer Speicher
        available_memory = psutil.virtual_memory().available
        target_memory = available_memory * self.memory_target_percentage
        
        # Berechne Chunk-Größe basierend auf Dateigröße und verfügbarem Speicher
        # Wir wollen etwa 100 Chunks für große Dateien, aber nicht zu kleine Chunks
        suggested_size = max(file_size // 100, self.min_chunk_size * 1024)
        
        # Begrenze auf den verfügbaren Speicher und die maximale Chunk-Größe
        max_size_by_memory = target_memory // self.max_workers
        chunk_size = min(suggested_size, max_size_by_memory, self.max_chunk_size * 1024)
        
        # Stelle sicher, dass die Chunk-Größe mindestens die Mindestgröße hat
        chunk_size = max(chunk_size, self.min_chunk_size * 1024)
        
        logger.info(f"Bestimmte Chunk-Größe: {chunk_size / 1024:.2f} KB (Dateigröße: {file_size / 1024 / 1024:.2f} MB, "
                   f"Verfügbarer Speicher: {available_memory / 1024 / 1024:.2f} MB)")
        
        return int(chunk_size)
    
    def process_file(self, file_path: Union[str, Path], processor_func: Callable[[bytes], Any]) -> Dict[str, Any]:
        """
        Verarbeitet eine Datei in Chunks.
        
        Args:
            file_path: Pfad zur Datei
            processor_func: Funktion zur Verarbeitung eines Chunks
            
        Returns:
            Dictionary mit Verarbeitungsstatistiken und Ergebnissen
        """
        file_path = Path(file_path)
        if not file_path.exists():
            error_msg = f"Datei nicht gefunden: {file_path}"
            logger.error(error_msg)
            if self.callback_error:
                self.callback_error(error_msg, FileNotFoundError(error_msg))
            return {"success": False, "error": error_msg}
        
        # Setze Verarbeitungsstatistiken zurück
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        current_memory = memory_info.rss / (1024 * 1024)  # In MB
        
        self.processing_stats = {
            "start_time": time.time(),
            "end_time": None,
            "total_chunks": 0,
            "processed_chunks": 0,
            "total_size": file_path.stat().st_size,
            "processed_size": 0,
            "errors": 0,
            "avg_chunk_processing_time": 0,
            "peak_memory_usage": current_memory,
            "current_memory_usage": current_memory,
            "results": [],
            "file_path": str(file_path)
        }
        
        # Bestimme Chunk-Größe
        chunk_size = self.determine_chunk_size(self.processing_stats["total_size"])
        
        # Berechne Anzahl der Chunks
        total_chunks = (self.processing_stats["total_size"] + chunk_size - 1) // chunk_size
        self.processing_stats["total_chunks"] = total_chunks
        
        logger.info(f"Starte Verarbeitung von {file_path} in {total_chunks} Chunks")
        
        if self.callback_status:
            self.callback_status("Starte Verarbeitung...", self.processing_stats)
        
        # Verarbeite Datei in Chunks
        try:
            with open(file_path, 'rb') as f:
                chunk_id = 0
                while True:
                    # Überprüfe, ob Abbruch angefordert wurde
                    if self.cancel_requested:
                        logger.info("Verarbeitung abgebrochen")
                        break
                    
                    # Lese nächsten Chunk
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    
                    # Füge Chunk zur Verarbeitungsqueue hinzu
                    self.task_queue.put((chunk_id, chunk_data, processor_func, chunk_size, total_chunks))
                    chunk_id += 1
                
                # Warte, bis alle Chunks verarbeitet wurden
                self.task_queue.join()
                
                # Sammle Ergebnisse
                results = []
                total_processing_time = 0
                
                # Hole alle Ergebnisse aus der Queue
                while not self.result_queue.empty():
                    chunk_id, result, processing_time, error = self.result_queue.get()
                    
                    if error:
                        self.processing_stats["errors"] += 1
                    else:
                        self.processing_stats["processed_chunks"] += 1
                        self.processing_stats["processed_size"] += len(chunk_data) if chunk_id < total_chunks else 0
                        total_processing_time += processing_time
                        
                        # Füge Ergebnis zur Liste hinzu
                        results.append((chunk_id, result))
                    
                    # Sende Fortschrittsupdate
                    if self.callback_progress:
                        progress = self.processing_stats["processed_chunks"] / total_chunks
                        self.callback_progress(progress, self.processing_stats)
                
                # Sortiere Ergebnisse nach Chunk-ID
                results.sort(key=lambda x: x[0])
                self.processing_stats["results"] = [r[1] for r in results]
                
                # Berechne durchschnittliche Verarbeitungszeit
                if self.processing_stats["processed_chunks"] > 0:
                    self.processing_stats["avg_chunk_processing_time"] = (
                        total_processing_time / self.processing_stats["processed_chunks"]
                    )
                
                # Setze Endzeit
                self.processing_stats["end_time"] = time.time()
                
                # Sende Abschluss-Callback
                if self.callback_complete and not self.cancel_requested:
                    self.callback_complete(self.processing_stats)
                
                logger.info(f"Verarbeitung abgeschlossen: {self.processing_stats['processed_chunks']}/{total_chunks} "
                           f"Chunks verarbeitet, {self.processing_stats['errors']} Fehler")
                
                return {
                    "success": True,
                    "stats": self.processing_stats,
                    "results": self.processing_stats["results"]
                }
                
        except Exception as e:
            error_msg = f"Fehler bei der Verarbeitung von {file_path}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            if self.callback_error:
                self.callback_error(error_msg, e)
            
            return {"success": False, "error": error_msg}
    
    def process_text(self, text: str, processor_func: Callable[[str], Any], 
                    chunk_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Verarbeitet einen Text in Chunks.
        
        Args:
            text: Zu verarbeitender Text
            processor_func: Funktion zur Verarbeitung eines Chunks
            chunk_size: Optionale manuelle Chunk-Größe in Zeichen
            
        Returns:
            Dictionary mit Verarbeitungsstatistiken und Ergebnissen
        """
        # Konvertiere Text in Bytes für einheitliche Verarbeitung
        text_bytes = text.encode('utf-8')
        text_size = len(text_bytes)
        
        # Setze Verarbeitungsstatistiken zurück
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        current_memory = memory_info.rss / (1024 * 1024)  # In MB
        
        self.processing_stats = {
            "start_time": time.time(),
            "end_time": None,
            "total_chunks": 0,
            "processed_chunks": 0,
            "total_size": text_size,
            "processed_size": 0,
            "errors": 0,
            "avg_chunk_processing_time": 0,
            "peak_memory_usage": current_memory,
            "current_memory_usage": current_memory,
            "results": []
        }
        
        # Bestimme Chunk-Größe
        if chunk_size is None:
            chunk_size_bytes = self.determine_chunk_size(text_size)
        else:
            # Konvertiere Zeichen-Chunk-Größe in ungefähre Byte-Größe
            chunk_size_bytes = chunk_size * 4  # Großzügige Schätzung für UTF-8
        
        # Berechne Anzahl der Chunks
        total_chunks = (text_size + chunk_size_bytes - 1) // chunk_size_bytes
        self.processing_stats["total_chunks"] = total_chunks
        
        logger.info(f"Starte Verarbeitung von Text ({text_size} Bytes) in {total_chunks} Chunks")
        
        if self.callback_status:
            self.callback_status("Starte Textverarbeitung...", self.processing_stats)
        
        # Verarbeite Text in Chunks
        try:
            chunk_id = 0
            offset = 0
            
            while offset < text_size:
                # Überprüfe, ob Abbruch angefordert wurde
                if self.cancel_requested:
                    logger.info("Verarbeitung abgebrochen")
                    break
                
                # Extrahiere nächsten Chunk
                end_offset = min(offset + chunk_size_bytes, text_size)
                chunk_bytes = text_bytes[offset:end_offset]
                
                # Konvertiere zurück zu Text
                chunk_text = chunk_bytes.decode('utf-8')
                
                # Erstelle eine Wrapper-Funktion, die den Text-Chunk verarbeitet
                def process_text_chunk(chunk_bytes):
                    chunk_text = chunk_bytes.decode('utf-8')
                    return processor_func(chunk_text)
                
                # Füge Chunk zur Verarbeitungsqueue hinzu
                self.task_queue.put((chunk_id, chunk_bytes, process_text_chunk, chunk_size_bytes, total_chunks))
                
                offset = end_offset
                chunk_id += 1
            
            # Warte, bis alle Chunks verarbeitet wurden
            self.task_queue.join()
            
            # Sammle Ergebnisse
            results = []
            total_processing_time = 0
            
            # Hole alle Ergebnisse aus der Queue
            while not self.result_queue.empty():
                chunk_id, result, processing_time, error = self.result_queue.get()
                
                if error:
                    self.processing_stats["errors"] += 1
                else:
                    self.processing_stats["processed_chunks"] += 1
                    chunk_size = min(chunk_size_bytes, text_size - chunk_id * chunk_size_bytes)
                    self.processing_stats["processed_size"] += chunk_size
                    total_processing_time += processing_time
                    
                    # Füge Ergebnis zur Liste hinzu
                    results.append((chunk_id, result))
                
                # Sende Fortschrittsupdate
                if self.callback_progress:
                    progress = self.processing_stats["processed_chunks"] / total_chunks
                    self.callback_progress(progress, self.processing_stats)
            
            # Sortiere Ergebnisse nach Chunk-ID
            results.sort(key=lambda x: x[0])
            self.processing_stats["results"] = [r[1] for r in results]
            
            # Berechne durchschnittliche Verarbeitungszeit
            if self.processing_stats["processed_chunks"] > 0:
                self.processing_stats["avg_chunk_processing_time"] = (
                    total_processing_time / self.processing_stats["processed_chunks"]
                )
            
            # Setze Endzeit
            self.processing_stats["end_time"] = time.time()
            
            # Sende Abschluss-Callback
            if self.callback_complete and not self.cancel_requested:
                self.callback_complete(self.processing_stats)
            
            logger.info(f"Textverarbeitung abgeschlossen: {self.processing_stats['processed_chunks']}/{total_chunks} "
                       f"Chunks verarbeitet, {self.processing_stats['errors']} Fehler")
            
            return {
                "success": True,
                "stats": self.processing_stats,
                "results": self.processing_stats["results"]
            }
            
        except Exception as e:
            error_msg = f"Fehler bei der Textverarbeitung: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            if self.callback_error:
                self.callback_error(error_msg, e)
            
            return {"success": False, "error": error_msg}
    
    def cancel(self):
        """Bricht die Verarbeitung ab."""
        logger.info("Abbruch der Verarbeitung angefordert")
        self.cancel_requested = True
    
    def shutdown(self):
        """Fährt den Chunk-Prozessor herunter und beendet alle Worker-Threads."""
        logger.info("Fahre Chunk-Prozessor herunter")
        
        # Setze Abbruch-Flag
        self.cancel_requested = True
        
        # Sende None an alle Worker, um sie zu beenden
        for _ in range(len(self.workers)):
            self.task_queue.put(None)
        
        # Warte auf Beendigung aller Worker
        for worker in self.workers:
            worker.join(timeout=2.0)
        
        logger.info("Chunk-Prozessor heruntergefahren")


# Beispiel für die Verwendung
if __name__ == "__main__":
    # Beispiel-Callback-Funktionen
    def progress_callback(progress, stats):
        print(f"Fortschritt: {progress:.1%}")
    
    def status_callback(status, stats):
        print(f"Status: {status}")
    
    def error_callback(message, exception):
        print(f"Fehler: {message} - {str(exception)}")
    
    def complete_callback(stats):
        print(f"Verarbeitung abgeschlossen in {stats['end_time'] - stats['start_time']:.2f} Sekunden")
        print(f"Durchschnittliche Chunk-Verarbeitungszeit: {stats['avg_chunk_processing_time']:.4f} Sekunden")
        print(f"Maximaler Speicherverbrauch: {stats['peak_memory_usage']:.2f} MB")
    
    # Beispiel-Verarbeitungsfunktion
    def process_chunk(chunk):
        # Simuliere Verarbeitung
        time.sleep(0.1)
        return len(chunk)
    
    # Erstelle Chunk-Prozessor
    processor = ChunkProcessor(
        callback_progress=progress_callback,
        callback_status=status_callback,
        callback_error=error_callback,
        callback_complete=complete_callback
    )
    
    # Verarbeite eine Beispieldatei
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        result = processor.process_file(file_path, process_chunk)
        print(f"Ergebnis: {result['success']}")
    else:
        # Verarbeite einen Beispieltext
        text = "Dies ist ein Beispieltext, der in Chunks verarbeitet wird." * 1000
        result = processor.process_text(text, lambda chunk: len(chunk))
        print(f"Ergebnis: {result['success']}")
    
    # Fahre Prozessor herunter
    processor.shutdown() 