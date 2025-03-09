#!/usr/bin/env python3
"""
Überprüft, welche Lesezeichen immer noch keine Beschreibung haben.
"""

import json
import os
from pathlib import Path

def check_remaining(input_file, output_file):
    """
    Überprüft, welche Lesezeichen immer noch keine Beschreibung haben.
    
    Args:
        input_file: Pfad zur Eingabe-JSON-Datei
        output_file: Pfad zur Ausgabe-JSON-Datei
    """
    # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Lade die Lesezeichen
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filtere Lesezeichen ohne Beschreibungen
    still_missing = [b for b in data if not b.get('description')]
    
    # Speichere die gefilterten Lesezeichen
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(still_missing, f, indent=2)
    
    print(f'Immer noch fehlend: {len(still_missing)} von {len(data)} Lesezeichen ohne Beschreibungen')
    if still_missing:
        print("\nLesezeichen ohne Beschreibung:")
        for i, bookmark in enumerate(still_missing):
            print(f"{i+1}. {bookmark.get('title', 'Kein Titel')} - URL: {bookmark.get('url', 'Keine URL')}")
    
    print(f'\nGespeichert in: {output_file}')

def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Überprüft verbleibende Lesezeichen ohne Beschreibungen")
    parser.add_argument("input_file", help="Pfad zur Eingabe-JSON-Datei")
    parser.add_argument("--output-file", default="data/processed/still_missing.json",
                        help="Pfad zur Ausgabe-JSON-Datei")
    
    args = parser.parse_args()
    
    # Überprüfe verbleibende Lesezeichen ohne Beschreibungen
    check_remaining(args.input_file, args.output_file)

if __name__ == "__main__":
    main() 