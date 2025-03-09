#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generiert Embeddings für Webseiten in der SQLite-Datenbank.

Verwendet sentence-transformers, um Embeddings für die Webseiten zu generieren,
und speichert diese in der Datenbank. Führt auch Clustering durch und speichert
die Cluster-IDs in der Datenbank.
"""

import os
import sys
import json
import time
import pickle
import logging
import argparse
import sqlite3
import numpy as np
from pathlib import Path
from tqdm import tqdm
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE

# Füge das Projektverzeichnis zum Pfad hinzu
sys.path.append(str(Path(__file__).parent.parent.parent))

# Importiere die Datenbankklasse
from scripts.database.db_operations import BookmarkDB

# Konfiguriere Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/generate_embeddings_db.log")
    ]
)
logger = logging.getLogger("generate_embeddings_db")

def get_sentence_transformer(model_name="all-MiniLM-L6-v2"):
    """
    Initialisiert das Sentence-Transformer-Modell.
    
    Args:
        model_name: Name des zu verwendenden Modells
        
    Returns:
        SentenceTransformer: Modell oder None im Fehlerfall
    """
    try:
        from sentence_transformers import SentenceTransformer
        
        # Initialisiere das Modell
        model = SentenceTransformer(model_name)
        return model
        
    except ImportError:
        logger.error("Sentence-Transformers-Paket nicht installiert. Bitte installieren Sie es mit 'pip install sentence-transformers'")
        return None
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung des Sentence-Transformer-Modells: {str(e)}")
        return None

def generate_embeddings(db_path, model_name="all-MiniLM-L6-v2", output_dir="data/embeddings/hybrid_run"):
    """
    Generiert Embeddings für alle Webseiten in der Datenbank.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        model_name: Name des zu verwendenden Modells
        output_dir: Verzeichnis für die Ausgabedateien
        
    Returns:
        dict: Dictionary mit URLs als Schlüssel und Embeddings als Werte
    """
    # Initialisiere das Modell
    model = get_sentence_transformer(model_name)
    if not model:
        logger.error("Sentence-Transformer-Modell konnte nicht initialisiert werden")
        return {}
    
    # Stelle sicher, dass das Ausgabeverzeichnis existiert
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialisiere die Datenbankverbindung
    db = BookmarkDB(db_path)
    
    # Hole alle Seiten aus der Datenbank
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Finde Seiten mit Beschreibungen oder Artikeltexten
    cursor.execute("""
        SELECT url, title, description, article_text FROM pages 
        WHERE (description IS NOT NULL AND description != '' AND description != 'null')
        OR (article_text IS NOT NULL AND article_text != '' AND article_text != 'null')
        ORDER BY scrape_time DESC
    """)
    
    pages = cursor.fetchall()
    conn.close()
    
    logger.info(f"{len(pages)} Seiten für die Embedding-Generierung gefunden")
    
    # Generiere Embeddings für alle Seiten
    embeddings = {}
    documents = {}
    
    for url, title, description, article_text in tqdm(pages, desc="Generiere Embeddings"):
        # Erstelle ein Dokument aus Titel, Beschreibung und Text
        document = ""
        
        if title and title.strip() != "":
            document += f"Titel: {title}\n\n"
        
        if description and description.strip() != "":
            document += f"Beschreibung: {description}\n\n"
        
        if article_text and article_text.strip() != "":
            # Begrenze den Artikeltext auf 5000 Zeichen
            max_text_length = 5000
            shortened_text = article_text[:max_text_length] + ("..." if len(article_text) > max_text_length else "")
            document += f"Inhalt: {shortened_text}"
        
        # Wenn kein Dokument erstellt werden konnte, überspringe diese Seite
        if document.strip() == "":
            logger.warning(f"Überspringe {url}: Kein Text für die Embedding-Generierung vorhanden")
            continue
        
        # Speichere das Dokument
        documents[url] = document
        
        # Generiere das Embedding
        embedding = model.encode(document)
        
        # Speichere das Embedding
        embeddings[url] = embedding
        
        # Speichere das Embedding in der Datenbank
        db.save_embedding(url, embedding, model_name)
    
    logger.info(f"{len(embeddings)} Embeddings erfolgreich generiert und in der Datenbank gespeichert")
    
    # Speichere die Embeddings als Pickle-Datei
    embedding_file = os.path.join(output_dir, "bookmark_embeddings.pkl")
    with open(embedding_file, "wb") as f:
        pickle.dump(embeddings, f)
    
    logger.info(f"Embeddings gespeichert in {embedding_file}")
    
    # Speichere die Dokumente als JSON-Datei
    document_file = os.path.join(output_dir, "bookmark_documents.json")
    with open(document_file, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Dokumente gespeichert in {document_file}")
    
    return embeddings

def cluster_embeddings(embeddings, db_path, model_name="all-MiniLM-L6-v2", num_clusters=20, output_dir="data/embeddings/hybrid_run"):
    """
    Führt Clustering auf den Embeddings durch.
    
    Args:
        embeddings: Dictionary mit URLs als Schlüssel und Embeddings als Werte
        db_path: Pfad zur SQLite-Datenbank
        model_name: Name des verwendeten Modells
        num_clusters: Anzahl der Cluster
        output_dir: Verzeichnis für die Ausgabedateien
        
    Returns:
        dict: Dictionary mit URLs als Schlüssel und Cluster-IDs als Werte
    """
    # Stelle sicher, dass genügend Daten für das Clustering vorhanden sind
    if len(embeddings) < num_clusters:
        logger.warning(f"Zu wenige Daten für {num_clusters} Cluster. Reduziere Anzahl der Cluster.")
        num_clusters = max(2, len(embeddings) // 2)
    
    # Konvertiere die Embeddings in ein NumPy-Array
    urls = list(embeddings.keys())
    X = np.array([embeddings[url] for url in urls])
    
    # Führe K-Means-Clustering durch
    logger.info(f"Führe K-Means-Clustering mit {num_clusters} Clustern durch")
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    clusters = kmeans.fit_predict(X)
    
    # Erstelle ein Dictionary mit URLs als Schlüssel und Cluster-IDs als Werte
    url_to_cluster = {url: int(cluster) for url, cluster in zip(urls, clusters)}
    
    # Speichere die Cluster-Zuordnungen in der Datenbank
    db = BookmarkDB(db_path)
    
    for url, cluster_id in tqdm(url_to_cluster.items(), desc="Speichere Cluster-Zuordnungen"):
        db.save_cluster(url, cluster_id, model_name)
    
    logger.info(f"{len(url_to_cluster)} Cluster-Zuordnungen erfolgreich in der Datenbank gespeichert")
    
    # Speichere die Cluster-Zuordnungen als JSON-Datei
    cluster_file = os.path.join(output_dir, "bookmark_clusters.json")
    with open(cluster_file, "w", encoding="utf-8") as f:
        json.dump(url_to_cluster, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Cluster-Zuordnungen gespeichert in {cluster_file}")
    
    # Generiere eine t-SNE-Visualisierung für die Embeddings
    logger.info("Generiere t-SNE-Visualisierung")
    
    # Berechne die Perplexity basierend auf der Anzahl der Datenpunkte
    # Perplexity muss kleiner sein als die Anzahl der Samples
    perplexity = min(30, len(urls) - 1)
    if len(urls) <= 3:
        logger.warning(f"Zu wenige Daten für t-SNE-Visualisierung. Mindestens 4 Datenpunkte erforderlich.")
        tsne_data = []
        for i, url in enumerate(urls):
            tsne_data.append({
                "url": url,
                "x": float(i),  # Einfache lineare Anordnung
                "y": 0.0,
                "cluster": int(clusters[i])
            })
    else:
        tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity)
        X_tsne = tsne.fit_transform(X)
        
        # Speichere die t-SNE-Koordinaten zusammen mit den Cluster-IDs und URLs
        tsne_data = []
        for i, url in enumerate(urls):
            tsne_data.append({
                "url": url,
                "x": float(X_tsne[i, 0]),
                "y": float(X_tsne[i, 1]),
                "cluster": int(clusters[i])
            })
    
    # Speichere die t-SNE-Daten als JSON-Datei
    tsne_file = os.path.join(output_dir, "bookmark_tsne.json")
    with open(tsne_file, "w", encoding="utf-8") as f:
        json.dump(tsne_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"t-SNE-Daten gespeichert in {tsne_file}")
    
    return url_to_cluster

def analyze_clusters(db_path, model_name="all-MiniLM-L6-v2", output_dir="data/embeddings/hybrid_run"):
    """
    Analysiert die Cluster und generiert Statistiken.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        model_name: Name des verwendeten Modells
        output_dir: Verzeichnis für die Ausgabedateien
    """
    # Initialisiere die Datenbankverbindung
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Hole alle Cluster-Zuordnungen aus der Datenbank
    cursor.execute("""
        SELECT c.cluster_id, COUNT(*) as count, 
               GROUP_CONCAT(p.title, ' | ') as titles
        FROM clusters c
        JOIN pages p ON c.url = p.url
        WHERE c.model = ?
        GROUP BY c.cluster_id
        ORDER BY count DESC
    """, (model_name,))
    
    cluster_stats = cursor.fetchall()
    conn.close()
    
    # Generiere Statistiken für jeden Cluster
    cluster_info = []
    for cluster_id, count, titles in cluster_stats:
        # Begrenze die Anzahl der Titel auf 5
        title_list = titles.split(" | ")[:5]
        
        cluster_info.append({
            "cluster_id": cluster_id,
            "count": count,
            "sample_titles": title_list
        })
    
    # Speichere die Cluster-Statistiken als JSON-Datei
    stats_file = os.path.join(output_dir, "bookmark_cluster_stats.json")
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(cluster_info, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Cluster-Statistiken gespeichert in {stats_file}")
    
    # Logge die Cluster-Statistiken
    logger.info(f"Cluster-Statistiken:")
    for cluster in cluster_info:
        logger.info(f"Cluster {cluster['cluster_id']}: {cluster['count']} Seiten")
        logger.info(f"  Beispiel-Titel: {', '.join(cluster['sample_titles'][:3])}")

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Generiert Embeddings für Webseiten in der SQLite-Datenbank")
    parser.add_argument("--db-path", default="data/database/bookmarks.db", help="Pfad zur SQLite-Datenbank")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="Name des zu verwendenden Embedding-Modells")
    parser.add_argument("--output-dir", default="data/embeddings/hybrid_run", help="Verzeichnis für die Ausgabedateien")
    parser.add_argument("--num-clusters", type=int, default=20, help="Anzahl der Cluster")
    args = parser.parse_args()
    
    # Stelle sicher, dass das Ausgabeverzeichnis existiert
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generiere Embeddings
    embeddings = generate_embeddings(args.db_path, args.model, args.output_dir)
    
    # Führe Clustering durch
    if embeddings:
        url_to_cluster = cluster_embeddings(embeddings, args.db_path, args.model, args.num_clusters, args.output_dir)
        
        # Analysiere die Cluster
        analyze_clusters(args.db_path, args.model, args.output_dir)
    
    logger.info("Embedding-Generierung und Clustering abgeschlossen")

if __name__ == "__main__":
    main() 