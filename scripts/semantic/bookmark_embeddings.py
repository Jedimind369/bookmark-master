#!/usr/bin/env python3
"""
Bookmark-Embeddings-Modul.

Dieses Modul implementiert die Generierung und Verwaltung von Vektor-Embeddings
für Bookmarks mit Hilfe von sentence-transformers.
"""

import os
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from sentence_transformers import SentenceTransformer

class BookmarkEmbeddings:
    """
    Klasse zur Generierung und Verwaltung von Bookmark-Embeddings.
    
    Diese Klasse verwendet sentence-transformers, um Texte aus Bookmarks
    in Vektor-Embeddings umzuwandeln und diese zu verwalten.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialisiere die BookmarkEmbeddings-Klasse.
        
        Args:
            model_name: Name des zu verwendenden sentence-transformers-Modells.
                        Standard ist 'all-MiniLM-L6-v2', ein gutes Allzweckmodell.
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embeddings = {}  # Dict mit URL als Schlüssel und Embedding als Wert
        self.urls = []  # Liste aller URLs
        self.initialized = False
    
    def is_initialized(self) -> bool:
        """
        Prüfe, ob Embeddings initialisiert wurden.
        
        Returns:
            True, wenn Embeddings vorhanden sind, sonst False.
        """
        return self.initialized and len(self.embeddings) > 0
    
    def add_bookmarks(self, texts: List[str], urls: List[str]) -> None:
        """
        Füge Bookmarks hinzu und generiere Embeddings.
        
        Args:
            texts: Liste von Texten aus den Bookmarks (Titel, Beschreibung, Inhalt).
            urls: Liste von URLs, die den Texten entsprechen.
        
        Raises:
            ValueError: Wenn die Länge von texts und urls nicht übereinstimmt.
        """
        if len(texts) != len(urls):
            raise ValueError("Die Anzahl der Texte und URLs muss übereinstimmen.")
        
        # Generiere Embeddings für alle Texte
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Speichere die Embeddings mit den URLs als Schlüssel
        for i, url in enumerate(urls):
            self.embeddings[url] = embeddings[i]
            if url not in self.urls:
                self.urls.append(url)
        
        self.initialized = True
    
    def get_embedding(self, url: str) -> Optional[np.ndarray]:
        """
        Hole das Embedding für eine bestimmte URL.
        
        Args:
            url: Die URL, für die das Embedding abgerufen werden soll.
        
        Returns:
            Das Embedding als numpy-Array oder None, wenn die URL nicht gefunden wurde.
        """
        return self.embeddings.get(url)
    
    def get_embedding_for_text(self, text: str) -> np.ndarray:
        """
        Generiere ein Embedding für einen Text.
        
        Args:
            text: Der Text, für den ein Embedding generiert werden soll.
        
        Returns:
            Das generierte Embedding als numpy-Array.
        """
        return self.model.encode(text)
    
    def get_urls(self) -> List[str]:
        """
        Hole alle URLs, für die Embeddings vorhanden sind.
        
        Returns:
            Liste aller URLs.
        """
        return self.urls
    
    def get_count(self) -> int:
        """
        Hole die Anzahl der gespeicherten Embeddings.
        
        Returns:
            Anzahl der Embeddings.
        """
        return len(self.embeddings)
    
    def get_dimension(self) -> int:
        """
        Hole die Dimensionalität der Embeddings.
        
        Returns:
            Dimensionalität der Embeddings oder 0, wenn keine Embeddings vorhanden sind.
        """
        if not self.embeddings:
            return 0
        
        # Hole das erste Embedding und gib dessen Dimensionalität zurück
        first_embedding = next(iter(self.embeddings.values()))
        return len(first_embedding)
    
    def save(self, filepath: str) -> None:
        """
        Speichere die Embeddings in einer Datei.
        
        Args:
            filepath: Pfad zur Datei, in der die Embeddings gespeichert werden sollen.
        """
        data = {
            'model_name': self.model_name,
            'embeddings': self.embeddings,
            'urls': self.urls
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
    
    def load(self, filepath: str) -> None:
        """
        Lade Embeddings aus einer Datei.
        
        Args:
            filepath: Pfad zur Datei, aus der die Embeddings geladen werden sollen.
        
        Raises:
            FileNotFoundError: Wenn die Datei nicht gefunden wurde.
            ValueError: Wenn die Datei ungültige Daten enthält.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Die Datei {filepath} wurde nicht gefunden.")
        
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        # Prüfe, ob die Daten das erwartete Format haben
        if not all(key in data for key in ['model_name', 'embeddings', 'urls']):
            raise ValueError("Die Datei enthält ungültige Daten.")
        
        # Wenn das Modell in der Datei ein anderes ist, lade es neu
        if data['model_name'] != self.model_name:
            self.model_name = data['model_name']
            self.model = SentenceTransformer(self.model_name)
        
        self.embeddings = data['embeddings']
        self.urls = data['urls']
        self.initialized = True
    
    def clear(self) -> None:
        """Lösche alle gespeicherten Embeddings."""
        self.embeddings = {}
        self.urls = []
        self.initialized = False 