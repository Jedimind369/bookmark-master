#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.processing.process_bookmarks import process_partial_bookmarks

def simple_process(input_file, limit=200):
    """
    Einfache Funktion zum Verarbeiten einer HTML-Lesezeichendatei.
    
    Args:
        input_file (str): Pfad zur HTML-Lesezeichendatei
        limit (int): Maximale Anzahl der zu verarbeitenden Lesezeichen (0 = alle)
    
    Returns:
        tuple: (valid_bookmarks, invalid_bookmarks, stats)
    """
    print(f"Verarbeite Lesezeichendatei: {input_file}")
    
    # Erstelle Ausgabeverzeichnis
    output_dir = os.path.join("data", "processed", "simple_process")
    os.makedirs(output_dir, exist_ok=True)
    
    # Verarbeite die Datei
    end_index = None if limit == 0 else limit
    
    valid_bookmarks, invalid_bookmarks, stats = process_partial_bookmarks(
        input_file,
        output_dir,
        start_index=0,
        end_index=end_index,
        batch_size=50
    )
    
    # Zeige Statistiken
    print("\nVerarbeitung abgeschlossen!")
    print(f"Verarbeitete Lesezeichen: {stats['total_processed']}")
    print(f"Gültige Lesezeichen: {stats['valid_bookmarks']}")
    print(f"Ungültige Lesezeichen: {stats['invalid_bookmarks']}")
    print(f"Ergebnisse gespeichert in: {output_dir}")
    
    return valid_bookmarks, invalid_bookmarks, stats

def main():
    # Prüfe, ob eine Datei angegeben wurde
    if len(sys.argv) < 2:
        print("Fehler: Keine Eingabedatei angegeben.")
        print(f"Verwendung: python {sys.argv[0]} <pfad/zur/lesezeichen.html> [limit]")
        sys.exit(1)
    
    # Hole die Eingabedatei
    input_file = sys.argv[1]
    
    # Prüfe, ob die Datei existiert
    if not os.path.isfile(input_file):
        print(f"Fehler: Die Datei '{input_file}' existiert nicht.")
        sys.exit(1)
    
    # Hole das Limit (optional)
    limit = 200
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except ValueError:
            print(f"Warnung: Ungültiges Limit '{sys.argv[2]}'. Verwende Standardwert 200.")
    
    # Verarbeite die Datei
    simple_process(input_file, limit)

if __name__ == "__main__":
    main() 