#!/usr/bin/env python3
"""
Bookmark-Ähnlichkeitsmodul.

Dieses Modul implementiert die Ähnlichkeitssuche und das Clustering von Bookmarks
basierend auf ihren Vektor-Embeddings mit Hilfe von FAISS.
"""

import numpy as np
import faiss
from typing import List, Dict, Any, Tuple, Optional
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict

from scripts.semantic.bookmark_embeddings import BookmarkEmbeddings

class BookmarkSimilarity:
    """
    Klasse für die Ähnlichkeitssuche und das Clustering von Bookmarks.
    
    Diese Klasse verwendet FAISS, um effiziente Ähnlichkeitssuchen und
    Clustering-Operationen auf Bookmark-Embeddings durchzuführen.
    """
    
    def __init__(self, embeddings: BookmarkEmbeddings):
        """
        Initialisiere die BookmarkSimilarity-Klasse.
        
        Args:
            embeddings: Eine Instanz der BookmarkEmbeddings-Klasse.
        """
        self.embeddings = embeddings
        self.index = None
        self._build_index()
    
    def _build_index(self) -> None:
        """
        Baue den FAISS-Index für die Ähnlichkeitssuche auf.
        
        Diese Methode wird automatisch aufgerufen, wenn die Klasse initialisiert wird,
        und kann manuell aufgerufen werden, wenn neue Embeddings hinzugefügt wurden.
        """
        if not self.embeddings.is_initialized():
            return
        
        # Hole alle Embeddings und URLs
        urls = self.embeddings.get_urls()
        if not urls:
            return
        
        # Erstelle ein numpy-Array mit allen Embeddings
        embeddings_list = [self.embeddings.get_embedding(url) for url in urls]
        embeddings_array = np.array(embeddings_list).astype('float32')
        
        # Erstelle den FAISS-Index
        dimension = self.embeddings.get_dimension()
        self.index = faiss.IndexFlatIP(dimension)  # Inneres Produkt für Kosinus-Ähnlichkeit
        
        # Normalisiere die Embeddings für Kosinus-Ähnlichkeit
        faiss.normalize_L2(embeddings_array)
        
        # Füge die Embeddings zum Index hinzu
        self.index.add(embeddings_array)
    
    def find_similar_bookmarks(self, query_url: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Finde ähnliche Bookmarks basierend auf einer Abfrage-URL.
        
        Args:
            query_url: Die URL des Bookmarks, für das ähnliche Bookmarks gefunden werden sollen.
            top_k: Die Anzahl der ähnlichsten Bookmarks, die zurückgegeben werden sollen.
        
        Returns:
            Eine Liste von Tupeln mit (URL, Ähnlichkeitswert) für die ähnlichsten Bookmarks.
            Der Ähnlichkeitswert liegt zwischen 0 und 1, wobei 1 die höchste Ähnlichkeit ist.
        
        Raises:
            ValueError: Wenn die Abfrage-URL nicht in den Embeddings gefunden wurde.
        """
        if not self.embeddings.is_initialized() or self.index is None:
            return []
        
        # Hole das Embedding für die Abfrage-URL
        query_embedding = self.embeddings.get_embedding(query_url)
        if query_embedding is None:
            raise ValueError(f"Die URL '{query_url}' wurde nicht in den Embeddings gefunden.")
        
        # Konvertiere das Embedding in ein numpy-Array und normalisiere es
        query_embedding = np.array([query_embedding]).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Führe die Ähnlichkeitssuche durch
        k = min(top_k + 1, self.embeddings.get_count())  # +1, um die Abfrage selbst zu berücksichtigen
        distances, indices = self.index.search(query_embedding, k)
        
        # Hole die URLs für die gefundenen Indizes
        urls = self.embeddings.get_urls()
        results = []
        
        for i, idx in enumerate(indices[0]):
            if idx < len(urls):
                url = urls[idx]
                # Überspringe die Abfrage-URL selbst
                if url != query_url:
                    # Konvertiere die Distanz in einen Ähnlichkeitswert (0-1)
                    similarity = float(distances[0][i])
                    results.append((url, similarity))
        
        return results[:top_k]
    
    def search_by_text(self, query_text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Suche Bookmarks basierend auf einem Textabfrage.
        
        Args:
            query_text: Der Text, nach dem gesucht werden soll.
            top_k: Die Anzahl der relevantesten Bookmarks, die zurückgegeben werden sollen.
        
        Returns:
            Eine Liste von Tupeln mit (URL, Relevanzwert) für die relevantesten Bookmarks.
            Der Relevanzwert liegt zwischen 0 und 1, wobei 1 die höchste Relevanz ist.
        """
        if not self.embeddings.is_initialized() or self.index is None:
            return []
        
        # Generiere ein Embedding für den Abfragetext
        query_embedding = self.embeddings.get_embedding_for_text(query_text)
        
        # Konvertiere das Embedding in ein numpy-Array und normalisiere es
        query_embedding = np.array([query_embedding]).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Führe die Ähnlichkeitssuche durch
        k = min(top_k, self.embeddings.get_count())
        distances, indices = self.index.search(query_embedding, k)
        
        # Hole die URLs für die gefundenen Indizes
        urls = self.embeddings.get_urls()
        results = []
        
        for i, idx in enumerate(indices[0]):
            if idx < len(urls):
                url = urls[idx]
                # Konvertiere die Distanz in einen Ähnlichkeitswert (0-1)
                similarity = float(distances[0][i])
                results.append((url, similarity))
        
        return results
    
    def cluster_bookmarks(self, num_clusters: int = 5) -> Dict[str, List[str]]:
        """
        Clustere Bookmarks basierend auf ihren Embeddings.
        
        Args:
            num_clusters: Die Anzahl der zu erstellenden Cluster.
        
        Returns:
            Ein Dictionary mit Cluster-Labels als Schlüssel und Listen von URLs als Werte.
            Die Cluster-Labels werden automatisch basierend auf den häufigsten Wörtern generiert.
        """
        if not self.embeddings.is_initialized() or self.index is None:
            return {}
        
        # Hole alle Embeddings und URLs
        urls = self.embeddings.get_urls()
        if not urls or len(urls) < num_clusters:
            return {}
        
        # Erstelle ein numpy-Array mit allen Embeddings
        embeddings_list = [self.embeddings.get_embedding(url) for url in urls]
        embeddings_array = np.array(embeddings_list)
        
        # Führe K-Means-Clustering durch
        kmeans = KMeans(n_clusters=num_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings_array)
        
        # Organisiere die URLs nach Clustern
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[int(label)].append(urls[i])
        
        # Generiere aussagekräftige Labels für die Cluster
        labeled_clusters = self._generate_cluster_labels(clusters)
        
        return labeled_clusters
    
    def _generate_cluster_labels(self, clusters: Dict[int, List[str]]) -> Dict[str, List[str]]:
        """
        Generiere aussagekräftige Labels für die Cluster.
        
        Args:
            clusters: Ein Dictionary mit Cluster-IDs als Schlüssel und Listen von URLs als Werte.
        
        Returns:
            Ein Dictionary mit aussagekräftigen Cluster-Labels als Schlüssel und Listen von URLs als Werte.
        """
        labeled_clusters = {}
        
        # Für jeden Cluster
        for cluster_id, urls in clusters.items():
            # Sammle die Texte für alle URLs im Cluster
            texts = []
            for url in urls:
                # Hier könnten wir die Originaltexte verwenden, aber wir haben nur die URLs
                # Daher verwenden wir die URLs selbst als Fallback
                texts.append(url)
            
            # Verwende TF-IDF, um die wichtigsten Wörter im Cluster zu finden
            vectorizer = TfidfVectorizer(max_features=5, stop_words='english')
            try:
                tfidf_matrix = vectorizer.fit_transform(texts)
                feature_names = vectorizer.get_feature_names_out()
                
                # Berechne die durchschnittlichen TF-IDF-Werte für jedes Wort
                tfidf_means = np.array(tfidf_matrix.mean(axis=0)).flatten()
                
                # Finde die Indizes der Top-Wörter
                top_indices = tfidf_means.argsort()[-3:][::-1]
                
                # Erstelle ein Label aus den Top-Wörtern
                label = ", ".join([feature_names[i] for i in top_indices])
            except:
                # Fallback, wenn TF-IDF fehlschlägt
                label = f"Cluster {cluster_id + 1}"
            
            labeled_clusters[label] = urls
        
        return labeled_clusters
    
    def refresh(self) -> None:
        """
        Aktualisiere den FAISS-Index mit den neuesten Embeddings.
        
        Diese Methode sollte aufgerufen werden, wenn neue Embeddings zur
        BookmarkEmbeddings-Instanz hinzugefügt wurden.
        """
        self._build_index() 