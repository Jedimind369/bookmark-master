#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generiert verbesserte Beschreibungen für Webseiten in der SQLite-Datenbank.

Verwendet OpenAI's GPT-Modelle, um hochwertige Beschreibungen
für Webseiten zu generieren, die nicht bereits gute Beschreibungen haben.
"""

import os
import sys
import json
import time
import logging
import argparse
import sqlite3
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

# Füge das Projektverzeichnis zum Pfad hinzu
sys.path.append(str(Path(__file__).parent.parent.parent))

# Importiere die Datenbankklasse
from scripts.database.db_operations import BookmarkDB

# Lade Umgebungsvariablen aus .env-Datei
load_dotenv()

# Konfiguriere Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/enhanced_descriptions_db.log")
    ]
)
logger = logging.getLogger("enhanced_descriptions_db")

def get_openai_client():
    """
    Initialisiert den OpenAI-Client.
    
    Returns:
        OpenAI: OpenAI-Client oder None im Fehlerfall
    """
    try:
        from openai import OpenAI
        
        # Überprüfe, ob der API-Schlüssel in den Umgebungsvariablen vorhanden ist
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY nicht gefunden in .env-Datei")
            return None
        
        # Initialisiere den Client
        client = OpenAI(api_key=api_key)
        return client
        
    except ImportError:
        logger.error("OpenAI-Paket nicht installiert. Bitte installieren Sie es mit 'pip install openai'")
        return None
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung des OpenAI-Clients: {str(e)}")
        return None

def generate_description_with_openai(client, title, article_text, max_tokens=150):
    """
    Generiert eine Beschreibung mit OpenAI.
    
    Args:
        client: OpenAI-Client
        title: Titel der Webseite
        article_text: Extrahierter Text der Webseite
        max_tokens: Maximale Länge der Beschreibung in Tokens
        
    Returns:
        str: Generierte Beschreibung oder None im Fehlerfall
    """
    try:
        # Begrenze den Artikeltext auf 4000 Tokens (ca. 3000 Wörter)
        max_article_length = 16000
        if article_text and len(article_text) > max_article_length:
            article_text = article_text[:max_article_length] + "..."
        
        # Wenn kein Artikeltext vorhanden ist, verwende nur den Titel
        if not article_text or article_text.strip() == "":
            prompt = f"""Basierend auf dem Titel '{title}', erstelle eine präzise und informative Beschreibung. 
            Die Beschreibung sollte knapp und informativ sein und nicht mehr als 2-3 Sätze umfassen.
            Beschreibe den vermutlichen Inhalt und die Art der Webseite.
            """
        else:
            prompt = f"""Basierend auf dem Titel '{title}' und dem folgenden Artikeltext, erstelle eine präzise und informative Beschreibung. 
            Die Beschreibung sollte knapp und informativ sein und nicht mehr als 2-3 Sätze umfassen.
            
            Artikeltext:
            {article_text}
            """
        
        # Sende Anfrage an OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Du bist ein Experte für Metadaten und Web-Content. Deine Aufgabe ist es, präzise und informative Beschreibungen für Webseiten zu erstellen."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        # Extrahiere die generierte Beschreibung
        description = response.choices[0].message.content.strip()
        return description
        
    except Exception as e:
        logger.error(f"Fehler bei der Generierung der Beschreibung: {str(e)}")
        return None

def process_pages_without_descriptions(db_path, limit=None):
    """
    Verarbeitet alle Seiten in der Datenbank ohne Beschreibungen.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        limit: Maximale Anzahl zu verarbeitender Seiten
        
    Returns:
        int: Anzahl der verarbeiteten Seiten
    """
    # Initialisiere den OpenAI-Client
    client = get_openai_client()
    if not client:
        logger.error("OpenAI-Client konnte nicht initialisiert werden")
        return 0
    
    # Initialisiere die Datenbankverbindung
    db = BookmarkDB(db_path)
    
    # Hole alle Seiten aus der Datenbank
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Finde Seiten ohne Beschreibungen oder mit leeren Beschreibungen
    cursor.execute("""
        SELECT url, title, article_text FROM pages 
        WHERE description IS NULL OR description = '' OR description = 'null'
        ORDER BY scrape_time DESC
    """)
    
    pages = cursor.fetchall()
    conn.close()
    
    if limit and limit > 0:
        pages = pages[:limit]
    
    logger.info(f"{len(pages)} Seiten ohne Beschreibungen gefunden")
    
    # Verarbeite alle Seiten
    processed_count = 0
    for url, title, article_text in tqdm(pages, desc="Generiere Beschreibungen"):
        # Wenn kein Titel vorhanden ist, überspringe die Seite
        if not title or title.strip() == "":
            logger.warning(f"Überspringe {url}: Kein Titel vorhanden")
            continue
        
        # Generiere eine Beschreibung
        description = generate_description_with_openai(client, title, article_text)
        
        if description:
            # Aktualisiere die Beschreibung in der Datenbank
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE pages SET description = ? WHERE url = ?", (description, url))
            conn.commit()
            conn.close()
            
            processed_count += 1
            logger.debug(f"Beschreibung für {url} aktualisiert: {description[:50]}...")
        
        # Warte kurz, um die API-Rate-Limits zu respektieren
        time.sleep(0.5)
    
    logger.info(f"{processed_count} Beschreibungen erfolgreich generiert und in der Datenbank aktualisiert")
    return processed_count

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Generiert erweiterte Beschreibungen für Webseiten in der SQLite-Datenbank")
    parser.add_argument("--db-path", default="data/database/bookmarks.db", help="Pfad zur SQLite-Datenbank")
    parser.add_argument("--limit", type=int, help="Maximale Anzahl zu verarbeitender Seiten")
    args = parser.parse_args()
    
    # Verarbeite Seiten ohne Beschreibungen
    process_pages_without_descriptions(args.db_path, args.limit)
    
    logger.info("Beschreibungsgenerierung abgeschlossen")

if __name__ == "__main__":
    main() 