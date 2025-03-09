#!/usr/bin/env python3
"""
Überprüft die Vollständigkeit der Beschreibungen in den angereicherten Lesezeichen.
"""

import json
import sys
from pathlib import Path

def check_descriptions(file_path):
    """
    Überprüft die Vollständigkeit der Beschreibungen in den angereicherten Lesezeichen.
    
    Args:
        file_path: Pfad zur JSON-Datei mit den angereicherten Lesezeichen
    """
    # Lade die angereicherten Lesezeichen
    with open(file_path, 'r', encoding='utf-8') as f:
        bookmarks = json.load(f)
    
    print(f'Anzahl der Lesezeichen: {len(bookmarks)}')
    
    # Zähle die Lesezeichen mit und ohne Beschreibungen
    with_desc = 0
    without_desc = 0
    short_desc = 0
    
    # Überprüfe jedes Lesezeichen
    print('\nLesezeichen ohne Beschreibung:')
    for i, bookmark in enumerate(bookmarks):
        desc = bookmark.get('description', '')
        
        if not desc:
            without_desc += 1
            print(f'{i+1}. {bookmark.get("title", "Kein Titel")} - URL: {bookmark.get("url", "Keine URL")}')
        elif len(desc) < 50:
            short_desc += 1
            with_desc += 1
        else:
            with_desc += 1
    
    print(f'\nLesezeichen mit kurzer Beschreibung (< 50 Zeichen):')
    for i, bookmark in enumerate(bookmarks):
        desc = bookmark.get('description', '')
        
        if desc and len(desc) < 50:
            print(f'{i+1}. {bookmark.get("title", "Kein Titel")} - Beschreibung: {desc}')
    
    # Zeige Statistiken
    print('\nStatistiken:')
    print(f'Lesezeichen mit Beschreibung: {with_desc} ({with_desc/len(bookmarks)*100:.1f}%)')
    print(f'Lesezeichen ohne Beschreibung: {without_desc} ({without_desc/len(bookmarks)*100:.1f}%)')
    print(f'Lesezeichen mit kurzer Beschreibung: {short_desc} ({short_desc/len(bookmarks)*100:.1f}%)')

def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Überprüft die Vollständigkeit der Beschreibungen")
    parser.add_argument("input_file", help="Pfad zur JSON-Datei mit den angereicherten Lesezeichen")
    
    args = parser.parse_args()
    
    # Überprüfe die Beschreibungen
    check_descriptions(args.input_file)

if __name__ == "__main__":
    main() 