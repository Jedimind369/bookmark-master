#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Initialisiert die SQLite-Datenbank für das Bookmark-Projekt.
Erstellt die notwendigen Tabellen, wenn sie noch nicht existieren.
"""

import os
import sqlite3
import argparse
import logging
from pathlib import Path

# Konfiguriere Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database(db_path):
    """
    Initialisiert die SQLite-Datenbank mit den notwendigen Tabellen.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
    """
    # Erstelle Verzeichnis, falls es nicht existiert
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Verbindung zur Datenbank herstellen
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Erstelle die Tabelle pages für die gescrapten Seiten
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pages (
        url TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        article_text TEXT,
        scraper_used TEXT,
        scrape_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        folder TEXT,
        folder_path TEXT,
        added DATETIME,
        tags TEXT
    )
    ''')
    
    # Erstelle die Tabelle embeddings für die generierten Embeddings
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS embeddings (
        url TEXT PRIMARY KEY,
        embedding BLOB,
        model TEXT,
        generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (url) REFERENCES pages (url)
    )
    ''')
    
    # Erstelle die Tabelle clusters für die Cluster-Informationen
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clusters (
        url TEXT,
        cluster_id INTEGER,
        model TEXT,
        generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (url, model),
        FOREIGN KEY (url) REFERENCES pages (url)
    )
    ''')
    
    # Erstelle Index für schnellere Abfragen
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pages_folder ON pages (folder)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pages_added ON pages (added)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_clusters_cluster_id ON clusters (cluster_id)')
    
    # Änderungen speichern und Verbindung schließen
    conn.commit()
    conn.close()
    
    logger.info(f"Datenbank erfolgreich initialisiert: {db_path}")

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Initialisiert die SQLite-Datenbank für das Bookmark-Projekt")
    parser.add_argument("--db-path", default="data/database/bookmarks.db", help="Pfad zur SQLite-Datenbank")
    args = parser.parse_args()
    
    init_database(args.db_path)
    
    logger.info("Datenbank-Initialisierung abgeschlossen.")

if __name__ == "__main__":
    main() 