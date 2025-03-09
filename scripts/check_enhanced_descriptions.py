#!/usr/bin/env python3
"""
Überprüft die Qualität der generierten Beschreibungen.
"""

import json
import os
import sys
from pathlib import Path

def check_descriptions(input_file, num_samples=3):
    """
    Überprüft die Qualität der generierten Beschreibungen.
    
    Args:
        input_file: Pfad zur JSON-Datei mit den Lesezeichen
        num_samples: Anzahl der zu überprüfenden Lesezeichen
    """
    # Lade die Lesezeichen
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Überprüfe {num_samples} von {len(data)} Lesezeichen:\n")
    
    # Überprüfe die ersten num_samples Lesezeichen
    for i, bookmark in enumerate(data[:num_samples]):
        title = bookmark.get('title', 'Kein Titel')
        url = bookmark.get('url', 'Keine URL')
        description = bookmark.get('description', 'Keine Beschreibung')
        
        # Zähle die Sätze in der Beschreibung
        sentences = description.split('. ')
        num_sentences = len([s for s in sentences if s.strip()])
        
        print(f"{i+1}. {title}")
        print(f"   URL: {url}")
        print(f"   Beschreibung ({num_sentences} Sätze): {description[:150]}...")
        print()
    
    # Berechne die durchschnittliche Anzahl von Sätzen
    total_sentences = 0
    bookmarks_with_desc = 0
    
    for bookmark in data:
        description = bookmark.get('description', '')
        if description:
            sentences = description.split('. ')
            total_sentences += len([s for s in sentences if s.strip()])
            bookmarks_with_desc += 1
    
    avg_sentences = total_sentences / bookmarks_with_desc if bookmarks_with_desc > 0 else 0
    
    print(f"Statistik für alle {len(data)} Lesezeichen:")
    print(f"- Lesezeichen mit Beschreibung: {bookmarks_with_desc} ({bookmarks_with_desc/len(data)*100:.1f}%)")
    print(f"- Durchschnittliche Anzahl von Sätzen: {avg_sentences:.1f}")

def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Überprüft die Qualität der generierten Beschreibungen")
    parser.add_argument("input_file", help="Pfad zur JSON-Datei mit den Lesezeichen")
    parser.add_argument("--num-samples", type=int, default=3,
                        help="Anzahl der zu überprüfenden Lesezeichen")
    
    args = parser.parse_args()
    
    # Überprüfe die Beschreibungen
    check_descriptions(args.input_file, args.num_samples)

if __name__ == "__main__":
    main() 