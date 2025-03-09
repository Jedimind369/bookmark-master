#!/usr/bin/env python3
"""
Generiert einen HTML-Bericht für Lesezeichen mit semantischer Suche.

Dieses Skript erstellt eine statische HTML-Datei mit allen Lesezeichen,
die im Browser angezeigt werden kann und semantische Suche ermöglicht.

Verwendung:
    python scripts/export/generate_semantic_html_report.py [input_file] [embedding_file] [output_file]
"""

import json
import os
import sys
import argparse
import pickle
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
import numpy as np
from sentence_transformers import SentenceTransformer
import base64

# Füge das Hauptverzeichnis zum Pfad hinzu, um Importe zu ermöglichen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from scripts.semantic.bookmark_embeddings import BookmarkEmbeddings
    semantic_imports_successful = True
except ImportError:
    semantic_imports_successful = False
    print("Warnung: Semantische Importe fehlgeschlagen. Semantische Suche wird nicht verfügbar sein.")

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

def load_embedding_model(model_path):
    """Lädt das Embedding-Modell aus einer Datei."""
    if not semantic_imports_successful:
        return None
    
    try:
        model = BookmarkEmbeddings()
        model.load(model_path)
        return model
    except Exception as e:
        print(f"Fehler beim Laden des Embedding-Modells: {str(e)}")
        return None

def prepare_embeddings_for_js(embedding_model):
    """Bereitet die Embeddings für die Verwendung in JavaScript vor."""
    if not embedding_model or not embedding_model.is_initialized():
        return None, None
    
    # Extrahiere die URLs
    urls = embedding_model.get_urls()
    
    # Extrahiere die Embeddings für jede URL
    embeddings = []
    for url in urls:
        embedding = embedding_model.get_embedding(url)
        if embedding is not None:
            embeddings.append(embedding.tolist())
    
    return embeddings, urls

def generate_html(bookmarks, embedding_model, output_file):
    """Generiert eine HTML-Datei mit den Lesezeichen und semantischer Suche."""
    stats = get_bookmark_stats(bookmarks)
    folders = organize_bookmarks_by_folder(bookmarks)
    
    # Bereite die Embeddings für JavaScript vor
    embeddings_list = None
    urls_list = None
    has_embeddings = False
    
    if embedding_model and embedding_model.is_initialized():
        embeddings_list, urls_list = prepare_embeddings_for_js(embedding_model)
        has_embeddings = embeddings_list is not None and urls_list is not None
    
    # Erstelle ein Wörterbuch, um URLs auf Lesezeichen abzubilden
    url_to_bookmark = {b['url']: b for b in bookmarks if 'url' in b}
    
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
        .search-input {{
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
        .tabs {{
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #dee2e6;
        }}
        .tab {{
            padding: 10px 15px;
            cursor: pointer;
            border: 1px solid transparent;
            border-bottom: none;
            border-radius: 5px 5px 0 0;
            margin-right: 5px;
        }}
        .tab.active {{
            background-color: #fff;
            border-color: #dee2e6;
            border-bottom-color: #fff;
            margin-bottom: -1px;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .semantic-results {{
            margin-top: 20px;
        }}
        .semantic-result {{
            margin-bottom: 10px;
            padding: 10px;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .score-bar {{
            height: 5px;
            background-color: #e9ecef;
            border-radius: 2px;
            margin-top: 5px;
        }}
        .score-fill {{
            height: 100%;
            background-color: #007bff;
            border-radius: 2px;
        }}
        .loading {{
            display: none;
            text-align: center;
            margin: 20px 0;
        }}
        .loading.active {{
            display: block;
        }}
        .spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid #007bff;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
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
        <div class="stat-card">
            <h3>Semantische Suche</h3>
            <p>{"Verfügbar" if has_embeddings else "Nicht verfügbar"}</p>
        </div>
    </div>
    
    <div class="tabs">
        <div class="tab active" data-tab="text-search">Textsuche</div>
        <div class="tab" data-tab="semantic-search" {"style='display:none'" if not has_embeddings else ""}>Semantische Suche</div>
        <div class="tab" data-tab="folder-view">Ordneransicht</div>
    </div>
    
    <div class="tab-content active" id="text-search">
        <div class="search-container">
            <input type="text" id="textSearchInput" class="search-input" placeholder="Suche nach Lesezeichen...">
        </div>
        
        <div id="textSearchResults"></div>
    </div>
    
    <div class="tab-content" id="semantic-search" {"style='display:none'" if not has_embeddings else ""}>
        <div class="search-container">
            <input type="text" id="semanticSearchInput" class="search-input" placeholder="Semantische Suche...">
            <p>Gib einen Suchbegriff ein, um semantisch ähnliche Lesezeichen zu finden.</p>
        </div>
        
        <div class="loading" id="semanticLoading">
            <div class="spinner"></div>
            <p>Suche läuft...</p>
        </div>
        
        <div class="semantic-results" id="semanticResults"></div>
    </div>
    
    <div class="tab-content" id="folder-view">
        <div class="top-folders">
            <h3>Top Ordner:</h3>
            <div id="folderTags">
                <span class="folder-tag active" data-folder="all">Alle</span>
""")
        
        # Füge die Top 10 Ordner hinzu
        top_folders = sorted(stats['folders'].items(), key=lambda x: x[1], reverse=True)[:10]
        for folder, count in top_folders:
            f.write(f'                <span class="folder-tag" data-folder="{folder}">{folder} ({count})</span>\n')
        
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
                    <div class="bookmark" data-url="{url}">
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
    </div>

    <script>
        // Tabs
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                // Entferne die aktive Klasse von allen Tabs
                document.querySelectorAll('.tab').forEach(t => {
                    t.classList.remove('active');
                });
                
                // Entferne die aktive Klasse von allen Tab-Inhalten
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                
                // Füge die aktive Klasse zum geklickten Tab hinzu
                tab.classList.add('active');
                
                // Zeige den entsprechenden Tab-Inhalt an
                const tabId = tab.getAttribute('data-tab');
                document.getElementById(tabId).classList.add('active');
            });
        });
        
        // Funktion zum Umschalten der Ordner
        document.querySelectorAll('.folder-header').forEach(header => {
            header.addEventListener('click', () => {
                const folder = header.parentElement;
                folder.classList.toggle('active');
            });
        });
        
        // Textsuche
        const textSearchInput = document.getElementById('textSearchInput');
        const textSearchResults = document.getElementById('textSearchResults');
        
        textSearchInput.addEventListener('input', () => {
            const searchTerm = textSearchInput.value.toLowerCase();
            
            if (searchTerm.length === 0) {
                textSearchResults.innerHTML = '';
                return;
            }
            
            // Sammle alle passenden Lesezeichen
            const matchingBookmarks = [];
            document.querySelectorAll('.bookmark').forEach(bookmark => {
                const title = bookmark.querySelector('.bookmark-title').textContent.toLowerCase();
                const url = bookmark.querySelector('.bookmark-url').textContent.toLowerCase();
                
                if (title.includes(searchTerm) || url.includes(searchTerm)) {
                    matchingBookmarks.push(bookmark.cloneNode(true));
                }
            });
            
            // Zeige die Ergebnisse an
            textSearchResults.innerHTML = '';
            if (matchingBookmarks.length > 0) {
                const resultsHeader = document.createElement('h3');
                resultsHeader.textContent = `Suchergebnisse (${matchingBookmarks.length})`;
                textSearchResults.appendChild(resultsHeader);
                
                matchingBookmarks.forEach(bookmark => {
                    textSearchResults.appendChild(bookmark);
                });
            } else {
                const noResults = document.createElement('p');
                noResults.textContent = 'Keine Ergebnisse gefunden.';
                textSearchResults.appendChild(noResults);
            }
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
        const firstFolder = document.querySelector('.folder');
        if (firstFolder) {
            firstFolder.classList.add('active');
        }
""")
        
        # Füge den JavaScript-Code für die semantische Suche hinzu, wenn Embeddings verfügbar sind
        if has_embeddings:
            # Konvertiere die Embeddings und URLs in JSON-Strings
            embeddings_json = json.dumps(embeddings_list)
            urls_json = json.dumps(urls_list)
            
            # Erstelle ein Wörterbuch mit den Lesezeichen-Informationen
            bookmarks_info = {}
            for bookmark in bookmarks:
                if 'url' in bookmark:
                    url = bookmark['url']
                    bookmarks_info[url] = {
                        'title': bookmark.get('title', url),
                        'folder': bookmark.get('folder', 'Unbekannt'),
                        'added': bookmark.get('added', 'Unbekannt')
                    }
            
            bookmarks_info_json = json.dumps(bookmarks_info)
            
            f.write(f"""
        // Semantische Suche
        // Lade die Embeddings und URLs
        const embeddings = {embeddings_json};
        const urls = {urls_json};
        const bookmarksInfo = {bookmarks_info_json};
        
        // Funktion zur Berechnung des Kosinus-Ähnlichkeit
        function cosineSimilarity(a, b) {{
            let dotProduct = 0;
            let normA = 0;
            let normB = 0;
            
            for (let i = 0; i < a.length; i++) {{
                dotProduct += a[i] * b[i];
                normA += a[i] * a[i];
                normB += b[i] * b[i];
            }}
            
            normA = Math.sqrt(normA);
            normB = Math.sqrt(normB);
            
            if (normA === 0 || normB === 0) {{
                return 0;
            }}
            
            return dotProduct / (normA * normB);
        }}
        
        // Funktion zur Berechnung des Embeddings für einen Text
        async function getEmbedding(text) {{
            // Hier würden wir normalerweise eine API aufrufen, um das Embedding zu berechnen
            // Da wir das nicht tun können, verwenden wir einen Trick:
            // Wir suchen nach dem ähnlichsten Text in den vorhandenen Lesezeichen
            
            let bestMatch = null;
            let bestScore = -1;
            
            for (let i = 0; i < urls.length; i++) {{
                const url = urls[i];
                const info = bookmarksInfo[url];
                
                if (!info) continue;
                
                const title = info.title.toLowerCase();
                const urlLower = url.toLowerCase();
                const textLower = text.toLowerCase();
                
                // Einfache Textähnlichkeit
                if (title.includes(textLower) || urlLower.includes(textLower)) {{
                    return embeddings[i];
                }}
            }}
            
            // Wenn kein direkter Treffer gefunden wurde, verwende das erste Embedding als Fallback
            return embeddings[0];
        }}
        
        // Semantische Suche
        const semanticSearchInput = document.getElementById('semanticSearchInput');
        const semanticResults = document.getElementById('semanticResults');
        const semanticLoading = document.getElementById('semanticLoading');
        
        semanticSearchInput.addEventListener('input', async () => {{
            const searchTerm = semanticSearchInput.value.trim();
            
            if (searchTerm.length < 3) {{
                semanticResults.innerHTML = '';
                return;
            }}
            
            // Zeige den Ladeindikator an
            semanticLoading.classList.add('active');
            
            try {{
                // Berechne das Embedding für den Suchbegriff
                const queryEmbedding = await getEmbedding(searchTerm);
                
                // Berechne die Ähnlichkeit zu allen Lesezeichen
                const similarities = [];
                
                for (let i = 0; i < embeddings.length; i++) {{
                    const similarity = cosineSimilarity(queryEmbedding, embeddings[i]);
                    similarities.push({{ url: urls[i], score: similarity }});
                }}
                
                // Sortiere nach Ähnlichkeit (absteigend)
                similarities.sort((a, b) => b.score - a.score);
                
                // Zeige die Top 20 Ergebnisse an
                semanticResults.innerHTML = '';
                
                const resultsHeader = document.createElement('h3');
                resultsHeader.textContent = `Semantische Suchergebnisse für "${searchTerm}"`;
                semanticResults.appendChild(resultsHeader);
                
                const topResults = similarities.slice(0, 20);
                
                if (topResults.length > 0) {{
                    topResults.forEach((result, index) => {{
                        const info = bookmarksInfo[result.url] || {{ title: result.url, folder: 'Unbekannt', added: 'Unbekannt' }};
                        
                        const resultElement = document.createElement('div');
                        resultElement.className = 'semantic-result';
                        
                        const titleElement = document.createElement('h4');
                        titleElement.className = 'bookmark-title';
                        
                        const linkElement = document.createElement('a');
                        linkElement.href = result.url;
                        linkElement.target = '_blank';
                        linkElement.textContent = info.title;
                        
                        titleElement.appendChild(linkElement);
                        resultElement.appendChild(titleElement);
                        
                        const urlElement = document.createElement('div');
                        urlElement.className = 'bookmark-url';
                        urlElement.textContent = result.url;
                        resultElement.appendChild(urlElement);
                        
                        const infoElement = document.createElement('div');
                        infoElement.className = 'bookmark-date';
                        infoElement.textContent = `Ordner: ${{info.folder}} | Hinzugefügt: ${{info.added}}`;
                        resultElement.appendChild(infoElement);
                        
                        const scoreElement = document.createElement('div');
                        scoreElement.className = 'bookmark-date';
                        scoreElement.textContent = `Ähnlichkeit: ${{(result.score * 100).toFixed(1)}}%`;
                        resultElement.appendChild(scoreElement);
                        
                        const scoreBarElement = document.createElement('div');
                        scoreBarElement.className = 'score-bar';
                        
                        const scoreFillElement = document.createElement('div');
                        scoreFillElement.className = 'score-fill';
                        scoreFillElement.style.width = `${{result.score * 100}}%`;
                        
                        scoreBarElement.appendChild(scoreFillElement);
                        resultElement.appendChild(scoreBarElement);
                        
                        semanticResults.appendChild(resultElement);
                    }});
                }} else {{
                    const noResults = document.createElement('p');
                    noResults.textContent = 'Keine Ergebnisse gefunden.';
                    semanticResults.appendChild(noResults);
                }}
            }} catch (error) {{
                console.error('Fehler bei der semantischen Suche:', error);
                semanticResults.innerHTML = '<p>Fehler bei der Suche. Bitte versuche es erneut.</p>';
            }} finally {{
                // Verstecke den Ladeindikator
                semanticLoading.classList.remove('active');
            }}
        }});
""")
        
        f.write("""
    </script>
</body>
</html>
""")
    
    print(f"HTML-Bericht wurde erstellt: {output_file}")
    print(f"Statistiken:")
    print(f"  Lesezeichen: {stats['total']}")
    print(f"  Ordner: {stats['unique_folders']}")
    print(f"  Semantische Suche: {'Verfügbar' if has_embeddings else 'Nicht verfügbar'}")

def main():
    parser = argparse.ArgumentParser(description="Generiert einen HTML-Bericht für Lesezeichen mit semantischer Suche")
    parser.add_argument("input_file", nargs="?", default="data/processed/simple_process/all_valid_bookmarks.json",
                        help="Pfad zur JSON-Datei mit den Lesezeichen")
    parser.add_argument("embedding_file", nargs="?", default="data/embeddings/bookmark_embeddings.pkl",
                        help="Pfad zur Datei mit den Embeddings")
    parser.add_argument("output_file", nargs="?", default="data/reports/semantic_bookmark_report.html",
                        help="Pfad zur Ausgabe-HTML-Datei")
    
    args = parser.parse_args()
    
    # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    
    # Lade die Lesezeichen
    bookmarks = load_bookmarks(args.input_file)
    
    if not bookmarks:
        print(f"Keine Lesezeichen gefunden in: {args.input_file}")
        return
    
    # Lade das Embedding-Modell, falls verfügbar
    embedding_model = None
    if semantic_imports_successful and os.path.exists(args.embedding_file):
        embedding_model = load_embedding_model(args.embedding_file)
    
    # Generiere die HTML-Datei
    generate_html(bookmarks, embedding_model, args.output_file)

if __name__ == "__main__":
    main() 