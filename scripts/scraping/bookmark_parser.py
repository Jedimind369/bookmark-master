#!/usr/bin/env python3
"""
bookmark_parser.py

Dieses Skript analysiert HTML-Lesezeichendateien (von Chrome, Firefox, Safari, etc.)
und konvertiert sie in ein strukturiertes JSON-Format, das für die weitere Verarbeitung 
verwendet werden kann. Es unterstützt verschachtelte Ordnerstrukturen und
extrahiert relevante Metadaten.
"""

import os
import re
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BookmarkParser:
    """
    Parser für HTML-Lesezeichendateien, die von Browsern exportiert wurden.
    Unterstützt verschiedene Browser-Formate und extrahiert alle verfügbaren 
    Metadaten für jedes Lesezeichen.
    """
    
    def __init__(self):
        """Initialisiert den BookmarkParser mit Standardwerten."""
        self.stats = {
            "total_bookmarks": 0,
            "total_folders": 0,
            "invalid_urls": 0,
            "duplicate_urls": 0,
            "empty_titles": 0,
            "max_depth": 0
        }
        
        # Set für die Überprüfung auf Duplikate
        self.url_set: Set[str] = set()
        
        # Unterstützte Browser
        self.browser_patterns = {
            "chrome": "<DL><p>",
            "firefox": "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
            "safari": "<!DOCTYPE html PUBLIC"
        }
    
    def parse_file(self, input_file: str) -> Dict[str, Any]:
        """
        Parst eine HTML-Lesezeichendatei und gibt eine strukturierte Darstellung zurück.
        
        Args:
            input_file: Pfad zur HTML-Lesezeichendatei
            
        Returns:
            Ein Dictionary mit der Lesezeichenstruktur
        """
        logger.info(f"Parsing bookmark file: {input_file}")
        
        # Datei öffnen und Inhalt laden
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Browser-Typ erkennen
        browser_type = self._detect_browser_type(content)
        logger.info(f"Detected browser type: {browser_type}")
        
        # Parse mit BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        
        # Vereinfachter Parser für alle Browser-Typen
        bookmarks = self._parse_simplified(soup)
        
        # Füge Metadaten hinzu
        result = {
            "bookmarks": bookmarks,
            "metadata": {
                "source_file": input_file,
                "browser_type": browser_type,
                "parsed_at": datetime.now().isoformat(),
                "stats": self.stats
            }
        }
        
        logger.info(f"Parsed {self.stats['total_bookmarks']} bookmarks in {self.stats['total_folders']} folders")
        
        return result
    
    def _detect_browser_type(self, content: str) -> str:
        """
        Erkennt den Browser-Typ aus dem Dateiinhalt.
        
        Args:
            content: Inhalt der Lesezeichendatei
            
        Returns:
            Browser-Typ als String ("chrome", "firefox", "safari" oder "unknown")
        """
        for browser, pattern in self.browser_patterns.items():
            if pattern in content:
                return browser
        return "unknown"
    
    def _parse_simplified(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Vereinfachter Parser, der direkt alle A-Tags und H3-Tags findet.
        
        Args:
            soup: BeautifulSoup-Objekt
            
        Returns:
            Liste von Lesezeichen und Ordnern
        """
        result = []
        current_folder = "root"
        current_depth = 0
        folder_stack = []
        
        # Finde alle H3-Tags (Ordner) und A-Tags (Lesezeichen)
        all_elements = soup.find_all(['h3', 'a'])
        
        for element in all_elements:
            if element.name == 'h3':
                # Es ist ein Ordner
                folder_name = element.get_text(strip=True)
                folder_add_date = element.get('add_date')
                folder_last_modified = element.get('last_modified')
                
                # Prüfe, ob es ein Unterordner ist
                if folder_stack and not element.get('personal_toolbar_folder'):
                    # Erhöhe die Tiefe, wenn es ein Unterordner ist
                    current_depth += 1
                
                folder = {
                    "type": "folder",
                    "name": folder_name,
                    "parent": folder_stack[-1] if folder_stack else "root",
                    "added": self._convert_timestamp(folder_add_date) if folder_add_date else None,
                    "last_modified": self._convert_timestamp(folder_last_modified) if folder_last_modified else None,
                    "depth": current_depth,
                    "items": []
                }
                
                # Füge den Ordner zum Ergebnis hinzu
                if folder_stack:
                    # Finde den übergeordneten Ordner und füge den Unterordner hinzu
                    parent_folder = self._find_folder_by_name(result, folder_stack[-1])
                    if parent_folder:
                        parent_folder["items"].append(folder)
                    else:
                        result.append(folder)
                else:
                    result.append(folder)
                
                # Aktualisiere den aktuellen Ordner und füge ihn zum Stack hinzu
                current_folder = folder_name
                folder_stack.append(folder_name)
                
                # Zähle Ordner
                self.stats["total_folders"] += 1
                
                # Aktualisiere maximale Tiefe
                self.stats["max_depth"] = max(self.stats["max_depth"], current_depth)
            
            elif element.name == 'a' and element.get('href'):
                # Es ist ein Lesezeichen
                bookmark = self._parse_bookmark_tag(element, current_folder, current_depth)
                if bookmark:
                    # Füge das Lesezeichen zum aktuellen Ordner hinzu
                    if folder_stack:
                        parent_folder = self._find_folder_by_name(result, folder_stack[-1])
                        if parent_folder:
                            parent_folder["items"].append(bookmark)
                        else:
                            result.append(bookmark)
                    else:
                        result.append(bookmark)
        
        return result
    
    def _find_folder_by_name(self, folders: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
        """
        Findet einen Ordner anhand seines Namens in der Ordnerhierarchie.
        
        Args:
            folders: Liste von Ordnern und Lesezeichen
            name: Name des gesuchten Ordners
            
        Returns:
            Der gefundene Ordner oder None
        """
        for item in folders:
            if item.get("type") == "folder" and item.get("name") == name:
                return item
            
            # Rekursive Suche in Unterordnern
            if item.get("type") == "folder" and "items" in item:
                found = self._find_folder_by_name(item["items"], name)
                if found:
                    return found
        
        return None
    
    def _parse_bookmark_tag(self, a_tag: Any, folder: str, depth: int) -> Optional[Dict[str, Any]]:
        """
        Parst ein einzelnes Lesezeichen-Tag.
        
        Args:
            a_tag: A-Tag mit dem Lesezeichen
            folder: Name des Ordners, in dem sich das Lesezeichen befindet
            depth: Verschachtelungstiefe
            
        Returns:
            Dictionary mit Lesezeichen-Informationen oder None, wenn ungültig
        """
        url = a_tag.get('href', '')
        
        # Überprüfe, ob dies ein gültiges Lesezeichen ist
        if not url or url.startswith('javascript:') or url == '#':
            return None
        
        # Überprüfe auf gültige URL
        if not self._is_valid_url(url):
            self.stats["invalid_urls"] += 1
            logger.debug(f"Invalid URL: {url}")
            return None
        
        # Überprüfe auf Duplikate
        if url in self.url_set:
            self.stats["duplicate_urls"] += 1
            logger.debug(f"Duplicate URL: {url}")
            return None
        
        self.url_set.add(url)
        
        # Extrahiere Titel
        title = a_tag.get_text(strip=True)
        if not title:
            title = url
            self.stats["empty_titles"] += 1
        
        # Extrahiere weitere Metadaten
        add_date = a_tag.get('add_date') or a_tag.get('added')
        last_modified = a_tag.get('last_modified')
        icon = a_tag.get('icon')
        
        # Extrahiere Tags (falls vorhanden)
        tags = []
        tags_attr = a_tag.get('tags')
        if tags_attr:
            tags = [tag.strip() for tag in tags_attr.split(',')]
        
        # Extrahiere Beschreibung (falls vorhanden)
        description = ""
        desc_element = a_tag.find_next_sibling('dd')
        if desc_element:
            description = desc_element.get_text(strip=True)
        
        bookmark = {
            "type": "bookmark",
            "title": title,
            "url": url,
            "folder": folder,
            "depth": depth,
            "added": self._convert_timestamp(add_date) if add_date else None,
            "last_modified": self._convert_timestamp(last_modified) if last_modified else None,
            "description": description if description else None,
            "tags": tags if tags else None,
            "icon": icon if icon else None
        }
        
        self.stats["total_bookmarks"] += 1
        return bookmark
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Überprüft, ob eine URL gültig ist.
        
        Args:
            url: Die zu überprüfende URL
            
        Returns:
            True, wenn die URL gültig ist, sonst False
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _convert_timestamp(self, timestamp: str) -> Optional[str]:
        """
        Konvertiert einen Unix-Timestamp in ein ISO-Datumsformat.
        
        Args:
            timestamp: Unix-Timestamp als String
            
        Returns:
            ISO-formatiertes Datum oder None bei Fehler
        """
        try:
            # Einige Browser speichern den Timestamp in Sekunden, andere in Millisekunden
            ts = int(timestamp)
            if ts > 10000000000:  # Vermutlich Millisekunden
                ts = ts / 1000
            
            dt = datetime.fromtimestamp(ts)
            return dt.isoformat()
        except:
            return None
    
    def extract_urls(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrahiert alle URLs aus einer geparsten Struktur und gibt sie als Liste zurück.
        
        Args:
            parsed_data: Die von parse_file() zurückgegebene Struktur
            
        Returns:
            Liste von Dictionaries mit URL-Informationen
        """
        urls = []
        
        def extract_from_items(items, path=None):
            if path is None:
                path = []
            
            for item in items:
                if item.get("type") == "bookmark":
                    url_data = {
                        "id": f"bm_{len(urls) + 1}",
                        "url": item.get("url"),
                        "title": item.get("title"),
                        "folder": item.get("folder"),
                        "folder_path": "/".join(path),
                        "added": item.get("added"),
                        "tags": item.get("tags")
                    }
                    urls.append(url_data)
                elif item.get("type") == "folder" and "items" in item:
                    new_path = path + [item.get("name")]
                    extract_from_items(item.get("items"), new_path)
        
        if "bookmarks" in parsed_data:
            extract_from_items(parsed_data["bookmarks"])
        
        return urls
    
    def save_to_file(self, parsed_data: Dict[str, Any], output_file: str) -> None:
        """
        Speichert die geparsten Daten in einer JSON-Datei.
        
        Args:
            parsed_data: Die von parse_file() zurückgegebene Struktur
            output_file: Pfad zur Ausgabedatei
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Parsed bookmarks saved to {output_file}")
    
    def save_urls_to_file(self, urls: List[Dict[str, Any]], output_file: str) -> None:
        """
        Speichert eine Liste von URLs in einer Textdatei (eine URL pro Zeile).
        
        Args:
            urls: Liste von URL-Dictionaries
            output_file: Pfad zur Ausgabedatei
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            for url_data in urls:
                f.write(f"{url_data['url']}\n")
        
        logger.info(f"Extracted {len(urls)} URLs saved to {output_file}")
    
    def save_bookmarks_to_file(self, bookmarks: List[Dict[str, Any]], output_file: str) -> None:
        """
        Speichert eine Liste von Bookmark-Dictionaries als JSON-Datei.
        
        Args:
            bookmarks: Liste von Bookmark-Dictionaries
            output_file: Pfad zur Ausgabedatei
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(bookmarks, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(bookmarks)} bookmarks to {output_file}")

def main():
    """Hauptfunktion zum Parsen von Lesezeichen über die Kommandozeile."""
    parser = argparse.ArgumentParser(description="Parse HTML bookmark files to structured JSON")
    parser.add_argument("input_file", help="Path to the HTML bookmark file")
    parser.add_argument("--output", "-o", default=None, 
                      help="Output file path (default: input filename with .json extension)")
    parser.add_argument("--urls-only", "-u", action="store_true",
                      help="Extract URLs only to a text file")
    parser.add_argument("--urls-file", default=None,
                      help="Output file for extracted URLs (default: input filename with .urls.txt extension)")
    
    args = parser.parse_args()
    
    # Setze Standardwerte für Ausgabedateien
    if not args.output:
        input_path = Path(args.input_file)
        args.output = str(input_path.with_suffix('.json'))
    
    if args.urls_only and not args.urls_file:
        input_path = Path(args.input_file)
        args.urls_file = str(input_path.with_suffix('.urls.txt'))
    
    try:
        # Parse die Lesezeichendatei
        parser = BookmarkParser()
        parsed_data = parser.parse_file(args.input_file)
        
        # Speichere die geparsten Daten
        parser.save_to_file(parsed_data, args.output)
        
        # Extrahiere URLs, wenn gewünscht
        if args.urls_only:
            urls = parser.extract_urls(parsed_data)
            parser.save_urls_to_file(urls, args.urls_file)
        
        # Ausgabe der Statistiken
        stats = parsed_data.get("metadata", {}).get("stats", {})
        print("Parsing Statistics:")
        print(f"- Total Bookmarks: {stats.get('total_bookmarks', 0)}")
        print(f"- Total Folders: {stats.get('total_folders', 0)}")
        print(f"- Invalid URLs: {stats.get('invalid_urls', 0)}")
        print(f"- Duplicate URLs: {stats.get('duplicate_urls', 0)}")
        print(f"- Empty Titles: {stats.get('empty_titles', 0)}")
        print(f"- Maximum Folder Depth: {stats.get('max_depth', 0)}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error parsing bookmarks: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    main() 