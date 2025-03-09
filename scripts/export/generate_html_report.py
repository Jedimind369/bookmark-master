#!/usr/bin/env python3
"""
Generiert einen HTML-Bericht für Lesezeichen.

Dieses Skript erstellt eine statische HTML-Datei mit allen Lesezeichen,
die im Browser angezeigt werden kann.

Verwendung:
    python scripts/export/generate_html_report.py [input_file] [output_file]
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

def load_bookmarks(file_path):
    """Lädt die Lesezeichen aus einer JSON-Datei."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            bookmarks = json.load(f)
        return bookmarks
    except Exception as e:
        print(f"Fehler beim Laden der Lesezeichen: {str(e)}")
        return []

def get_bookmark_stats(bookmarks):
    """Berechnet Statistiken über die Lesezeichen."""
    if not bookmarks:
        return {}
    
    # Zähle die Anzahl der Lesezeichen pro Ordner
    folder_counts = Counter([b.get('folder', 'Unbekannt') for b in bookmarks])
    
    # Extrahiere die Jahre aus den Datumsangaben
    years = []
    for b in bookmarks:
        if 'added' in b and b['added']:
            try:
                year = b['added'].split('-')[0]
                years.append(year)
            except:
                pass
    year_counts = Counter(years)
    
    return {
        'total': len(bookmarks),
        'folders': dict(folder_counts.most_common()),
        'years': dict(sorted(year_counts.items())),
        'unique_folders': len(folder_counts)
    }

def organize_bookmarks_by_folder(bookmarks):
    """Organisiert die Lesezeichen nach Ordnern."""
    folders = defaultdict(list)
    
    for bookmark in bookmarks:
        folder = bookmark.get('folder', 'Unbekannt')
        folders[folder].append(bookmark)
    
    return folders

def generate_html(bookmarks, output_file):
    """Generiert eine HTML-Datei mit den Lesezeichen."""
    stats = get_bookmark_stats(bookmarks)
    folders = organize_bookmarks_by_folder(bookmarks)
    
    # Erstelle die HTML-Datei
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bookmark Explorer - {stats['total']} Lesezeichen</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .stats {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .stat-card {{
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex: 1;
            min-width: 200px;
            margin-right: 10px;
        }}
        .stat-card h3 {{
            margin-top: 0;
            margin-bottom: 10px;
            font-size: 16px;
            color: #6c757d;
        }}
        .stat-card p {{
            margin: 0;
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .folder {{
            margin-bottom: 30px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            overflow: hidden;
        }}
        .folder-header {{
            background-color: #e9ecef;
            padding: 10px 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .folder-header h3 {{
            margin: 0;
        }}
        .folder-content {{
            padding: 0;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }}
        .folder.active .folder-content {{
            max-height: 5000px;
            padding: 15px;
        }}
        .bookmark {{
            margin-bottom: 10px;
            padding: 10px;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .bookmark-title {{
            margin: 0 0 5px 0;
            font-size: 16px;
        }}
        .bookmark-url {{
            color: #6c757d;
            font-size: 14px;
            word-break: break-all;
        }}
        .bookmark-date {{
            color: #6c757d;
            font-size: 12px;
            margin-top: 5px;
        }}
        .search-container {{
            margin-bottom: 20px;
        }}
        #searchInput {{
            width: 100%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ced4da;
            border-radius: 5px;
            box-sizing: border-box;
        }}
        .hidden {{
            display: none;
        }}
        .folder-count {{
            background-color: #007bff;
            color: white;
            border-radius: 50%;
            padding: 2px 8px;
            font-size: 12px;
        }}
        .top-folders {{
            margin-bottom: 20px;
        }}
        .folder-tag {{
            display: inline-block;
            background-color: #e9ecef;
            padding: 5px 10px;
            margin: 0 5px 5px 0;
            border-radius: 15px;
            font-size: 14px;
            cursor: pointer;
        }}
        .folder-tag:hover {{
            background-color: #dee2e6;
        }}
        .folder-tag.active {{
            background-color: #007bff;
            color: white;
        }}
    </style>
</head>
<body>
    <h1>Bookmark Explorer</h1>
    
    <div class="stats">
        <div class="stat-card">
            <h3>Lesezeichen</h3>
            <p>{stats['total']}</p>
        </div>
        <div class="stat-card">
            <h3>Ordner</h3>
            <p>{stats['unique_folders']}</p>
        </div>
    </div>
    
    <div class="search-container">
        <input type="text" id="searchInput" placeholder="Suche nach Lesezeichen...">
    </div>
    
    <div class="top-folders">
        <h3>Top Ordner:</h3>
        <div id="folderTags">
            <span class="folder-tag active" data-folder="all">Alle</span>
""")
        
        # Füge die Top 10 Ordner hinzu
        top_folders = sorted(stats['folders'].items(), key=lambda x: x[1], reverse=True)[:10]
        for folder, count in top_folders:
            f.write(f'            <span class="folder-tag" data-folder="{folder}">{folder} ({count})</span>\n')
        
        f.write("""
        </div>
    </div>
    
    <div id="bookmarkList">
""")
        
        # Füge die Ordner und Lesezeichen hinzu
        for folder, folder_bookmarks in sorted(folders.items()):
            f.write(f"""
        <div class="folder" data-folder="{folder}">
            <div class="folder-header">
                <h3>{folder}</h3>
                <span class="folder-count">{len(folder_bookmarks)}</span>
            </div>
            <div class="folder-content">
""")
            
            # Sortiere die Lesezeichen nach Datum (neueste zuerst)
            folder_bookmarks.sort(key=lambda x: x.get('added', ''), reverse=True)
            
            for bookmark in folder_bookmarks:
                title = bookmark.get('title', bookmark.get('url', 'Unbekannt'))
                url = bookmark.get('url', '#')
                date = bookmark.get('added', 'Unbekannt')
                
                f.write(f"""
                <div class="bookmark">
                    <h4 class="bookmark-title"><a href="{url}" target="_blank">{title}</a></h4>
                    <div class="bookmark-url">{url}</div>
                    <div class="bookmark-date">Hinzugefügt: {date}</div>
                </div>
""")
            
            f.write("""
            </div>
        </div>
""")
        
        f.write("""
    </div>

    <script>
        // Funktion zum Umschalten der Ordner
        document.querySelectorAll('.folder-header').forEach(header => {
            header.addEventListener('click', () => {
                const folder = header.parentElement;
                folder.classList.toggle('active');
            });
        });
        
        // Suchfunktion
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', () => {
            const searchTerm = searchInput.value.toLowerCase();
            
            document.querySelectorAll('.bookmark').forEach(bookmark => {
                const title = bookmark.querySelector('.bookmark-title').textContent.toLowerCase();
                const url = bookmark.querySelector('.bookmark-url').textContent.toLowerCase();
                
                if (title.includes(searchTerm) || url.includes(searchTerm)) {
                    bookmark.classList.remove('hidden');
                    // Zeige den übergeordneten Ordner an
                    const folder = bookmark.closest('.folder');
                    folder.classList.remove('hidden');
                    // Öffne den Ordner, wenn etwas gefunden wurde
                    if (searchTerm.length > 0) {
                        folder.classList.add('active');
                    }
                } else {
                    bookmark.classList.add('hidden');
                }
            });
            
            // Verstecke leere Ordner
            document.querySelectorAll('.folder').forEach(folder => {
                const visibleBookmarks = folder.querySelectorAll('.bookmark:not(.hidden)').length;
                if (visibleBookmarks === 0 && searchTerm.length > 0) {
                    folder.classList.add('hidden');
                } else {
                    folder.classList.remove('hidden');
                }
            });
        });
        
        // Ordner-Filter
        document.querySelectorAll('.folder-tag').forEach(tag => {
            tag.addEventListener('click', () => {
                // Entferne die aktive Klasse von allen Tags
                document.querySelectorAll('.folder-tag').forEach(t => {
                    t.classList.remove('active');
                });
                
                // Füge die aktive Klasse zum geklickten Tag hinzu
                tag.classList.add('active');
                
                const selectedFolder = tag.getAttribute('data-folder');
                
                // Zeige/verstecke Ordner basierend auf der Auswahl
                document.querySelectorAll('.folder').forEach(folder => {
                    if (selectedFolder === 'all' || folder.getAttribute('data-folder') === selectedFolder) {
                        folder.style.display = 'block';
                    } else {
                        folder.style.display = 'none';
                    }
                });
            });
        });
        
        // Öffne den ersten Ordner standardmäßig
        document.querySelector('.folder').classList.add('active');
    </script>
</body>
</html>
""")
    
    print(f"HTML-Bericht wurde erstellt: {output_file}")
    print(f"Statistiken:")
    print(f"  Lesezeichen: {stats['total']}")
    print(f"  Ordner: {stats['unique_folders']}")

def main():
    parser = argparse.ArgumentParser(description="Generiert einen HTML-Bericht für Lesezeichen")
    parser.add_argument("input_file", nargs="?", default="data/processed/simple_process/all_valid_bookmarks.json",
                        help="Pfad zur JSON-Datei mit den Lesezeichen")
    parser.add_argument("output_file", nargs="?", default="data/reports/bookmark_report.html",
                        help="Pfad zur Ausgabe-HTML-Datei")
    
    args = parser.parse_args()
    
    # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    
    # Lade die Lesezeichen
    bookmarks = load_bookmarks(args.input_file)
    
    if not bookmarks:
        print(f"Keine Lesezeichen gefunden in: {args.input_file}")
        return
    
    # Generiere die HTML-Datei
    generate_html(bookmarks, args.output_file)

if __name__ == "__main__":
    main() 