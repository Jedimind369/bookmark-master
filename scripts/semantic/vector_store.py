#!/usr/bin/env python3

"""
vector_store.py

Implementiert einen Vector Store für semantische Verbindungen zwischen Lesezeichen.
Verwendet Qdrant und SentenceTransformers für effizientes Similarity Matching.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

# Pfad zur Hauptanwendung hinzufügen
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Bitte installiere die erforderlichen Pakete:")
    print("pip install qdrant-client sentence-transformers")
    sys.exit(1)

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vector_store")

class BookmarkVectorStore:
    """
    Verwaltet semantische Verbindungen zwischen Lesezeichen mit Hilfe von Qdrant.
    Ermöglicht effizientes Ähnlichkeitsmatching und Clusteranalyse.
    """
    
    def __init__(self, 
                collection_name: str = "bookmarks",
                host: str = "localhost", 
                port: int = 6333,
                model_name: str = "all-MiniLM-L6-v2",
                vector_size: int = 384,
                in_memory: bool = False):
        """
        Initialisiert den Vector Store für Lesezeichen.
        
        Args:
            collection_name: Name der Qdrant-Kollektion
            host: Hostname des Qdrant-Servers
            port: Port des Qdrant-Servers
            model_name: Name des zu verwendenden SentenceTransformer-Modells
            vector_size: Größe der generierten Embedding-Vektoren
            in_memory: Ob ein In-Memory-Qdrant-Client verwendet werden soll
        """
        self.collection_name = collection_name
        self.vector_size = vector_size
        
        # Initialisiere Qdrant-Client
        if in_memory:
            self.client = QdrantClient(":memory:")
            logger.info("In-Memory Qdrant-Client initialisiert")
        else:
            self.client = QdrantClient(host=host, port=port)
            logger.info(f"Qdrant-Client für {host}:{port} initialisiert")
        
        # Initialisiere Embedding-Modell
        self.model = SentenceTransformer(model_name)
        logger.info(f"Embedding-Modell {model_name} geladen")
        
        # Stelle sicher, dass die Kollektion existiert
        self._ensure_collection_exists()
        
        # Cache für bereits generierte Embeddings
        self.embedding_cache = {}
    
    def _ensure_collection_exists(self):
        """Stellt sicher, dass die Qdrant-Kollektion existiert und richtig konfiguriert ist."""
        # Prüfe, ob die Kollektion bereits existiert
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            # Erstelle die Kollektion, wenn sie nicht existiert
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"Kollektion '{self.collection_name}' erstellt")
            
            # Erstelle einen Index für das effiziente Filtern
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="category",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logger.info("Index für 'category' erstellt")
        else:
            logger.info(f"Kollektion '{self.collection_name}' existiert bereits")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generiert ein Embedding für den gegebenen Text.
        
        Args:
            text: Der zu embedding Text
            
        Returns:
            Embedding-Vektor
        """
        # Cache-Check
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        # Generiere das Embedding
        embedding = self.model.encode(text).tolist()
        
        # Speichere im Cache
        self.embedding_cache[text] = embedding
        
        return embedding
    
    def add_bookmark(self, 
                    bookmark_id: Union[int, str], 
                    title: str, 
                    description: str,
                    url: str,
                    keywords: List[str] = None,
                    category: str = None,
                    metadata: Dict[str, Any] = None) -> bool:
        """
        Fügt ein Lesezeichen zum Vector Store hinzu.
        
        Args:
            bookmark_id: Eindeutige ID des Lesezeichens
            title: Titel des Lesezeichens
            description: Beschreibung oder Zusammenfassung des Inhalts
            url: URL des Lesezeichens
            keywords: Liste von Schlüsselwörtern
            category: Kategorie des Lesezeichens
            metadata: Zusätzliche Metadaten
            
        Returns:
            True, wenn das Hinzufügen erfolgreich war
        """
        try:
            # Erstelle den Embedding-Text
            embedding_text = f"{title}. {description}"
            if keywords:
                embedding_text += f" Keywords: {', '.join(keywords)}"
            
            # Generiere das Embedding
            embedding = self._generate_embedding(embedding_text)
            
            # Erstelle die Payload für Qdrant
            payload = {
                "title": title,
                "description": description,
                "url": url,
                "embedding_text": embedding_text
            }
            
            if keywords:
                payload["keywords"] = keywords
            
            if category:
                payload["category"] = category
            
            if metadata:
                payload.update(metadata)
            
            # Füge das Lesezeichen zu Qdrant hinzu
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=bookmark_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            logger.info(f"Lesezeichen hinzugefügt: {title} (ID: {bookmark_id})")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Lesezeichens: {str(e)}")
            return False
    
    def find_similar(self, 
                    query: str = None, 
                    bookmark_id: Union[int, str] = None,
                    limit: int = 10,
                    score_threshold: float = 0.7,
                    category: str = None) -> List[Dict[str, Any]]:
        """
        Findet ähnliche Lesezeichen basierend auf einer Abfrage oder einem vorhandenen Lesezeichen.
        
        Args:
            query: Textabfrage für die Ähnlichkeitssuche
            bookmark_id: ID eines vorhandenen Lesezeichens für die Ähnlichkeitssuche
            limit: Maximale Anzahl zurückzugebender Ergebnisse
            score_threshold: Minimaler Ähnlichkeitswert (0-1)
            category: Optional: Filtere nach Kategorie
            
        Returns:
            Liste ähnlicher Lesezeichen mit Ähnlichkeitswerten
        """
        try:
            # Prüfe, ob entweder query oder bookmark_id angegeben wurde
            if not query and not bookmark_id:
                raise ValueError("Entweder 'query' oder 'bookmark_id' muss angegeben werden")
            
            # Wenn bookmark_id angegeben ist, hole den Vektor aus der Datenbank
            if bookmark_id:
                try:
                    response = self.client.retrieve(
                        collection_name=self.collection_name,
                        ids=[bookmark_id]
                    )
                    
                    if not response or len(response) == 0 or not response[0].vector:
                        raise ValueError(f"Lesezeichen mit ID {bookmark_id} nicht gefunden oder kein Vektor vorhanden")
                    
                    query_vector = response[0].vector
                except Exception as e:
                    raise ValueError(f"Lesezeichen mit ID {bookmark_id} nicht gefunden oder kein Vektor vorhanden: {str(e)}")
            else:
                # Generiere Embedding für die Textabfrage
                query_vector = self._generate_embedding(query)
            
            # Erstelle den Filter, wenn eine Kategorie angegeben ist
            search_filter = None
            if category:
                search_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="category",
                            match=models.MatchValue(value=category)
                        )
                    ]
                )
            
            # Führe die Suche durch
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                filter=search_filter
            )
            
            # Formatiere die Ergebnisse
            formatted_results = []
            for res in results:
                if bookmark_id and str(res.id) == str(bookmark_id):
                    # Überspringe das Original-Lesezeichen
                    continue
                
                formatted_result = {
                    "id": res.id,
                    "similarity_score": res.score,
                    **res.payload
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Fehler bei der Ähnlichkeitssuche: {str(e)}")
            return []
    
    def get_categories(self) -> List[str]:
        """
        Gibt alle vorhandenen Kategorien im Vector Store zurück.
        
        Returns:
            Liste aller Kategorien
        """
        try:
            # Führe eine Aggregationsabfrage durch
            response = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=None,
                limit=10000,  # Hoher Wert, um alle Dokumente zu erhalten
                with_payload=True,
                with_vectors=False
            )
            
            # Prüfe, ob die Antwort ein Tupel oder direkt die Punkte ist
            if isinstance(response, tuple):
                points = response[0]  # Bei neueren Versionen ist das erste Element die Liste der Punkte
            else:
                points = response  # Bei älteren Versionen sind es direkt die Punkte
            
            # Extrahiere die Kategorien
            categories = set()
            for point in points:
                if "category" in point.payload:
                    categories.add(point.payload["category"])
            
            return sorted(list(categories))
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Kategorien: {str(e)}")
            return []
    
    def delete_bookmark(self, bookmark_id: Union[int, str]) -> bool:
        """
        Löscht ein Lesezeichen aus dem Vector Store.
        
        Args:
            bookmark_id: ID des zu löschenden Lesezeichens
            
        Returns:
            True, wenn das Löschen erfolgreich war
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[bookmark_id]
                )
            )
            logger.info(f"Lesezeichen mit ID {bookmark_id} gelöscht")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Lesezeichens: {str(e)}")
            return False
    
    def update_bookmark(self, 
                       bookmark_id: Union[int, str],
                       title: Optional[str] = None, 
                       description: Optional[str] = None,
                       url: Optional[str] = None,
                       keywords: Optional[List[str]] = None,
                       category: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Aktualisiert ein vorhandenes Lesezeichen im Vector Store.
        
        Args:
            bookmark_id: ID des zu aktualisierenden Lesezeichens
            title: Neuer Titel (optional)
            description: Neue Beschreibung (optional)
            url: Neue URL (optional)
            keywords: Neue Schlüsselwörter (optional)
            category: Neue Kategorie (optional)
            metadata: Neue Metadaten (optional)
            
        Returns:
            True, wenn die Aktualisierung erfolgreich war
        """
        try:
            # Hole das aktuelle Lesezeichen
            response = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[bookmark_id],
                with_payload=True,
                with_vectors=False
            )
            
            if not response:
                logger.error(f"Lesezeichen mit ID {bookmark_id} nicht gefunden")
                return False
            
            current_payload = response[0].payload
            
            # Aktualisiere die Felder
            updated_payload = dict(current_payload)
            
            if title:
                updated_payload["title"] = title
            
            if description:
                updated_payload["description"] = description
            
            if url:
                updated_payload["url"] = url
            
            if keywords is not None:
                updated_payload["keywords"] = keywords
            
            if category:
                updated_payload["category"] = category
            
            if metadata:
                # Merge neue Metadaten mit vorhandenen
                current_metadata = updated_payload.get("metadata", {})
                current_metadata.update(metadata)
                updated_payload["metadata"] = current_metadata
            
            # Wenn Titel oder Beschreibung geändert wurden, aktualisiere das Embedding
            if title or description:
                embedding_text = f"{updated_payload.get('title')}. {updated_payload.get('description')}"
                if updated_payload.get("keywords"):
                    embedding_text += f" Keywords: {', '.join(updated_payload['keywords'])}"
                
                updated_payload["embedding_text"] = embedding_text
                embedding = self._generate_embedding(embedding_text)
                
                # Aktualisiere den Punkt mit neuem Vektor und Payload
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        models.PointStruct(
                            id=bookmark_id,
                            vector=embedding,
                            payload=updated_payload
                        )
                    ]
                )
            else:
                # Aktualisiere nur die Payload
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload=updated_payload,
                    points=[bookmark_id]
                )
            
            logger.info(f"Lesezeichen mit ID {bookmark_id} aktualisiert")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Lesezeichens: {str(e)}")
            return False
    
    def clear_collection(self) -> bool:
        """
        Löscht alle Lesezeichen aus der Kollektion.
        
        Returns:
            True, wenn das Löschen erfolgreich war
        """
        try:
            # Lösche die Kollektion
            self.client.delete_collection(collection_name=self.collection_name)
            logger.info(f"Kollektion '{self.collection_name}' gelöscht")
            
            # Erstelle sie neu
            self._ensure_collection_exists()
            
            # Leere den Cache
            self.embedding_cache = {}
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Kollektion: {str(e)}")
            return False
    
    def get_all_bookmarks(self, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Gibt alle Lesezeichen im Vector Store zurück.
        
        Args:
            limit: Maximale Anzahl zurückzugebender Ergebnisse
            offset: Startpunkt für die Paginierung
            
        Returns:
            Liste aller Lesezeichen
        """
        try:
            # In neueren Qdrant-Versionen gibt scroll() ein Tupel zurück, bei älteren Versionen nur die Punkte
            response = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=None,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            bookmarks = []
            
            # Prüfe, ob die Antwort ein Tupel oder direkt die Punkte ist
            if isinstance(response, tuple):
                points = response[0]  # Bei neueren Versionen ist das erste Element die Liste der Punkte
            else:
                points = response  # Bei älteren Versionen sind es direkt die Punkte
            
            for point in points:
                bookmark = {
                    "id": point.id,
                    **point.payload
                }
                bookmarks.append(bookmark)
            
            return bookmarks
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen aller Lesezeichen: {str(e)}")
            return []
    
    def find_clusters(self, num_clusters: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Findet Cluster von ähnlichen Lesezeichen mit K-Means.
        
        Args:
            num_clusters: Anzahl der zu findenden Cluster
            
        Returns:
            Dictionary mit Cluster-IDs als Schlüssel und Listen von Lesezeichen als Werte
        """
        try:
            from sklearn.cluster import KMeans
            import numpy as np
            
            # Hole alle Lesezeichen mit Vektoren
            response = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=None,
                limit=10000,
                with_payload=True,
                with_vectors=True
            )
            
            # Prüfe, ob die Antwort ein Tupel oder direkt die Punkte ist
            if isinstance(response, tuple):
                points = response[0]  # Bei neueren Versionen ist das erste Element die Liste der Punkte
            else:
                points = response  # Bei älteren Versionen sind es direkt die Punkte
            
            bookmarks = []
            vectors = []
            for point in points:
                if point.vector:
                    bookmark = {
                        "id": point.id,
                        **point.payload
                    }
                    bookmarks.append(bookmark)
                    vectors.append(point.vector)
            
            if not vectors:
                logger.warning("Keine Vektoren für Clustering gefunden")
                return {}
            
            # Führe K-Means-Clustering durch
            vectors_array = np.array(vectors)
            
            # Stelle sicher, dass wir mindestens 2 Cluster haben (oder die Anzahl der Vektoren)
            actual_clusters = min(num_clusters, len(vectors_array))
            if actual_clusters < 2:
                logger.warning(f"Nicht genug Datenpunkte für Clustering ({len(vectors_array)})")
                return {"0": bookmarks}  # Alles in einem Cluster
                
            kmeans = KMeans(n_clusters=actual_clusters, random_state=42)
            clusters = kmeans.fit_predict(vectors_array)
            
            # Gruppiere Lesezeichen nach Clustern
            result = {}
            for i, (bookmark, cluster_id) in enumerate(zip(bookmarks, clusters)):
                if cluster_id not in result:
                    result[str(cluster_id)] = []
                result[str(cluster_id)].append(bookmark)
            
            return result
            
        except ImportError:
            logger.error("Scikit-learn ist erforderlich für Clustering")
            return {}
        except Exception as e:
            logger.error(f"Fehler beim Clustering: {str(e)}")
            return {}

# Testfunktion
def test_vector_store():
    """Testet die grundlegende Funktionalität des Vector Stores."""
    store = BookmarkVectorStore(in_memory=True)
    
    # Füge einige Testlesezeichen hinzu
    store.add_bookmark(
        bookmark_id=1,
        title="Python Programming",
        description="A guide to Python programming language",
        url="https://python.org",
        keywords=["python", "programming", "guide"],
        category="Technology"
    )
    
    store.add_bookmark(
        bookmark_id=2,
        title="JavaScript Basics",
        description="Learn JavaScript from scratch",
        url="https://javascript.info",
        keywords=["javascript", "web", "programming"],
        category="Technology"
    )
    
    store.add_bookmark(
        bookmark_id=3,
        title="Cooking Recipes",
        description="Collection of delicious recipes",
        url="https://recipes.com",
        keywords=["cooking", "food", "recipes"],
        category="Food"
    )
    
    # Suche nach ähnlichen Lesezeichen
    python_similar = store.find_similar(query="Python programming tutorials")
    print(f"Ähnlich zu 'Python programming tutorials': {len(python_similar)} Ergebnisse")
    for bookmark in python_similar:
        print(f"  - {bookmark['title']} (Score: {bookmark['similarity_score']:.4f})")
    
    # Suche nach ähnlichen Lesezeichen basierend auf einem vorhandenen Lesezeichen
    js_similar = store.find_similar(bookmark_id=2)
    print(f"Ähnlich zu 'JavaScript Basics': {len(js_similar)} Ergebnisse")
    for bookmark in js_similar:
        print(f"  - {bookmark['title']} (Score: {bookmark['similarity_score']:.4f})")
    
    # Kategorien abrufen
    categories = store.get_categories()
    print(f"Kategorien: {categories}")
    
    # Lesezeichen aktualisieren
    store.update_bookmark(
        bookmark_id=1,
        description="An updated guide to Python programming language",
        keywords=["python", "programming", "guide", "updated"]
    )
    
    # Alle Lesezeichen abrufen
    all_bookmarks = store.get_all_bookmarks()
    print(f"Alle Lesezeichen: {len(all_bookmarks)}")
    for bookmark in all_bookmarks:
        print(f"  - {bookmark['title']} ({bookmark.get('category', 'Keine Kategorie')})")

if __name__ == "__main__":
    test_vector_store() 