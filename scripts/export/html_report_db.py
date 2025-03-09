#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generiert einen HTML-Bericht aus den in der SQLite-Datenbank gespeicherten Daten.

Erstellt einen umfassenden HTML-Bericht mit Suchfunktion, Filtern und
thematischer Gruppierung.
"""

import os
import sys
import json
import logging
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from jinja2 import Template

# Füge das Projektverzeichnis zum Pfad hinzu
sys.path.append(str(Path(__file__).parent.parent.parent))

# Importiere die Datenbankklasse
from scripts.database.db_operations import BookmarkDB

# Konfiguriere Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/html_report_db.log")
    ]
)
logger = logging.getLogger("html_report_db")

# HTML-Template für den Bericht
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bookmark Explorer - {{ count }} Lesezeichen</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .stats {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .filters {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            align-items: center;
            flex-wrap: wrap;
        }
        .search-box {
            flex: 1;
            min-width: 200px;
        }
        input[type="text"], select {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 100%;
        }
        button {
            padding: 8px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #45a049;
        }
        .bookmark-card {
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .bookmark-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .bookmark-title {
            margin-top: 0;
            margin-bottom: 10px;
            color: #2c3e50;
        }
        .bookmark-url {
            font-size: 0.9em;
            color: #3498db;
            margin-bottom: 10px;
            word-break: break-all;
        }
        .bookmark-description {
            margin-bottom: 15px;
        }
        .bookmark-meta {
            font-size: 0.8em;
            color: #7f8c8d;
            display: flex;
            justify-content: space-between;
        }
        .folder-badge {
            background-color: #e0f7fa;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            color: #00838f;
            margin-right: 5px;
        }
        .cluster-badge {
            background-color: #f3e5f5;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            color: #6a1b9a;
            margin-right: 5px;
        }
        .cluster-section {
            margin-bottom: 30px;
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
        }
        .bookmark-content {
            max-height: 300px;
            overflow-y: auto;
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 5px;
            font-size: 0.9em;
            margin-top: 10px;
            display: none;
        }
        .toggle-content {
            background-color: #eee;
            color: #333;
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 0.8em;
            cursor: pointer;
        }
        .toggle-content:hover {
            background-color: #ddd;
        }
        .no-results {
            padding: 20px;
            text-align: center;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .date-added {
            color: #7f8c8d;
            font-size: 0.8em;
        }
        .scraper-badge {
            background-color: #e8f5e9;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            color: #2e7d32;
        }
        @media (max-width: 768px) {
            .filters {
                flex-direction: column;
                align-items: stretch;
            }
            .filter-item {
                margin-bottom: 10px;
            }
        }
    </style>
</head>
<body>
    <h1>Bookmark Explorer</h1>
    
    <div class="stats">
        <p><strong>{{ count }}</strong> Lesezeichen, <strong>{{ clusters|length }}</strong> thematische Cluster</p>
        <p>Gescrapt mit: ScrapingBee ({{ scrapers.scrapingbee }}), Fallback ({{ scrapers.fallback }}), Cache ({{ scrapers.cached }})</p>
        <p>Generiert am: {{ generation_date }}</p>
    </div>
    
    <div class="filters">
        <div class="search-box filter-item">
            <input type="text" id="search-input" placeholder="Suche nach Titel, URL oder Beschreibung...">
        </div>
        
        <div class="filter-item">
            <select id="folder-filter">
                <option value="">Alle Ordner</option>
                {% for folder in folders %}
                <option value="{{ folder }}">{{ folder }}</option>
                {% endfor %}
            </select>
        </div>
        
        <div class="filter-item">
            <select id="cluster-filter">
                <option value="">Alle Cluster</option>
                {% for cluster_id, cluster_info in clusters.items() %}
                <option value="{{ cluster_id }}">Cluster {{ cluster_id }} ({{ cluster_info.count }})</option>
                {% endfor %}
            </select>
        </div>
        
        <div class="filter-item">
            <button id="reset-filters">Filter zurücksetzen</button>
        </div>
    </div>
    
    <div id="bookmarks-container">
        {% for cluster_id, cluster_info in clusters.items() %}
        <div class="cluster-section" data-cluster="{{ cluster_id }}">
            <h2>Cluster {{ cluster_id }}: {{ cluster_info.theme }}</h2>
            <p>{{ cluster_info.count }} Lesezeichen in diesem Cluster</p>
            
            <div class="bookmarks">
                {% for bookmark in bookmarks %}
                {% if bookmark.cluster_id == cluster_id %}
                <div class="bookmark-card" data-folder="{{ bookmark.folder }}" data-cluster="{{ bookmark.cluster_id }}">
                    <h3 class="bookmark-title">{{ bookmark.title }}</h3>
                    <div class="bookmark-url"><a href="{{ bookmark.url }}" target="_blank">{{ bookmark.url }}</a></div>
                    <div class="bookmark-description">{{ bookmark.description }}</div>
                    <div class="bookmark-meta">
                        <div>
                            <span class="folder-badge">{{ bookmark.folder }}</span>
                            <span class="cluster-badge">Cluster {{ bookmark.cluster_id }}</span>
                            <span class="scraper-badge">{{ bookmark.scraper_used }}</span>
                        </div>
                        <div class="date-added">Hinzugefügt: {{ bookmark.added }}</div>
                    </div>
                    <button class="toggle-content" onclick="toggleContent(this)">Inhalt anzeigen</button>
                    <div class="bookmark-content">{{ bookmark.article_text }}</div>
                </div>
                {% endif %}
                {% endfor %}
            </div>
        </div>
        {% endfor %}
        
        <div id="no-results" class="no-results" style="display: none;">
            <p>Keine Lesezeichen gefunden. Bitte versuchen Sie es mit anderen Filterkriterien.</p>
        </div>
    </div>
    
    <script>
        // Suchfunktion
        function performSearch() {
            const searchText = document.getElementById('search-input').value.toLowerCase();
            const folderFilter = document.getElementById('folder-filter').value;
            const clusterFilter = document.getElementById('cluster-filter').value;
            
            const bookmarkCards = document.querySelectorAll('.bookmark-card');
            const clusterSections = document.querySelectorAll('.cluster-section');
            
            let visibleBookmarks = 0;
            const visibleClusters = new Set();
            
            bookmarkCards.forEach(card => {
                const title = card.querySelector('.bookmark-title').textContent.toLowerCase();
                const url = card.querySelector('.bookmark-url').textContent.toLowerCase();
                const description = card.querySelector('.bookmark-description').textContent.toLowerCase();
                const content = card.querySelector('.bookmark-content').textContent.toLowerCase();
                const folder = card.getAttribute('data-folder');
                const cluster = card.getAttribute('data-cluster');
                
                const matchesSearch = !searchText || 
                    title.includes(searchText) || 
                    url.includes(searchText) || 
                    description.includes(searchText) ||
                    content.includes(searchText);
                
                const matchesFolder = !folderFilter || folder === folderFilter;
                const matchesCluster = !clusterFilter || cluster === clusterFilter;
                
                const isVisible = matchesSearch && matchesFolder && matchesCluster;
                card.style.display = isVisible ? 'block' : 'none';
                
                if (isVisible) {
                    visibleBookmarks++;
                    visibleClusters.add(cluster);
                }
            });
            
            // Zeige/Verstecke Cluster-Abschnitte
            clusterSections.forEach(section => {
                const clusterId = section.getAttribute('data-cluster');
                section.style.display = visibleClusters.has(clusterId) ? 'block' : 'none';
            });
            
            // Zeige "Keine Ergebnisse" Nachricht
            document.getElementById('no-results').style.display = visibleBookmarks === 0 ? 'block' : 'none';
        }
        
        // Funktion zum Ein-/Ausblenden des Artikelinhalts
        function toggleContent(button) {
            const content = button.nextElementSibling;
            const isHidden = content.style.display === 'none' || content.style.display === '';
            
            content.style.display = isHidden ? 'block' : 'none';
            button.textContent = isHidden ? 'Inhalt ausblenden' : 'Inhalt anzeigen';
        }
        
        // Event-Listener
        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('search-input').addEventListener('input', performSearch);
            document.getElementById('folder-filter').addEventListener('change', performSearch);
            document.getElementById('cluster-filter').addEventListener('change', performSearch);
            
            document.getElementById('reset-filters').addEventListener('click', () => {
                document.getElementById('search-input').value = '';
                document.getElementById('folder-filter').value = '';
                document.getElementById('cluster-filter').value = '';
                performSearch();
            });
            
            // Initial search to handle URL parameters
            performSearch();
        });
    </script>
</body>
</html>
"""

def get_pages_from_db(db_path):
    """
    Holt alle Seiten aus der Datenbank.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        
    Returns:
        list: Liste von Dictionaries mit Seitendaten
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Verwende Row-Factory für named columns
        cursor = conn.cursor()
        
        # Hole Seiten mit Cluster-Informationen
        cursor.execute("""
            SELECT p.*, c.cluster_id
            FROM pages p
            LEFT JOIN clusters c ON p.url = c.url
            ORDER BY p.scrape_time DESC
        """)
        
        rows = cursor.fetchall()
        
        # Konvertiere die Zeilen in Dictionaries
        bookmarks = []
        for row in rows:
            bookmark = {key: row[key] for key in row.keys()}
            
            # Konvertiere JSON-Tags zurück zu Liste
            if bookmark.get('tags'):
                try:
                    bookmark['tags'] = json.loads(bookmark['tags'])
                except json.JSONDecodeError:
                    bookmark['tags'] = []
            
            bookmarks.append(bookmark)
        
        conn.close()
        return bookmarks
        
    except sqlite3.Error as e:
        logger.error(f"Fehler beim Abrufen der Seiten aus der Datenbank: {str(e)}")
        return []

def get_cluster_info(db_path):
    """
    Holt Cluster-Informationen aus der Datenbank.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        
    Returns:
        dict: Dictionary mit Cluster-IDs als Schlüssel und Cluster-Informationen als Werte
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Hole Cluster-Informationen
        cursor.execute("""
            SELECT c.cluster_id, COUNT(*) as count, GROUP_CONCAT(p.title, ' | ') as titles
            FROM clusters c
            JOIN pages p ON c.url = p.url
            GROUP BY c.cluster_id
            ORDER BY count DESC
        """)
        
        rows = cursor.fetchall()
        
        # Erstelle ein Dictionary mit Cluster-Informationen
        clusters = {}
        for cluster_id, count, titles in rows:
            # Erzeuge ein Cluster-Thema basierend auf den Titeln
            titles_list = titles.split(' | ')[:5]
            theme = ', '.join(titles_list[:3])
            
            clusters[str(cluster_id)] = {
                'count': count,
                'titles': titles_list,
                'theme': theme
            }
        
        conn.close()
        return clusters
        
    except sqlite3.Error as e:
        logger.error(f"Fehler beim Abrufen der Cluster-Informationen: {str(e)}")
        return {}

def get_scraper_stats(bookmarks):
    """
    Berechnet Scraper-Statistiken.
    
    Args:
        bookmarks: Liste von Bookmark-Dictionaries
        
    Returns:
        dict: Dictionary mit Scraper-Statistiken
    """
    scrapers = {
        'scrapingbee': 0,
        'smartproxy': 0,
        'fallback': 0,
        'cached': 0
    }
    
    for bookmark in bookmarks:
        scraper = bookmark.get('scraper_used', '').lower()
        
        if scraper == 'scrapingbee':
            scrapers['scrapingbee'] += 1
        elif scraper == 'smartproxy':
            scrapers['smartproxy'] += 1
        elif scraper == 'fallback':
            scrapers['fallback'] += 1
        elif scraper == 'cached':
            scrapers['cached'] += 1
    
    return scrapers

def generate_html_report(db_path, output_file="data/reports/hybrid_report_db.html"):
    """
    Generiert einen HTML-Bericht aus den Daten in der Datenbank.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        output_file: Pfad zur Ausgabedatei
        
    Returns:
        bool: True, wenn erfolgreich, sonst False
    """
    try:
        # Hole die Daten aus der Datenbank
        bookmarks = get_pages_from_db(db_path)
        
        # Wenn keine Bookmarks gefunden wurden, brich ab
        if not bookmarks:
            logger.error("Keine Bookmarks in der Datenbank gefunden")
            return False
        
        # Hole Cluster-Informationen
        clusters = get_cluster_info(db_path)
        
        # Berechne Scraper-Statistiken
        scrapers = get_scraper_stats(bookmarks)
        
        # Sammle alle einzigartigen Ordner
        folders = sorted(set([bookmark.get('folder', '') for bookmark in bookmarks if bookmark.get('folder')]))
        
        # Erstelle das HTML mit Jinja2
        template = Template(HTML_TEMPLATE)
        html = template.render(
            bookmarks=bookmarks,
            count=len(bookmarks),
            clusters=clusters,
            folders=folders,
            scrapers=scrapers,
            generation_date=datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        )
        
        # Speichere das HTML in einer Datei
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        
        logger.info(f"HTML-Bericht erfolgreich generiert: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Fehler bei der Generierung des HTML-Berichts: {str(e)}")
        return False

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Generiert einen HTML-Bericht aus den Daten in der SQLite-Datenbank")
    parser.add_argument("--db-path", default="data/database/bookmarks.db", help="Pfad zur SQLite-Datenbank")
    parser.add_argument("--output", default="data/reports/hybrid_report_db.html", help="Pfad zur Ausgabedatei")
    args = parser.parse_args()
    
    # Generiere den HTML-Bericht
    generate_html_report(args.db_path, args.output)
    
    logger.info("HTML-Bericht-Generierung abgeschlossen")

if __name__ == "__main__":
    main() 