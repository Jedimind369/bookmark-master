#!/usr/bin/env python3
"""
similarity.py

Modul zur Berechnung von Ähnlichkeiten zwischen Lesezeichen und für Clustering.
Verwendet FAISS für effiziente Vektorsuche und Ähnlichkeitsberechnungen.
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import logging

# Importiere lokale Module
from scripts.semantic.embeddings import BookmarkEmbeddings

# Versuche, FAISS zu importieren
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("FAISS ist nicht installiert. Verwende Python-basierte Ähnlichkeitsberechnung.")

class BookmarkSimilarity:
    """Klasse für Ähnlichkeitsberechnungen und Clustering von Lesezeichen."""
    
    def __init__(self, embeddings: BookmarkEmbeddings):
        """
        Initialisiert das BookmarkSimilarity-Objekt.
        
        Args:
            embeddings: Ein BookmarkEmbeddings-Objekt mit vorhandenen Embeddings.
        """
        self.embeddings = embeddings
        self.index = None
        self.bookmark_ids = []
        self.build_index()
    
    def build_index(self):
        """Erstellt einen Index für die Ähnlichkeitssuche."""
        # Hole alle Bookmark-IDs
        self.bookmark_ids = list(self.embeddings.embeddings_data["bookmarks"].keys())
        
        if not self.bookmark_ids:
            logging.warning("Keine Lesezeichen für den Index vorhanden.")
            return
        
        # Erstelle NumPy-Array aus den Embeddings
        embeddings_list = []
        for bid in self.bookmark_ids:
            embedding = self.embeddings.get_embedding(bid)
            if embedding:
                embeddings_list.append(embedding)
            else:
                # Entferne die ID, wenn kein Embedding gefunden wurde
                self.bookmark_ids.remove(bid)
        
        if not embeddings_list:
            logging.warning("Keine gültigen Embeddings gefunden.")
            return
            
        embeddings_array = np.array(embeddings_list).astype('float32')
        
        # Erstelle FAISS-Index oder nutze Numpy für die Ähnlichkeitsberechnung
        if FAISS_AVAILABLE:
            # Dimensionalität des ersten Embeddings
            dimension = embeddings_array.shape[1]
            
            # Erstelle FAISS-Index
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(embeddings_array)
            logging.info(f"FAISS-Index mit {len(self.bookmark_ids)} Embeddings erstellt.")
        else:
            # Speichere das Array für Numpy-basierte Ähnlichkeitsberechnungen
            self.embeddings_array = embeddings_array
            logging.info(f"Numpy-Ähnlichkeitsmatrix mit {len(self.bookmark_ids)} Embeddings erstellt.")
    
    def find_similar_bookmarks(self, bookmark_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Findet ähnliche Lesezeichen für ein bestimmtes Lesezeichen.
        
        Args:
            bookmark_id: ID des Lesezeichens.
            k: Anzahl der zu findenden ähnlichen Lesezeichen.
            
        Returns:
            Liste von Dictionaries mit ähnlichen Lesezeichen, sortiert nach Ähnlichkeit.
        """
        # Prüfe, ob das Lesezeichen existiert
        query_embedding = self.embeddings.get_embedding(bookmark_id)
        if not query_embedding or not self.bookmark_ids:
            return []
        
        query_embedding_np = np.array([query_embedding]).astype('float32')
        
        # Verwende FAISS oder Numpy je nach Verfügbarkeit
        if FAISS_AVAILABLE and self.index is not None:
            # Verwende FAISS für die Suche
            distances, indices = self.index.search(query_embedding_np, min(k + 1, len(self.bookmark_ids)))
            
            similar_bookmarks = []
            for i in range(len(indices[0])):
                idx = indices[0][i]
                if idx < len(self.bookmark_ids):
                    similar_id = self.bookmark_ids[idx]
                    # Überspringe das ursprüngliche Lesezeichen
                    if similar_id == bookmark_id:
                        continue
                        
                    metadata = self.embeddings.get_bookmark_metadata(similar_id)
                    if metadata:
                        similar_bookmarks.append({
                            "id": similar_id,
                            "title": metadata.get("title", ""),
                            "url": metadata.get("url", ""),
                            "tags": metadata.get("tags", []),
                            "similarity": 1.0 - float(distances[0][i])  # Konvertiere Distanz in Ähnlichkeit
                        })
            
            return similar_bookmarks
        else:
            # Verwende Numpy für die Ähnlichkeitsberechnung
            similarities = []
            
            for i, bid in enumerate(self.bookmark_ids):
                if bid == bookmark_id:
                    continue
                
                other_embedding = self.embeddings.get_embedding(bid)
                if not other_embedding:
                    continue
                
                # Berechne Kosinus-Ähnlichkeit
                other_embedding_np = np.array(other_embedding).astype('float32')
                similarity = self._cosine_similarity(query_embedding_np[0], other_embedding_np)
                
                metadata = self.embeddings.get_bookmark_metadata(bid)
                if metadata:
                    similarities.append({
                        "id": bid,
                        "title": metadata.get("title", ""),
                        "url": metadata.get("url", ""),
                        "tags": metadata.get("tags", []),
                        "similarity": float(similarity)
                    })
            
            # Sortiere nach Ähnlichkeit (absteigend)
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            # Begrenze auf k Ergebnisse
            return similarities[:k]
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Berechnet die Kosinus-Ähnlichkeit zwischen zwei Vektoren."""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def search_bookmarks(self, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Sucht nach Lesezeichen, die einem Suchbegriff ähnlich sind.
        
        Args:
            query_text: Der Suchbegriff.
            k: Anzahl der Ergebnisse.
            
        Returns:
            Liste von Dictionaries mit ähnlichen Lesezeichen, sortiert nach Ähnlichkeit.
        """
        # Generiere ein Embedding für die Suchanfrage
        query_embedding = self.embeddings.generate_embedding(query_text)
        if not query_embedding or not self.bookmark_ids:
            return []
        
        query_embedding_np = np.array([query_embedding]).astype('float32')
        
        # Verwende FAISS oder Numpy je nach Verfügbarkeit
        if FAISS_AVAILABLE and self.index is not None:
            # Verwende FAISS für die Suche
            distances, indices = self.index.search(query_embedding_np, min(k, len(self.bookmark_ids)))
            
            search_results = []
            for i in range(len(indices[0])):
                idx = indices[0][i]
                if idx < len(self.bookmark_ids):
                    result_id = self.bookmark_ids[idx]
                    
                    metadata = self.embeddings.get_bookmark_metadata(result_id)
                    if metadata:
                        search_results.append({
                            "id": result_id,
                            "title": metadata.get("title", ""),
                            "url": metadata.get("url", ""),
                            "tags": metadata.get("tags", []),
                            "similarity": 1.0 - float(distances[0][i])  # Konvertiere Distanz in Ähnlichkeit
                        })
            
            return search_results
        else:
            # Verwende Numpy für die Ähnlichkeitsberechnung
            search_results = []
            
            for bid in self.bookmark_ids:
                embedding = self.embeddings.get_embedding(bid)
                if not embedding:
                    continue
                
                # Berechne Kosinus-Ähnlichkeit
                embedding_np = np.array(embedding).astype('float32')
                similarity = self._cosine_similarity(query_embedding_np[0], embedding_np)
                
                metadata = self.embeddings.get_bookmark_metadata(bid)
                if metadata:
                    search_results.append({
                        "id": bid,
                        "title": metadata.get("title", ""),
                        "url": metadata.get("url", ""),
                        "tags": metadata.get("tags", []),
                        "similarity": float(similarity)
                    })
            
            # Sortiere nach Ähnlichkeit (absteigend)
            search_results.sort(key=lambda x: x["similarity"], reverse=True)
            
            # Begrenze auf k Ergebnisse
            return search_results[:k]
    
    def cluster_bookmarks(self, n_clusters: int = 5) -> Dict[int, List[Dict[str, Any]]]:
        """
        Clustert die Lesezeichen in Gruppen.
        
        Args:
            n_clusters: Anzahl der zu erstellenden Cluster.
            
        Returns:
            Dictionary mit Cluster-IDs als Schlüssel und Listen von Lesezeichen als Werte.
        """
        if not FAISS_AVAILABLE:
            logging.error("FAISS wird für Clustering benötigt, ist aber nicht installiert.")
            return {}
            
        if not self.bookmark_ids or not self.index:
            return {}
            
        # Hole alle Embeddings
        embeddings_list = []
        valid_bookmark_ids = []
        
        for bid in self.bookmark_ids:
            embedding = self.embeddings.get_embedding(bid)
            if embedding:
                embeddings_list.append(embedding)
                valid_bookmark_ids.append(bid)
        
        if not embeddings_list:
            return {}
            
        embeddings_array = np.array(embeddings_list).astype('float32')
        
        # Begrenze die Anzahl der Cluster auf die Anzahl der Lesezeichen
        n_clusters = min(n_clusters, len(valid_bookmark_ids))
        
        # Erstelle K-Means-Clusterer
        dimension = embeddings_array.shape[1]
        kmeans = faiss.Kmeans(dimension, n_clusters, niter=100, verbose=False)
        
        # Trainiere K-Means
        kmeans.train(embeddings_array)
        
        # Klassifiziere die Embeddings
        _, cluster_assignments = kmeans.index.search(embeddings_array, 1)
        
        # Erstelle Cluster-Zuordnungen
        clusters = {}
        for i, cluster_id in enumerate(cluster_assignments.flatten()):
            cluster_id = int(cluster_id)
            if cluster_id not in clusters:
                clusters[cluster_id] = []
                
            bookmark_id = valid_bookmark_ids[i]
            metadata = self.embeddings.get_bookmark_metadata(bookmark_id)
            
            if metadata:
                clusters[cluster_id].append({
                    "id": bookmark_id,
                    "title": metadata.get("title", ""),
                    "url": metadata.get("url", ""),
                    "tags": metadata.get("tags", [])
                })
        
        return clusters
    
    def generate_cluster_labels(self, clusters: Dict[int, List[Dict[str, Any]]]) -> Dict[int, str]:
        """
        Generiert sinnvolle Labels für Cluster basierend auf häufigen Begriffen.
        
        Args:
            clusters: Dictionary mit Clustern.
            
        Returns:
            Dictionary mit Cluster-IDs als Schlüssel und Labels als Werte.
        """
        labels = {}
        
        for cluster_id, bookmarks in clusters.items():
            if not bookmarks:
                labels[cluster_id] = f"Cluster {cluster_id}"
                continue
                
            # Sammle alle Wörter aus Titeln und Tags
            all_words = []
            for bookmark in bookmarks:
                # Füge Wörter aus dem Titel hinzu
                title = bookmark.get("title", "").lower()
                title_words = [word for word in title.split() if len(word) > 3]
                all_words.extend(title_words)
                
                # Füge Tags hinzu
                tags = bookmark.get("tags", [])
                all_words.extend([tag.lower() for tag in tags])
            
            # Zähle Häufigkeit der Wörter
            word_counts = {}
            for word in all_words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # Finde die häufigsten Wörter
            if word_counts:
                top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                label = ", ".join([word for word, _ in top_words])
                labels[cluster_id] = label
            else:
                labels[cluster_id] = f"Cluster {cluster_id}"
        
        return labels 