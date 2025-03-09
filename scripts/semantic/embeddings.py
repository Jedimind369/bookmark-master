#!/usr/bin/env python3
"""
embeddings.py

Modul zur Generierung und Verwaltung von Vektor-Embeddings für Lesezeichen.
Verwendet SentenceTransformers, um Text in hochdimensionale Vektoren umzuwandeln,
die semantische Ähnlichkeit erfassen können.
"""

import os
import json
import torch
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from sentence_transformers import SentenceTransformer

class BookmarkEmbeddings:
    """Klasse zur Verwaltung von Embeddings für Lesezeichen."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialisiert das BookmarkEmbeddings-Objekt.
        
        Args:
            model_name: Name des zu verwendenden SentenceTransformer-Modells.
                        Standard ist "all-MiniLM-L6-v2", ein gutes Allzweckmodell.
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        
        # Erstelle Verzeichnisstruktur
        self.data_dir = Path("data/semantic")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.embeddings_file = self.data_dir / "bookmark_embeddings.json"
        
        # Lade vorhandene Embeddings oder initialisiere neue Datenstruktur
        self.load_embeddings()
    
    def load_embeddings(self):
        """Lädt Embeddings aus der Datei oder initialisiert die Datenstruktur."""
        if self.embeddings_file.exists():
            try:
                with open(self.embeddings_file, 'r', encoding='utf-8') as f:
                    self.embeddings_data = json.load(f)
                    
                    # Kompatibilitätsprüfung für ältere Versionen
                    if "metadata" not in self.embeddings_data:
                        self.embeddings_data["metadata"] = {
                            "model": self.model_name,
                            "last_updated": datetime.now().isoformat(),
                            "count": len(self.embeddings_data.get("bookmarks", {}))
                        }
            except (json.JSONDecodeError, IOError) as e:
                print(f"Fehler beim Laden der Embeddings: {str(e)}")
                self._initialize_new_data()
        else:
            self._initialize_new_data()
    
    def _initialize_new_data(self):
        """Initialisiert eine neue Embedding-Datenstruktur."""
        self.embeddings_data = {
            "bookmarks": {},
            "metadata": {
                "model": self.model_name,
                "last_updated": None,
                "count": 0
            }
        }
    
    def save_embeddings(self):
        """Speichert Embeddings in der Datei."""
        try:
            with open(self.embeddings_file, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings_data, f, indent=2)
        except IOError as e:
            print(f"Fehler beim Speichern der Embeddings: {str(e)}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generiert ein Embedding für einen Text.
        
        Args:
            text: Der zu embeddierende Text.
            
        Returns:
            Ein Embedding als Liste von Floats.
        """
        if not text.strip():
            return []
            
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def generate_embeddings(self, bookmarks: List[Dict[str, Any]]) -> int:
        """
        Generiert Embeddings für eine Liste von Lesezeichen.
        
        Args:
            bookmarks: Liste von Lesezeichen-Dictionaries, jedes muss mindestens 'id' enthalten.
                       'title' und 'description' werden für das Embedding verwendet.
            
        Returns:
            Anzahl der gespeicherten Embeddings.
        """
        added_count = 0
        
        for bookmark in bookmarks:
            if 'id' not in bookmark:
                continue
                
            bookmark_id = str(bookmark["id"])
            
            # Kombiniere Titel und Beschreibung für ein besseres Embedding
            title = bookmark.get('title', '')
            description = bookmark.get('description', '')
            tags = bookmark.get('tags', [])
            
            # Erstelle einen angereicherten Text für bessere Embeddings
            text = f"{title} {description}"
            
            # Füge Tags hinzu, wenn vorhanden
            if tags:
                tag_text = " ".join(tags)
                text += f" {tag_text}"
                
            if not text.strip():
                continue
            
            # Prüfe, ob dieses Lesezeichen bereits ein Embedding hat
            if bookmark_id in self.embeddings_data["bookmarks"]:
                # Prüfe, ob sich der Inhalt geändert hat
                existing_title = self.embeddings_data["bookmarks"][bookmark_id].get("title", "")
                existing_description = self.embeddings_data["bookmarks"][bookmark_id].get("description", "")
                existing_text = f"{existing_title} {existing_description}"
                
                if text == existing_text:
                    continue  # Keine Änderung, überspringe
            
            # Generiere das Embedding
            embedding = self.generate_embedding(text)
            
            if not embedding:
                continue
                
            # Speichere das Embedding und Metadaten
            self.embeddings_data["bookmarks"][bookmark_id] = {
                "embedding": embedding,
                "title": title,
                "description": description,
                "url": bookmark.get("url", ""),
                "tags": tags,
                "created": bookmark.get("created", datetime.now().isoformat())
            }
            
            added_count += 1
        
        # Aktualisiere Metadaten
        self.embeddings_data["metadata"]["count"] = len(self.embeddings_data["bookmarks"])
        self.embeddings_data["metadata"]["last_updated"] = datetime.now().isoformat()
        
        # Speichere die aktualisierten Embeddings
        self.save_embeddings()
        
        return added_count
    
    def get_embedding(self, bookmark_id: str) -> Optional[List[float]]:
        """
        Holt das Embedding für ein bestimmtes Lesezeichen.
        
        Args:
            bookmark_id: ID des Lesezeichens.
            
        Returns:
            Embedding als Liste von Floats oder None, wenn nicht gefunden.
        """
        if bookmark_id in self.embeddings_data["bookmarks"]:
            return self.embeddings_data["bookmarks"][bookmark_id]["embedding"]
        return None
    
    def get_all_embeddings(self) -> Dict[str, List[float]]:
        """
        Holt alle Embeddings.
        
        Returns:
            Dictionary mit Lesezeichen-IDs als Schlüssel und Embeddings als Werte.
        """
        return {
            bid: data["embedding"]
            for bid, data in self.embeddings_data["bookmarks"].items()
        }
    
    def delete_embedding(self, bookmark_id: str) -> bool:
        """
        Löscht das Embedding für ein bestimmtes Lesezeichen.
        
        Args:
            bookmark_id: ID des Lesezeichens.
            
        Returns:
            True bei Erfolg, False wenn das Embedding nicht existiert.
        """
        if bookmark_id in self.embeddings_data["bookmarks"]:
            del self.embeddings_data["bookmarks"][bookmark_id]
            
            # Aktualisiere Metadaten
            self.embeddings_data["metadata"]["count"] = len(self.embeddings_data["bookmarks"])
            self.embeddings_data["metadata"]["last_updated"] = datetime.now().isoformat()
            
            self.save_embeddings()
            return True
        return False
    
    def get_bookmark_metadata(self, bookmark_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt die Metadaten für ein bestimmtes Lesezeichen.
        
        Args:
            bookmark_id: ID des Lesezeichens.
            
        Returns:
            Dictionary mit Metadaten oder None, wenn nicht gefunden.
        """
        if bookmark_id in self.embeddings_data["bookmarks"]:
            bookmark_data = self.embeddings_data["bookmarks"][bookmark_id].copy()
            # Entferne das Embedding aus den zurückgegebenen Daten
            if "embedding" in bookmark_data:
                del bookmark_data["embedding"]
            return bookmark_data
        return None 