#!/usr/bin/env python3
"""
Optimierte Version des simple_html_report.py Skripts.

Generiert einen einfachen HTML-Bericht für Lesezeichen.
Verwendet den Chunk-Prozessor für optimierte Speichernutzung und Parallelverarbeitung.

Verwendung:
    python scripts/export/simple_html_report_optimized.py [input_file] [output_file]
"""

import os
import sys
import json
import gzip
import logging
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

# Füge das übergeordnete Verzeichnis zum Pfad hinzu, um den Chunk-Prozessor zu importieren
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.processing.pipeline_integration import PipelineIntegration

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/html_report.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("html_report")

class HTMLReportGenerator:
    """
    Generiert einen HTML-Bericht für Lesezeichen.
    Verwendet den Chunk-Prozessor für optimierte Speichernutzung und Parallelverarbeitung.
    """
    
    def __init__(self, max_workers=2, min_chunk_size=50, max_chunk_size=10000, memory_target_percentage=0.7):
        """
        Initialisiert den HTML-Report-Generator.
        
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
            'total_bookmarks': 0,
            'processed_bookmarks': 0,
            'folders': Counter(),
            'domains': Counter(),
            'tags': Counter()
        }
        
        logger.info(f"HTML-Report-Generator initialisiert mit {max_workers} Workern")
    
    def _progress_callback(self, progress, stats):
        """Callback für Fortschrittsupdates."""
        logger.info(f"Fortschritt: {progress:.1%}")
    
    def _status_callback(self, status, stats):
        """Callback für Statusupdates."""
        logger.info(f"Status: {status}")
    
    def _error_callback(self, message, exception):
        """Callback für Fehlerbehandlung."""
        logger.error(f"Fehler: {message} - {str(exception)}")
    
    def _complete_callback(self, stats):
        """Callback für Abschluss."""
        self.stats['end_time'] = stats.get('end_time', 0)
        duration = self.stats['end_time'] - self.stats['start_time'] if self.stats['start_time'] else 0
        logger.info(f"Verarbeitung abgeschlossen in {duration:.2f} Sekunden")
    
    def _collect_bookmark_stats(self, bookmarks):
        """
        Sammelt Statistiken über die Lesezeichen.
        
        Args:
            bookmarks: Liste von Lesezeichen
            
        Returns:
            dict: Statistiken über die Lesezeichen
        """
        stats = {
            'total': len(bookmarks),
            'folders': Counter(),
            'domains': Counter(),
            'tags': Counter(),
            'with_description': 0,
            'without_description': 0
        }
        
        for bookmark in bookmarks:
            # Zähle Ordner
            folder = bookmark.get('folder', 'Unbekannt')
            stats['folders'][folder] += 1
            
            # Zähle Domains
            url = bookmark.get('url', '')
            domain = url.split('//')[-1].split('/')[0] if '//' in url else url.split('/')[0]
            stats['domains'][domain] += 1
            
            # Zähle Tags
            for tag in bookmark.get('tags', []):
                stats['tags'][tag] += 1
            
            # Zähle Beschreibungen
            if bookmark.get('description'):
                stats['with_description'] += 1
            else:
                stats['without_description'] += 1
        
        return stats
    
    def _generate_html_template(self, bookmarks):
        """
        Generiert ein HTML-Template für die Lesezeichen.
        
        Args:
            bookmarks: Liste von Lesezeichen
            
        Returns:
            str: HTML-Template
        """
        # Sammle Statistiken
        stats = self._collect_bookmark_stats(bookmarks)
        self.stats.update(stats)
        
        # Generiere HTML
        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lesezeichen-Bericht ({stats['total']} Einträge)</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .stats {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-box {{
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            flex: 1;
            min-width: 200px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .bookmark {{
            background-color: #fff;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 0 5px 5px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .bookmark h3 {{
            margin-top: 0;
        }}
        .bookmark-url {{
            color: #3498db;
            word-break: break-all;
        }}
        .bookmark-description {{
            margin-top: 10px;
            color: #555;
        }}
        .bookmark-meta {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-top: 10px;
        }}
        .tag {{
            display: inline-block;
            background-color: #e0f7fa;
            color: #0097a7;
            padding: 2px 8px;
            border-radius: 3px;
            margin-right: 5px;
            font-size: 0.85em;
        }}
        .folder {{
            color: #e67e22;
        }}
        .timestamp {{
            color: #95a5a6;
        }}
        .top-items {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .top-item-box {{
            flex: 1;
            min-width: 250px;
        }}
        .search-box {{
            margin-bottom: 20px;
        }}
        #search {{
            padding: 8px;
            width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }}
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <h1>Lesezeichen-Bericht</h1>
    
    <div class="stats">
        <div class="stat-box">
            <h3>Übersicht</h3>
            <p>Gesamtzahl: <strong>{stats['total']}</strong> Lesezeichen</p>
            <p>Ordner: <strong>{len(stats['folders'])}</strong> verschiedene</p>
            <p>Domains: <strong>{len(stats['domains'])}</strong> verschiedene</p>
            <p>Tags: <strong>{len(stats['tags'])}</strong> verschiedene</p>
        </div>
        
        <div class="stat-box">
            <h3>Beschreibungen</h3>
            <p>Mit Beschreibung: <strong>{stats['with_description']}</strong> ({stats['with_description']/stats['total']*100:.1f}%)</p>
            <p>Ohne Beschreibung: <strong>{stats['without_description']}</strong> ({stats['without_description']/stats['total']*100:.1f}%)</p>
        </div>
    </div>
    
    <div class="top-items">
        <div class="top-item-box">
            <h3>Top 10 Ordner</h3>
            <ul>
"""
        
        # Füge Top 10 Ordner hinzu
        for folder, count in stats['folders'].most_common(10):
            html += f'                <li><span class="folder">{folder}</span>: {count} Lesezeichen</li>\n'
        
        html += """            </ul>
        </div>
        
        <div class="top-item-box">
            <h3>Top 10 Domains</h3>
            <ul>
"""
        
        # Füge Top 10 Domains hinzu
        for domain, count in stats['domains'].most_common(10):
            html += f'                <li>{domain}: {count} Lesezeichen</li>\n'
        
        html += """            </ul>
        </div>
        
        <div class="top-item-box">
            <h3>Top 10 Tags</h3>
            <ul>
"""
        
        # Füge Top 10 Tags hinzu
        for tag, count in stats['tags'].most_common(10):
            html += f'                <li><span class="tag">{tag}</span>: {count} Lesezeichen</li>\n'
        
        html += """            </ul>
        </div>
    </div>
    
    <div class="search-box">
        <input type="text" id="search" placeholder="Lesezeichen durchsuchen...">
    </div>
    
    <h2>Alle Lesezeichen</h2>
    <div id="bookmarks">
"""
        
        # Füge alle Lesezeichen hinzu
        for bookmark in bookmarks:
            title = bookmark.get('title', 'Kein Titel')
            url = bookmark.get('url', '#')
            description = bookmark.get('description', '')
            folder = bookmark.get('folder', 'Unbekannt')
            tags = bookmark.get('tags', [])
            timestamp = bookmark.get('dateAdded', '')
            
            # Formatiere Timestamp
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = datetime.fromtimestamp(timestamp / 1000)
                    timestamp = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    pass
            
            html += f"""        <div class="bookmark">
            <h3>{title}</h3>
            <a href="{url}" class="bookmark-url" target="_blank">{url}</a>
            
            <div class="bookmark-description">
                {description}
            </div>
            
            <div class="bookmark-meta">
                <div>Ordner: <span class="folder">{folder}</span></div>
                <div>Tags: {' '.join([f'<span class="tag">{tag}</span>' for tag in tags])}</div>
                <div>Hinzugefügt: <span class="timestamp">{timestamp}</span></div>
            </div>
        </div>
"""
        
        html += """    </div>
    
    <script>
        // Einfache Suchfunktion
        document.getElementById('search').addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const bookmarks = document.querySelectorAll('.bookmark');
            
            bookmarks.forEach(bookmark => {
                const text = bookmark.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    bookmark.classList.remove('hidden');
                } else {
                    bookmark.classList.add('hidden');
                }
            });
        });
    </script>
</body>
</html>
"""
        
        return html
    
    def generate_report(self, input_file, output_file):
        """
        Generiert einen HTML-Bericht für Lesezeichen.
        
        Args:
            input_file: Pfad zur Eingabe-JSON-Datei
            output_file: Pfad zur Ausgabe-HTML-Datei
            
        Returns:
            bool: True, wenn die Generierung erfolgreich war, sonst False
        """
        logger.info(f"Starte Generierung des HTML-Berichts für {input_file}")
        
        # Setze Startzeit
        self.stats['start_time'] = datetime.now().timestamp()
        
        # Generiere den HTML-Bericht mit dem Chunk-Prozessor
        result = self.pipeline.generate_html_report(
            input_file=input_file,
            output_file=output_file,
            template_func=self._generate_html_template
        )
        
        if result:
            logger.info(f"HTML-Bericht erfolgreich generiert und in {output_file} gespeichert")
        else:
            logger.error(f"Fehler bei der Generierung des HTML-Berichts")
        
        return result
    
    def shutdown(self):
        """Fährt den Generator herunter."""
        self.pipeline.shutdown()


def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Generiert einen HTML-Bericht für Lesezeichen")
    parser.add_argument("input_file", help="Pfad zur Eingabe-JSON-Datei")
    parser.add_argument("output_file", nargs='?', help="Pfad zur Ausgabe-HTML-Datei")
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
        output_file = input_path.with_suffix('.html')
    else:
        output_file = args.output_file
    
    # Erstelle Generator
    generator = HTMLReportGenerator(
        max_workers=args.max_workers,
        min_chunk_size=args.min_chunk_size,
        max_chunk_size=args.max_chunk_size,
        memory_target_percentage=args.memory_target
    )
    
    try:
        # Generiere Bericht
        success = generator.generate_report(args.input_file, output_file)
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