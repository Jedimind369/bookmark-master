import os
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

def merge_bookmark_results(input_dirs: List[str], output_dir: str) -> Dict[str, Any]:
    """
    Führt die Ergebnisse aus mehreren Verarbeitungsläufen zusammen.
    
    Args:
        input_dirs: Liste der Eingabeverzeichnisse
        output_dir: Ausgabeverzeichnis
    
    Returns:
        Dict mit Statistiken über die zusammengeführten Ergebnisse
    """
    # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialisiere Listen für gültige und ungültige Lesezeichen
    all_valid_bookmarks = []
    all_invalid_bookmarks = []
    
    # Statistiken
    stats = {
        "total_processed": 0,
        "valid_bookmarks": 0,
        "invalid_bookmarks": 0,
        "input_dirs": input_dirs,
        "runs": []
    }
    
    # Verarbeite jedes Eingabeverzeichnis
    for input_dir in input_dirs:
        print(f"Verarbeite Verzeichnis: {input_dir}")
        
        # Lade die Statistiken
        stats_file = os.path.join(input_dir, "processing_stats.json")
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                run_stats = json.load(f)
                stats["runs"].append(run_stats)
                stats["total_processed"] += run_stats.get("total_processed", 0)
        
        # Lade gültige Lesezeichen
        valid_file = os.path.join(input_dir, "all_valid_bookmarks.json")
        if os.path.exists(valid_file):
            with open(valid_file, 'r', encoding='utf-8') as f:
                valid_bookmarks = json.load(f)
                all_valid_bookmarks.extend(valid_bookmarks)
                print(f"  Geladen: {len(valid_bookmarks)} gültige Lesezeichen")
        
        # Lade ungültige Lesezeichen
        invalid_file = os.path.join(input_dir, "all_invalid_bookmarks.json")
        if os.path.exists(invalid_file):
            with open(invalid_file, 'r', encoding='utf-8') as f:
                invalid_bookmarks = json.load(f)
                all_invalid_bookmarks.extend(invalid_bookmarks)
                print(f"  Geladen: {len(invalid_bookmarks)} ungültige Lesezeichen")
    
    # Aktualisiere die Statistiken
    stats["valid_bookmarks"] = len(all_valid_bookmarks)
    stats["invalid_bookmarks"] = len(all_invalid_bookmarks)
    
    # Speichere die zusammengeführten Ergebnisse
    valid_output_file = os.path.join(output_dir, "merged_valid_bookmarks.json")
    invalid_output_file = os.path.join(output_dir, "merged_invalid_bookmarks.json")
    stats_output_file = os.path.join(output_dir, "merged_stats.json")
    
    with open(valid_output_file, 'w', encoding='utf-8') as f:
        json.dump(all_valid_bookmarks, f, ensure_ascii=False, indent=2)
    
    with open(invalid_output_file, 'w', encoding='utf-8') as f:
        json.dump(all_invalid_bookmarks, f, ensure_ascii=False, indent=2)
    
    with open(stats_output_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"Zusammenführung abgeschlossen. Statistiken:")
    print(f"  Verarbeitete Lesezeichen: {stats['total_processed']}")
    print(f"  Gültige Lesezeichen: {stats['valid_bookmarks']}")
    print(f"  Ungültige Lesezeichen: {stats['invalid_bookmarks']}")
    print(f"Ergebnisse gespeichert in {output_dir}")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="Führt die Ergebnisse aus mehreren Verarbeitungsläufen zusammen")
    parser.add_argument("--input-dirs", nargs="+", required=True,
                        help="Liste der Eingabeverzeichnisse")
    parser.add_argument("--output-dir", default="data/processed/merged",
                        help="Ausgabeverzeichnis")
    
    args = parser.parse_args()
    
    merge_bookmark_results(args.input_dirs, args.output_dir)

if __name__ == "__main__":
    main() 