#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stellt Funktionen für Datenbankoperationen bereit.
Speichert und ruft Daten aus der SQLite-Datenbank ab.
"""

import os
import json
import gzip
import sqlite3
import logging
import pickle
from datetime import datetime
from pathlib import Path

# Konfiguriere Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BookmarkDB:
    """Klasse für Datenbankoperationen mit dem Bookmark-Projekt."""
    
    def __init__(self, db_path="data/database/bookmarks.db"):
        """
        Initialisiert die Datenbankverbindung.
        
        Args:
            db_path: Pfad zur SQLite-Datenbank
        """
        self.db_path = db_path
        
        # Stelle sicher, dass das Datenbankverzeichnis existiert
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Teste die Verbindung
        self._test_connection()
    
    def _test_connection(self):
        """Testet die Verbindung zur Datenbank."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.close()
            logger.debug(f"Verbindung zur Datenbank erfolgreich: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Verbindungsfehler zur Datenbank: {str(e)}")
            raise
    
    def _get_connection(self):
        """
        Stellt eine Verbindung zur Datenbank her.
        
        Returns:
            sqlite3.Connection: Datenbankverbindung
        """
        return sqlite3.connect(self.db_path)
    
    def save_page(self, page_data):
        """
        Speichert eine gescrapte Seite in der Datenbank.
        
        Args:
            page_data: Dictionary mit den Seitendaten (url, title, article_text, etc.)
            
        Returns:
            bool: True, wenn erfolgreich, sonst False
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Bereite Daten vor
            url = page_data.get('url')
            title = page_data.get('title', '')
            description = page_data.get('description', '')
            article_text = page_data.get('article_text', '')
            scraper_used = page_data.get('scraper_used', '')
            scrape_time = page_data.get('scrape_time', datetime.now().isoformat())
            folder = page_data.get('folder', '')
            folder_path = page_data.get('folder_path', '')
            added = page_data.get('added', '')
            
            # Konvertiere Tags zu JSON, falls vorhanden
            tags = json.dumps(page_data.get('tags', [])) if page_data.get('tags') else None
            
            # SQL-Anweisung für INSERT oder UPDATE
            cursor.execute('''
            INSERT OR REPLACE INTO pages
            (url, title, description, article_text, scraper_used, scrape_time, folder, folder_path, added, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (url, title, description, article_text, scraper_used, scrape_time, folder, folder_path, added, tags))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Seite erfolgreich gespeichert: {url}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Fehler beim Speichern der Seite {page_data.get('url', 'unbekannt')}: {str(e)}")
            return False
    
    def save_pages_batch(self, pages):
        """
        Speichert mehrere gescrapte Seiten in einem Batch.
        
        Args:
            pages: Liste von Dictionaries mit Seitendaten
            
        Returns:
            int: Anzahl der erfolgreich gespeicherten Seiten
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Beginne Transaktion
            conn.execute('BEGIN TRANSACTION')
            
            success_count = 0
            for page_data in pages:
                try:
                    # Bereite Daten vor
                    url = page_data.get('url')
                    title = page_data.get('title', '')
                    description = page_data.get('description', '')
                    article_text = page_data.get('article_text', '')
                    scraper_used = page_data.get('scraper_used', '')
                    scrape_time = page_data.get('scrape_time', datetime.now().isoformat())
                    folder = page_data.get('folder', '')
                    folder_path = page_data.get('folder_path', '')
                    added = page_data.get('added', '')
                    
                    # Konvertiere Tags zu JSON, falls vorhanden
                    tags = json.dumps(page_data.get('tags', [])) if page_data.get('tags') else None
                    
                    # SQL-Anweisung für INSERT oder UPDATE
                    cursor.execute('''
                    INSERT OR REPLACE INTO pages
                    (url, title, description, article_text, scraper_used, scrape_time, folder, folder_path, added, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (url, title, description, article_text, scraper_used, scrape_time, folder, folder_path, added, tags))
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Fehler beim Speichern der Seite {page_data.get('url', 'unbekannt')}: {str(e)}")
            
            # Commit Transaktion
            conn.commit()
            conn.close()
            
            logger.info(f"{success_count} von {len(pages)} Seiten erfolgreich gespeichert")
            return success_count
            
        except sqlite3.Error as e:
            logger.error(f"Datenbankfehler beim Batch-Speichern: {str(e)}")
            if 'conn' in locals() and conn:
                conn.rollback()
                conn.close()
            return 0
    
    def get_page(self, url):
        """
        Ruft eine gescrapte Seite aus der Datenbank ab.
        
        Args:
            url: URL der abzurufenden Seite
            
        Returns:
            dict: Seitendaten oder None, wenn nicht gefunden
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM pages WHERE url = ?', (url,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
                
            # Spaltenname
            columns = [col[0] for col in cursor.description]
            page_data = dict(zip(columns, row))
            
            # Konvertiere JSON-Tags zurück zu Liste
            if page_data.get('tags'):
                try:
                    page_data['tags'] = json.loads(page_data['tags'])
                except json.JSONDecodeError:
                    page_data['tags'] = []
            
            conn.close()
            return page_data
            
        except sqlite3.Error as e:
            logger.error(f"Fehler beim Abrufen der Seite {url}: {str(e)}")
            return None
    
    def get_pages(self, limit=None, offset=0, folder=None, order_by='added DESC'):
        """
        Ruft mehrere gescrapte Seiten aus der Datenbank ab.
        
        Args:
            limit: Maximale Anzahl abzurufender Seiten
            offset: Offset für Paginierung
            folder: Filter nach Ordner
            order_by: Sortierung
            
        Returns:
            list: Liste von Seitendaten
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM pages'
            params = []
            
            # Füge Filter hinzu
            if folder:
                query += ' WHERE folder = ?'
                params.append(folder)
            
            # Füge Sortierung hinzu
            query += f' ORDER BY {order_by}'
            
            # Füge Limit und Offset hinzu
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
                
                if offset:
                    query += ' OFFSET ?'
                    params.append(offset)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Spaltenname
            columns = [col[0] for col in cursor.description]
            
            # Konvertiere Zeilen zu Dictionaries
            pages = []
            for row in rows:
                page_data = dict(zip(columns, row))
                
                # Konvertiere JSON-Tags zurück zu Liste
                if page_data.get('tags'):
                    try:
                        page_data['tags'] = json.loads(page_data['tags'])
                    except json.JSONDecodeError:
                        page_data['tags'] = []
                
                pages.append(page_data)
            
            conn.close()
            return pages
            
        except sqlite3.Error as e:
            logger.error(f"Fehler beim Abrufen der Seiten: {str(e)}")
            return []
    
    def save_embedding(self, url, embedding, model):
        """
        Speichert ein Embedding in der Datenbank.
        
        Args:
            url: URL der Seite
            embedding: Embedding-Vektor
            model: Name des verwendeten Modells
            
        Returns:
            bool: True, wenn erfolgreich, sonst False
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Serialisiere das Embedding
            embedding_blob = pickle.dumps(embedding)
            
            cursor.execute('''
            INSERT OR REPLACE INTO embeddings (url, embedding, model)
            VALUES (?, ?, ?)
            ''', (url, embedding_blob, model))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Embedding für {url} erfolgreich gespeichert")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Fehler beim Speichern des Embeddings für {url}: {str(e)}")
            return False
    
    def get_embedding(self, url, model):
        """
        Ruft ein Embedding aus der Datenbank ab.
        
        Args:
            url: URL der Seite
            model: Name des verwendeten Modells
            
        Returns:
            array: Embedding-Vektor oder None, wenn nicht gefunden
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT embedding FROM embeddings WHERE url = ? AND model = ?', (url, model))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
                
            # Deserialisiere das Embedding
            embedding = pickle.loads(row[0])
            
            conn.close()
            return embedding
            
        except sqlite3.Error as e:
            logger.error(f"Fehler beim Abrufen des Embeddings für {url}: {str(e)}")
            return None
    
    def save_cluster(self, url, cluster_id, model):
        """
        Speichert eine Cluster-Zuordnung in der Datenbank.
        
        Args:
            url: URL der Seite
            cluster_id: ID des Clusters
            model: Name des verwendeten Modells
            
        Returns:
            bool: True, wenn erfolgreich, sonst False
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO clusters (url, cluster_id, model)
            VALUES (?, ?, ?)
            ''', (url, cluster_id, model))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Cluster für {url} erfolgreich gespeichert")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Fehler beim Speichern des Clusters für {url}: {str(e)}")
            return False
    
    def get_pages_by_cluster(self, cluster_id, model):
        """
        Ruft alle Seiten eines Clusters aus der Datenbank ab.
        
        Args:
            cluster_id: ID des Clusters
            model: Name des verwendeten Modells
            
        Returns:
            list: Liste von Seitendaten
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT p.* FROM pages p
            JOIN clusters c ON p.url = c.url
            WHERE c.cluster_id = ? AND c.model = ?
            ''', (cluster_id, model))
            
            rows = cursor.fetchall()
            
            # Spaltenname
            columns = [col[0] for col in cursor.description]
            
            # Konvertiere Zeilen zu Dictionaries
            pages = []
            for row in rows:
                page_data = dict(zip(columns, row))
                
                # Konvertiere JSON-Tags zurück zu Liste
                if page_data.get('tags'):
                    try:
                        page_data['tags'] = json.loads(page_data['tags'])
                    except json.JSONDecodeError:
                        page_data['tags'] = []
                
                pages.append(page_data)
            
            conn.close()
            return pages
            
        except sqlite3.Error as e:
            logger.error(f"Fehler beim Abrufen der Seiten für Cluster {cluster_id}: {str(e)}")
            return []
    
    def import_from_json(self, json_file):
        """
        Importiert Seiten aus einer JSON-Datei in die Datenbank.
        
        Args:
            json_file: Pfad zur JSON-Datei
            
        Returns:
            int: Anzahl der importierten Seiten
        """
        try:
            # Öffne die JSON-Datei
            if json_file.endswith('.gz'):
                with gzip.open(json_file, 'rt', encoding='utf-8') as f:
                    pages = json.load(f)
            else:
                with open(json_file, 'r', encoding='utf-8') as f:
                    pages = json.load(f)
            
            # Speichere die Seiten in der Datenbank
            return self.save_pages_batch(pages)
            
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Fehler beim Import aus {json_file}: {str(e)}")
            return 0
    
    def export_to_json(self, json_file, compress=True, limit=None):
        """
        Exportiert Seiten aus der Datenbank in eine JSON-Datei.
        
        Args:
            json_file: Pfad zur JSON-Datei
            compress: Ob die Datei komprimiert werden soll
            limit: Maximale Anzahl zu exportierender Seiten
            
        Returns:
            int: Anzahl der exportierten Seiten
        """
        try:
            # Hole die Seiten aus der Datenbank
            pages = self.get_pages(limit=limit)
            
            # Schreibe die Seiten in die JSON-Datei
            if compress:
                with gzip.open(json_file, 'wt', encoding='utf-8') as f:
                    json.dump(pages, f, ensure_ascii=False, indent=2)
            else:
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(pages, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{len(pages)} Seiten erfolgreich nach {json_file} exportiert")
            return len(pages)
            
        except (IOError, sqlite3.Error) as e:
            logger.error(f"Fehler beim Export nach {json_file}: {str(e)}")
            return 0

# Beispielnutzung
if __name__ == "__main__":
    db = BookmarkDB()
    
    # Beispiel: Speichere eine Seite
    page = {
        'url': 'https://example.com',
        'title': 'Example Domain',
        'description': 'This domain is for use in illustrative examples in documents.',
        'article_text': 'This domain is established to be used for illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.',
        'scraper_used': 'example',
        'scrape_time': datetime.now().isoformat(),
        'folder': 'Examples',
        'folder_path': 'Examples',
        'added': '2023-01-01T00:00:00',
        'tags': ['example', 'test']
    }
    
    db.save_page(page)
    print("Beispielseite gespeichert.") 