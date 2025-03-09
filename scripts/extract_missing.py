#!/usr/bin/env python3
"""
Extrahiert Lesezeichen ohne Beschreibungen in eine separate Datei.
"""

import json
import os
from pathlib import Path

def extract_missing_descriptions(input_file, output_file):
    """
    Extrahiert Lesezeichen ohne Beschreibungen.
    
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
    missing = [b for b in data if not b.get('description')]
    
    # Speichere die gefilterten Lesezeichen
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(missing, f, indent=2)
    
    print(f'Extrahiert: {len(missing)} von {len(data)} Lesezeichen ohne Beschreibungen')
    print(f'Gespeichert in: {output_file}')

def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extrahiert Lesezeichen ohne Beschreibungen")
    parser.add_argument("input_file", help="Pfad zur Eingabe-JSON-Datei")
    parser.add_argument("--output-file", default="data/processed/missing_descriptions.json",
                        help="Pfad zur Ausgabe-JSON-Datei")
    
    args = parser.parse_args()
    
    # Extrahiere Lesezeichen ohne Beschreibungen
    extract_missing_descriptions(args.input_file, args.output_file)

if __name__ == "__main__":
    main() 