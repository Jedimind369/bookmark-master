#!/usr/bin/env python3
"""
Führt die Ergebnisse aus verschiedenen Quellen zusammen.
"""

import json
import os
from pathlib import Path

def merge_results(original_file, improved_file, zyte_file, output_file):
    """
    Führt die Ergebnisse aus verschiedenen Quellen zusammen.
    
    Args:
        original_file: Pfad zur ursprünglichen JSON-Datei
        improved_file: Pfad zur verbesserten JSON-Datei
        zyte_file: Pfad zur Zyte-JSON-Datei
        output_file: Pfad zur Ausgabe-JSON-Datei
    """
    # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Lade die ursprünglichen Daten
    with open(original_file, 'r', encoding='utf-8') as f:
        original = json.load(f)
    
    # Lade die verbesserten Daten
    with open(improved_file, 'r', encoding='utf-8') as f:
        improved = json.load(f)
    
    # Lade die Zyte-Daten
    with open(zyte_file, 'r', encoding='utf-8') as f:
        zyte = json.load(f)
    
    # Erstelle Dictionaries für schnellen Zugriff
    improved_dict = {b['url']: b for b in improved if 'url' in b}
    zyte_dict = {b['url']: b for b in zyte if 'url' in b}
    
    # Zähle die Aktualisierungen
    updated_count = 0
    
    # Aktualisiere die ursprünglichen Daten
    for i, bookmark in enumerate(original):
        if not bookmark.get('description') and 'url' in bookmark:
            # Versuche zuerst die verbesserte Beschreibung
            if bookmark['url'] in improved_dict and improved_dict[bookmark['url']].get('description'):
                original[i]['description'] = improved_dict[bookmark['url']]['description']
                updated_count += 1
            # Wenn nicht vorhanden, versuche die Zyte-Beschreibung
            elif bookmark['url'] in zyte_dict and zyte_dict[bookmark['url']].get('description'):
                original[i]['description'] = zyte_dict[bookmark['url']]['description']
                updated_count += 1
    
    # Speichere die zusammengeführten Daten
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(original, f, indent=2)
    
    print(f'Aktualisiert: {updated_count} Lesezeichen mit Beschreibungen')
    print(f'Gespeichert in: {output_file}')
    
    # Überprüfe, wie viele Lesezeichen immer noch keine Beschreibung haben
    still_missing = [b for b in original if not b.get('description')]
    print(f'Immer noch fehlend: {len(still_missing)} von {len(original)} Lesezeichen ohne Beschreibungen')
    
    if still_missing:
        print("\nLesezeichen ohne Beschreibung:")
        for i, bookmark in enumerate(still_missing):
            print(f"{i+1}. {bookmark.get('title', 'Kein Titel')} - URL: {bookmark.get('url', 'Keine URL')}")

def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Führt die Ergebnisse aus verschiedenen Quellen zusammen")
    parser.add_argument("original_file", help="Pfad zur ursprünglichen JSON-Datei")
    parser.add_argument("improved_file", help="Pfad zur verbesserten JSON-Datei")
    parser.add_argument("zyte_file", help="Pfad zur Zyte-JSON-Datei")
    parser.add_argument("--output-file", default="data/enriched/merged_enriched.json",
                        help="Pfad zur Ausgabe-JSON-Datei")
    
    args = parser.parse_args()
    
    # Führe die Ergebnisse zusammen
    merge_results(args.original_file, args.improved_file, args.zyte_file, args.output_file)

if __name__ == "__main__":
    main() 