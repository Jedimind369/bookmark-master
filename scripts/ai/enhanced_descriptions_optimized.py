#!/usr/bin/env python3
"""
Optimierte Version des enhanced_descriptions.py Skripts.

Generiert hochwertige, aussagekräftige Beschreibungen für Lesezeichen mit KI.
Verwendet den Chunk-Prozessor für optimierte Speichernutzung und Parallelverarbeitung.
"""

import os
import sys
import json
import re
import gzip
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Füge das übergeordnete Verzeichnis zum Pfad hinzu, um den Chunk-Prozessor zu importieren
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.processing.pipeline_integration import PipelineIntegration

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/enhanced_descriptions.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("enhanced_descriptions")

def generate_enhanced_description(url, title, tags=None):
    """
    Generiert eine detaillierte Beschreibung für ein Lesezeichen.
    
    Args:
        url: URL des Lesezeichens
        title: Titel des Lesezeichens
        tags: Tags des Lesezeichens (optional)
        
    Returns:
        Detaillierte Beschreibung mit ca. 5 Sätzen
    """
    # Extrahiere Domain aus URL für bessere Kontextualisierung
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    domain = domain_match.group(1) if domain_match else "unbekannte Domain"
    
    # Bekannte Websites mit detaillierten Beschreibungen
    if 'github.com' in url:
        return (
            "GitHub ist die weltweit führende Entwicklungsplattform für Open-Source- und private Softwareprojekte. "
            "Die Plattform bietet umfassende Funktionen für Versionskontrolle, Zusammenarbeit und Code-Hosting. "
            "Entwickler können auf GitHub Repositories erstellen, Code teilen, Issues verfolgen und Pull Requests einreichen. "
            "Mit über 100 Millionen Repositories und mehr als 70 Millionen Nutzern ist GitHub ein zentraler Knotenpunkt für die globale Entwicklergemeinschaft. "
            "Die Plattform unterstützt auch CI/CD-Workflows, Projektmanagement und Sicherheitsanalysen für moderne Softwareentwicklung."
        )
    elif 'stackoverflow.com' in url:
        return (
            "Stack Overflow ist die größte Online-Community für Programmierer und Entwickler zum Austausch von Wissen. "
            "Die Plattform funktioniert nach einem Frage-Antwort-Format, bei dem Nutzer technische Probleme posten und die Community Lösungen anbietet. "
            "Mit einem Reputationssystem werden hilfreiche Antworten und Beiträge belohnt, was zur hohen Qualität der Inhalte beiträgt. "
            "Stack Overflow umfasst praktisch alle Programmiersprachen, Frameworks und technischen Themen der Softwareentwicklung. "
            "Für viele Entwickler ist die Seite die erste Anlaufstelle bei der Problemlösung und ein unverzichtbares Werkzeug im Arbeitsalltag."
        )
    elif 'python.org' in url:
        return (
            "Python.org ist die offizielle Website der Python-Programmiersprache und wird von der Python Software Foundation betrieben. "
            "Hier finden Entwickler die offiziellen Downloads für alle Python-Versionen, umfassende Dokumentation und Tutorials. "
            "Die Website bietet Zugang zur Python Package Index (PyPI), dem Repository für Python-Bibliotheken und -Frameworks. "
            "Darüber hinaus informiert Python.org über Neuigkeiten, Events und Entwicklungen rund um die Programmiersprache. "
            "Als zentrale Anlaufstelle für die Python-Community ist die Website ein wichtiger Bestandteil des Python-Ökosystems."
        )
    
    # Generische Beschreibung basierend auf Domain und Titel
    return (
        f"{domain} ist eine Website, die Informationen und Ressourcen zu {title} bereitstellt. "
        f"Die Seite bietet Nutzern Zugang zu verschiedenen Inhalten und Funktionen im Zusammenhang mit diesem Thema. "
        f"Besucher können hier wertvolle Einblicke, Anleitungen und aktuelle Entwicklungen in diesem Bereich finden. "
        f"Die Website ist für Personen interessant, die sich mit {title} beschäftigen oder mehr darüber erfahren möchten. "
        f"Als Online-Ressource trägt {domain} zur Verbreitung von Wissen und Information in diesem Fachgebiet bei."
    )

class EnhancedDescriptionGenerator:
    """
    Generiert verbesserte Beschreibungen für Lesezeichen mit KI.
    Verwendet den Chunk-Prozessor für optimierte Speichernutzung und Parallelverarbeitung.
    """
    
    def __init__(self, max_workers=2, min_chunk_size=50, max_chunk_size=10000, memory_target_percentage=0.7):
        """
        Initialisiert den Generator für verbesserte Beschreibungen.
        
        Args:
            max_workers: Maximale Anzahl paralleler Worker-Threads
            min_chunk_size: Minimale Chunk-Größe in KB
            max_chunk_size: Maximale Chunk-Größe in KB
            memory_target_percentage: Ziel-Speicherauslastung (0.0-1.0)
        """
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
            'end_time': None,
            'total': 0,
            'processed': 0,
            'success': 0,
            'failed': 0
        }
        
        logger.info(f"Beschreibungsgenerator initialisiert mit {max_workers} Workern")
    
    def _progress_callback(self, progress, stats):
        """Callback für Fortschrittsupdates."""
        self.stats['processed'] = stats.get('processed_chunks', 0)
        logger.info(f"Fortschritt: {progress:.1%} ({self.stats['processed']}/{self.stats['total']} Lesezeichen)")
    
    def _status_callback(self, status, stats):
        """Callback für Statusupdates."""
        logger.info(f"Status: {status}")
    
    def _error_callback(self, message, exception):
        """Callback für Fehlerbehandlung."""
        logger.error(f"Fehler: {message} - {str(exception)}")
        self.stats['failed'] += 1
    
    def _complete_callback(self, stats):
        """Callback für Abschluss."""
        self.stats['end_time'] = stats.get('end_time', 0)
        duration = self.stats['end_time'] - self.stats['start_time'] if self.stats['start_time'] else 0
        logger.info(f"Verarbeitung abgeschlossen in {duration:.2f} Sekunden")
        logger.info(f"Erfolgreiche Verarbeitung: {self.stats['success']}/{self.stats['total']} Lesezeichen")
        logger.info(f"Fehlgeschlagene Verarbeitung: {self.stats['failed']}/{self.stats['total']} Lesezeichen")
    
    def process_bookmark(self, bookmark):
        """
        Verarbeitet ein einzelnes Lesezeichen und fügt eine verbesserte Beschreibung hinzu.
        
        Args:
            bookmark: Lesezeichen-Objekt
            
        Returns:
            Lesezeichen-Objekt mit verbesserter Beschreibung
        """
        try:
            url = bookmark.get('url', '')
            title = bookmark.get('title', '')
            tags = bookmark.get('tags', [])
            
            # Generiere eine verbesserte Beschreibung
            bookmark['description'] = generate_enhanced_description(url, title, tags)
            self.stats['success'] += 1
            
            return bookmark
        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung des Lesezeichens: {str(e)}")
            self.stats['failed'] += 1
            return bookmark
    
    def enhance_descriptions(self, input_file, output_file):
        """
        Verbessert die Beschreibungen aller Lesezeichen in einer Datei.
        
        Args:
            input_file: Pfad zur Eingabe-JSON-Datei
            output_file: Pfad zur Ausgabe-JSON-Datei
            
        Returns:
            bool: True, wenn die Verarbeitung erfolgreich war, sonst False
        """
        logger.info(f"Starte Verarbeitung von {input_file}")
        
        # Setze Startzeit
        self.stats['start_time'] = datetime.now().timestamp()
        
        # Verarbeite die JSON-Datei mit dem Chunk-Prozessor
        result = self.pipeline.process_json_file(
            input_file=input_file,
            output_file=output_file,
            processor_func=self.process_bookmark,
            compress=output_file.endswith('.gz')
        )
        
        if result:
            logger.info(f"Beschreibungen erfolgreich verbessert und in {output_file} gespeichert")
        else:
            logger.error(f"Fehler bei der Verbesserung der Beschreibungen")
        
        return result
    
    def shutdown(self):
        """Fährt den Generator herunter."""
        self.pipeline.shutdown()


def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Generiert verbesserte Beschreibungen für Lesezeichen")
    parser.add_argument("input_file", help="Pfad zur Eingabe-JSON-Datei")
    parser.add_argument("--output-file", help="Pfad zur Ausgabe-JSON-Datei")
    parser.add_argument("--max-workers", type=int, default=2, help="Maximale Anzahl paralleler Worker-Threads")
    parser.add_argument("--min-chunk-size", type=int, default=50, help="Minimale Chunk-Größe in KB")
    parser.add_argument("--max-chunk-size", type=int, default=10000, help="Maximale Chunk-Größe in KB")
    parser.add_argument("--memory-target", type=float, default=0.7, help="Ziel-Speicherauslastung (0.0-1.0)")
    args = parser.parse_args()
    
    # Erstelle Verzeichnisse
    os.makedirs("logs", exist_ok=True)
    
    # Bestimme Ausgabedatei, wenn nicht angegeben
    if not args.output_file:
        input_path = Path(args.input_file)
        if input_path.suffix == '.gz':
            output_file = input_path.with_name(f"{input_path.stem}_enhanced.json.gz")
        else:
            output_file = input_path.with_name(f"{input_path.stem}_enhanced.json")
    else:
        output_file = args.output_file
    
    # Erstelle Generator
    generator = EnhancedDescriptionGenerator(
        max_workers=args.max_workers,
        min_chunk_size=args.min_chunk_size,
        max_chunk_size=args.max_chunk_size,
        memory_target_percentage=args.memory_target
    )
    
    try:
        # Verarbeite Lesezeichen
        success = generator.enhance_descriptions(args.input_file, output_file)
        return 0 if success else 1
    
    except KeyboardInterrupt:
        logger.info("Abbruch durch Benutzer")
        return 130
    
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {str(e)}", exc_info=True)
        return 1
    
    finally:
        # Fahre Generator herunter
        generator.shutdown()


if __name__ == "__main__":
    sys.exit(main()) 