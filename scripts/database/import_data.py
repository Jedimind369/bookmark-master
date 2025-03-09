#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Importiert vorhandene Daten in die SQLite-Datenbank.
"""

import os
import sys
import json
import gzip
import glob
import argparse
import logging
from pathlib import Path

# Füge das Projektverzeichnis zum Pfad hinzu
sys.path.append(str(Path(__file__).parent.parent.parent))

# Importiere das Datenbankmodul
from scripts.database.db_operations import BookmarkDB
from scripts.database.init_db import init_database

# Konfiguriere Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def import_bookmarks(input_file, db_path):
    """
    Importiert Bookmarks aus einer JSON-Datei in die Datenbank.
    
    Args:
        input_file: Pfad zur JSON-Datei mit Bookmarks
        db_path: Pfad zur SQLite-Datenbank
        
    Returns:
        int: Anzahl der importierten Bookmarks
    """
    logger.info(f"Importiere Bookmarks aus {input_file}")
    
    try:
        # Stelle sicher, dass die Datenbank initialisiert ist
        init_database(db_path)
        
        # Erstelle eine Datenbankverbindung
        db = BookmarkDB(db_path)
        
        # Importiere die Daten
        imported_count = db.import_from_json(input_file)
        
        logger.info(f"{imported_count} Bookmarks erfolgreich importiert")
        return imported_count
        
    except Exception as e:
        logger.error(f"Fehler beim Import der Bookmarks: {str(e)}")
        return 0

def import_enriched_data(input_file, db_path):
    """
    Importiert angereicherte Daten aus einer JSON-Datei in die Datenbank.
    
    Args:
        input_file: Pfad zur JSON-Datei mit angereicherten Daten
        db_path: Pfad zur SQLite-Datenbank
        
    Returns:
        int: Anzahl der importierten Seiten
    """
    logger.info(f"Importiere angereicherte Daten aus {input_file}")
    
    try:
        # Stelle sicher, dass die Datenbank initialisiert ist
        init_database(db_path)
        
        # Erstelle eine Datenbankverbindung
        db = BookmarkDB(db_path)
        
        # Importiere die Daten
        imported_count = db.import_from_json(input_file)
        
        logger.info(f"{imported_count} angereicherte Seiten erfolgreich importiert")
        return imported_count
        
    except Exception as e:
        logger.error(f"Fehler beim Import der angereicherten Daten: {str(e)}")
        return 0

def import_batch_files(pattern, db_path):
    """
    Importiert mehrere Batch-Dateien in die Datenbank.
    
    Args:
        pattern: Glob-Pattern für die Batch-Dateien
        db_path: Pfad zur SQLite-Datenbank
        
    Returns:
        int: Anzahl der importierten Seiten
    """
    logger.info(f"Importiere Batch-Dateien mit Pattern {pattern}")
    
    try:
        # Stelle sicher, dass die Datenbank initialisiert ist
        init_database(db_path)
        
        # Erstelle eine Datenbankverbindung
        db = BookmarkDB(db_path)
        
        # Finde alle Batch-Dateien
        batch_files = sorted(glob.glob(pattern))
        logger.info(f"{len(batch_files)} Batch-Dateien gefunden")
        
        total_imported = 0
        for batch_file in batch_files:
            logger.info(f"Importiere {batch_file}")
            imported_count = db.import_from_json(batch_file)
            total_imported += imported_count
            logger.info(f"{imported_count} Seiten aus {batch_file} importiert")
        
        logger.info(f"Insgesamt {total_imported} Seiten erfolgreich importiert")
        return total_imported
        
    except Exception as e:
        logger.error(f"Fehler beim Import der Batch-Dateien: {str(e)}")
        return 0

def import_embeddings(embeddings_file, model, db_path):
    """
    Importiert Embeddings aus einer Pickle-Datei in die Datenbank.
    
    Args:
        embeddings_file: Pfad zur Pickle-Datei mit Embeddings
        model: Name des verwendeten Modells
        db_path: Pfad zur SQLite-Datenbank
        
    Returns:
        int: Anzahl der importierten Embeddings
    """
    import pickle
    
    logger.info(f"Importiere Embeddings aus {embeddings_file}")
    
    try:
        # Stelle sicher, dass die Datenbank initialisiert ist
        init_database(db_path)
        
        # Erstelle eine Datenbankverbindung
        db = BookmarkDB(db_path)
        
        # Lade die Embeddings
        with open(embeddings_file, 'rb') as f:
            embeddings_data = pickle.load(f)
        
        # Importiere die Embeddings
        imported_count = 0
        for url, embedding in embeddings_data.items():
            success = db.save_embedding(url, embedding, model)
            if success:
                imported_count += 1
        
        logger.info(f"{imported_count} Embeddings erfolgreich importiert")
        return imported_count
        
    except Exception as e:
        logger.error(f"Fehler beim Import der Embeddings: {str(e)}")
        return 0

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Importiert vorhandene Daten in die SQLite-Datenbank")
    parser.add_argument("--db-path", default="data/database/bookmarks.db", help="Pfad zur SQLite-Datenbank")
    
    subparsers = parser.add_subparsers(dest="command", help="Zu importierende Daten")
    
    # Parser für Bookmarks
    bookmarks_parser = subparsers.add_parser("bookmarks", help="Importiert Bookmarks")
    bookmarks_parser.add_argument("--input", required=True, help="Pfad zur JSON-Datei mit Bookmarks")
    
    # Parser für angereicherte Daten
    enriched_parser = subparsers.add_parser("enriched", help="Importiert angereicherte Daten")
    enriched_parser.add_argument("--input", required=True, help="Pfad zur JSON-Datei mit angereicherten Daten")
    
    # Parser für Batch-Dateien
    batch_parser = subparsers.add_parser("batch", help="Importiert Batch-Dateien")
    batch_parser.add_argument("--pattern", required=True, help="Glob-Pattern für die Batch-Dateien")
    
    # Parser für Embeddings
    embeddings_parser = subparsers.add_parser("embeddings", help="Importiert Embeddings")
    embeddings_parser.add_argument("--input", required=True, help="Pfad zur Pickle-Datei mit Embeddings")
    embeddings_parser.add_argument("--model", required=True, help="Name des verwendeten Modells")
    
    args = parser.parse_args()
    
    if args.command == "bookmarks":
        import_bookmarks(args.input, args.db_path)
    elif args.command == "enriched":
        import_enriched_data(args.input, args.db_path)
    elif args.command == "batch":
        import_batch_files(args.pattern, args.db_path)
    elif args.command == "embeddings":
        import_embeddings(args.input, args.model, args.db_path)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 