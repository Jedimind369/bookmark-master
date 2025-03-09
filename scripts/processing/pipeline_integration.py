#!/usr/bin/env python3
"""
pipeline_integration.py

Integriert den Chunk-Prozessor in die bestehende Pipeline.
Bietet Adapter-Funktionen für die verschiedenen Pipeline-Komponenten.
"""

import os
import sys
import json
import gzip
import logging
from pathlib import Path
from typing import List, Dict, Any, Callable, Union, Optional

# Füge das übergeordnete Verzeichnis zum Pfad hinzu, um den Chunk-Prozessor zu importieren
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processing.chunk_processor import ChunkProcessor

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/pipeline_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pipeline_integration")

class PipelineIntegration:
    """
    Integriert den Chunk-Prozessor in die bestehende Pipeline.
    """
    
    def __init__(self, max_workers=2, min_chunk_size=50, max_chunk_size=10000, memory_target_percentage=0.7):
        """
        Initialisiert die Pipeline-Integration.
        
        Args:
            max_workers: Maximale Anzahl paralleler Worker-Threads
            min_chunk_size: Minimale Chunk-Größe in KB
            max_chunk_size: Maximale Chunk-Größe in KB
            memory_target_percentage: Ziel-Speicherauslastung (0.0-1.0)
        """
        self.processor = ChunkProcessor(
            max_workers=max_workers,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
            memory_target_percentage=memory_target_percentage
        )
        
        # Status-Tracking
        self.progress_callback = None
        self.status_callback = None
        self.error_callback = None
        self.complete_callback = None
    
    def set_callbacks(self, progress_callback=None, status_callback=None, 
                     error_callback=None, complete_callback=None):
        """
        Setzt die Callbacks für die Pipeline-Integration.
        
        Args:
            progress_callback: Callback für Fortschrittsupdates
            status_callback: Callback für Statusupdates
            error_callback: Callback für Fehlerbehandlung
            complete_callback: Callback für Abschluss
        """
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.error_callback = error_callback
        self.complete_callback = complete_callback
        
        # Aktualisiere Callbacks im Chunk-Prozessor
        self.processor.callback_progress = progress_callback
        self.processor.callback_status = status_callback
        self.processor.callback_error = error_callback
        self.processor.callback_complete = complete_callback
    
    def process_json_file(self, input_file: Union[str, Path], output_file: Union[str, Path], 
                         processor_func: Callable[[Dict], Dict], compress: bool = True) -> bool:
        """
        Verarbeitet eine JSON-Datei in Chunks.
        
        Args:
            input_file: Pfad zur Eingabe-JSON-Datei
            output_file: Pfad zur Ausgabe-JSON-Datei
            processor_func: Funktion zur Verarbeitung eines JSON-Objekts
            compress: Ob die Ausgabedatei komprimiert werden soll
            
        Returns:
            bool: True, wenn die Verarbeitung erfolgreich war, sonst False
        """
        input_file = Path(input_file)
        output_file = Path(output_file)
        
        # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Lade die JSON-Datei
        try:
            # Definiere eine Funktion zur Verarbeitung eines JSON-Chunks
            def process_json_chunk(chunk_text):
                try:
                    # Parse JSON
                    data = json.loads(chunk_text)
                    
                    # Verarbeite jedes Objekt im Array, wenn es sich um ein Array handelt
                    if isinstance(data, list):
                        return [processor_func(item) for item in data]
                    else:
                        # Verarbeite das Objekt direkt, wenn es kein Array ist
                        return processor_func(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Fehler beim Parsen des JSON-Chunks: {str(e)}")
                    return None
            
            # Lese die Datei und verarbeite sie in Chunks
            if input_file.suffix == '.gz':
                # Für komprimierte Dateien: Entpacke zuerst
                with gzip.open(input_file, 'rt', encoding='utf-8') as f:
                    content = f.read()
                
                result = self.processor.process_text(content, process_json_chunk)
            else:
                # Für unkomprimierte Dateien: Lese direkt
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                result = self.processor.process_text(content, process_json_chunk)
            
            # Prüfe, ob die Verarbeitung erfolgreich war
            if not result.get('success', False):
                logger.error(f"Fehler bei der Verarbeitung von {input_file}: {result.get('error', 'Unbekannter Fehler')}")
                return False
            
            # Sammle die Ergebnisse
            processed_data = []
            for chunk_result in result.get('results', []):
                if chunk_result is not None:
                    if isinstance(chunk_result, list):
                        processed_data.extend(chunk_result)
                    else:
                        processed_data.append(chunk_result)
            
            # Speichere die Ergebnisse
            if compress or output_file.suffix == '.gz':
                with gzip.open(output_file, 'wt', encoding='utf-8') as f:
                    json.dump(processed_data, f, indent=2)
            else:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed_data, f, indent=2)
            
            logger.info(f"Verarbeitung abgeschlossen: {len(processed_data)} Objekte in {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung von {input_file}: {str(e)}", exc_info=True)
            return False
    
    def process_url_list(self, urls: List[str], processor_func: Callable[[str], Dict], 
                        output_file: Union[str, Path], compress: bool = True, 
                        batch_size: int = 100) -> List[Dict]:
        """
        Verarbeitet eine Liste von URLs in Chunks.
        
        Args:
            urls: Liste von URLs
            processor_func: Funktion zur Verarbeitung einer URL
            output_file: Pfad zur Ausgabedatei
            compress: Ob die Ausgabedatei komprimiert werden soll
            batch_size: Größe der Batches für die Verarbeitung
            
        Returns:
            list: Liste der Ergebnisse
        """
        output_file = Path(output_file)
        
        # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Verarbeite URLs in Batches
        all_results = []
        
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i+batch_size]
            logger.info(f"Verarbeite Batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size} mit {len(batch_urls)} URLs")
            
            # Definiere eine Funktion zur Verarbeitung eines URL-Chunks
            def process_url_chunk(chunk_text):
                # Teile den Chunk in Zeilen auf
                url_list = chunk_text.strip().split('\n')
                results = []
                
                for url in url_list:
                    url = url.strip()
                    if url:
                        try:
                            result = processor_func(url)
                            results.append(result)
                        except Exception as e:
                            logger.error(f"Fehler bei der Verarbeitung von URL {url}: {str(e)}")
                
                return results
            
            # Konvertiere die URLs in einen Text
            batch_text = '\n'.join(batch_urls)
            
            # Verarbeite den Batch
            result = self.processor.process_text(batch_text, process_url_chunk)
            
            # Prüfe, ob die Verarbeitung erfolgreich war
            if not result.get('success', False):
                logger.error(f"Fehler bei der Verarbeitung des Batches: {result.get('error', 'Unbekannter Fehler')}")
                continue
            
            # Sammle die Ergebnisse
            batch_results = []
            for chunk_result in result.get('results', []):
                if chunk_result is not None:
                    batch_results.extend(chunk_result)
            
            all_results.extend(batch_results)
            
            # Speichere Zwischenergebnisse
            if output_file:
                batch_output_file = output_file.with_name(f"{output_file.stem}_batch_{i//batch_size + 1}{output_file.suffix}")
                
                if compress or batch_output_file.suffix == '.gz':
                    with gzip.open(batch_output_file, 'wt', encoding='utf-8') as f:
                        json.dump(all_results, f, indent=2)
                else:
                    with open(batch_output_file, 'w', encoding='utf-8') as f:
                        json.dump(all_results, f, indent=2)
                
                logger.info(f"Zwischenergebnisse gespeichert in {batch_output_file}")
        
        # Speichere die Gesamtergebnisse
        if output_file and all_results:
            if compress or output_file.suffix == '.gz':
                with gzip.open(output_file, 'wt', encoding='utf-8') as f:
                    json.dump(all_results, f, indent=2)
            else:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, indent=2)
            
            logger.info(f"Gesamtergebnisse gespeichert in {output_file}")
        
        return all_results
    
    def generate_html_report(self, input_file: Union[str, Path], output_file: Union[str, Path], 
                           template_func: Callable[[List[Dict]], str]) -> bool:
        """
        Generiert einen HTML-Bericht aus einer JSON-Datei.
        
        Args:
            input_file: Pfad zur Eingabe-JSON-Datei
            output_file: Pfad zur Ausgabe-HTML-Datei
            template_func: Funktion zur Generierung des HTML-Templates
            
        Returns:
            bool: True, wenn die Generierung erfolgreich war, sonst False
        """
        input_file = Path(input_file)
        output_file = Path(output_file)
        
        # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Lade die JSON-Datei
            if input_file.suffix == '.gz':
                with gzip.open(input_file, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(input_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Generiere den HTML-Bericht
            html_content = template_func(data)
            
            # Speichere den HTML-Bericht
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML-Bericht generiert: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler bei der Generierung des HTML-Berichts: {str(e)}", exc_info=True)
            return False
    
    def shutdown(self):
        """Fährt den Chunk-Prozessor herunter."""
        self.processor.shutdown()


# Beispiel für die Verwendung
if __name__ == "__main__":
    # Erstelle Pipeline-Integration
    pipeline = PipelineIntegration(max_workers=4)
    
    # Definiere Callbacks
    def progress_callback(progress, stats):
        print(f"Fortschritt: {progress:.1%}")
    
    def status_callback(status, stats):
        print(f"Status: {status}")
    
    def error_callback(message, exception):
        print(f"Fehler: {message} - {str(exception)}")
    
    def complete_callback(stats):
        print(f"Verarbeitung abgeschlossen in {stats['end_time'] - stats['start_time']:.2f} Sekunden")
    
    # Setze Callbacks
    pipeline.set_callbacks(
        progress_callback=progress_callback,
        status_callback=status_callback,
        error_callback=error_callback,
        complete_callback=complete_callback
    )
    
    # Beispiel: Verarbeite eine JSON-Datei
    def process_bookmark(bookmark):
        # Füge eine Beschreibung hinzu, wenn keine vorhanden ist
        if 'description' not in bookmark or not bookmark['description']:
            bookmark['description'] = f"Automatisch generierte Beschreibung für {bookmark.get('title', 'Unbekannt')}"
        return bookmark
    
    # Verarbeite eine JSON-Datei
    pipeline.process_json_file(
        input_file="data/bookmarks/example.json",
        output_file="data/processed/example_processed.json",
        processor_func=process_bookmark
    )
    
    # Fahre Pipeline herunter
    pipeline.shutdown() 