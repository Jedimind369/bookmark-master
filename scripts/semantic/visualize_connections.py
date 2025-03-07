#!/usr/bin/env python3

"""
visualize_connections.py

Visualisiert semantische Verbindungen zwischen Lesezeichen mit Plotly.
Erstellt interaktive Netzwerkgraphen und Cluster-Visualisierungen.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

# Pfad zur Hauptanwendung hinzufügen
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    from sklearn.manifold import TSNE
    from sklearn.decomposition import PCA
except ImportError:
    print("Bitte installiere die erforderlichen Pakete:")
    print("pip install numpy pandas plotly scikit-learn")
    sys.exit(1)

from scripts.semantic.vector_store import BookmarkVectorStore

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("visualize_connections")

class BookmarkVisualizer:
    """
    Visualisiert semantische Verbindungen zwischen Lesezeichen als interaktive Graphen.
    """
    
    def __init__(self, vector_store: BookmarkVectorStore):
        """
        Initialisiert den Visualizer.
        
        Args:
            vector_store: Eine Instanz des BookmarkVectorStore
        """
        self.vector_store = vector_store
    
    def create_network_graph(self, 
                            similarity_threshold: float = 0.7, 
                            max_bookmarks: int = 100,
                            title: str = "Semantische Verbindungen zwischen Lesezeichen") -> go.Figure:
        """
        Erstellt einen interaktiven Netzwerkgraphen der semantischen Verbindungen.
        
        Args:
            similarity_threshold: Minimaler Ähnlichkeitswert für Verbindungen
            max_bookmarks: Maximale Anzahl anzuzeigender Lesezeichen
            title: Titel der Visualisierung
            
        Returns:
            Plotly-Figure mit dem Netzwerkgraphen
        """
        # Hole alle Lesezeichen
        bookmarks = self.vector_store.get_all_bookmarks(limit=max_bookmarks)
        
        if not bookmarks:
            logger.warning("Keine Lesezeichen für die Visualisierung gefunden")
            fig = go.Figure()
            fig.add_annotation(text="Keine Daten verfügbar", showarrow=False)
            return fig
        
        # Erstelle Knoten für jedes Lesezeichen
        nodes = []
        for i, bookmark in enumerate(bookmarks):
            nodes.append({
                "id": bookmark["id"],
                "label": bookmark["title"],
                "url": bookmark["url"],
                "category": bookmark.get("category", "Unkategorisiert"),
                "description": bookmark.get("description", "")
            })
        
        # Finde Verbindungen zwischen ähnlichen Lesezeichen
        edges = []
        for i, bookmark in enumerate(bookmarks):
            # Finde ähnliche Lesezeichen
            similar = self.vector_store.find_similar(
                bookmark_id=bookmark["id"],
                score_threshold=similarity_threshold
            )
            
            for similar_bookmark in similar:
                # Füge eine Verbindung hinzu
                edges.append({
                    "source": bookmark["id"],
                    "target": similar_bookmark["id"],
                    "weight": similar_bookmark["similarity_score"]
                })
        
        # Erstelle eine Adjazenzliste
        adjacency = {}
        for edge in edges:
            if edge["source"] not in adjacency:
                adjacency[edge["source"]] = []
            adjacency[edge["source"]].append({
                "target": edge["target"],
                "weight": edge["weight"]
            })
        
        # Erstelle einen Force-Directed Graph mit Plotly
        # Verwende Fruchterman-Reingold-Algorithmus für das Layout
        pos = self._calculate_layout(nodes, edges)
        
        # Gruppiere Knoten nach Kategorien
        categories = set(node["category"] for node in nodes)
        color_map = {category: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                    for i, category in enumerate(categories)}
        
        # Erstelle die Figure
        fig = go.Figure()
        
        # Füge Kanten hinzu
        for edge in edges:
            source_id = edge["source"]
            target_id = edge["target"]
            weight = edge["weight"]
            
            # Finde die Positionen der Knoten
            source_idx = next(i for i, node in enumerate(nodes) if node["id"] == source_id)
            target_idx = next(i for i, node in enumerate(nodes) if node["id"] == target_id)
            
            source_pos = pos[source_idx]
            target_pos = pos[target_idx]
            
            # Dicke der Linie basierend auf dem Gewicht
            width = weight * 3
            
            fig.add_trace(go.Scatter(
                x=[source_pos[0], target_pos[0]],
                y=[source_pos[1], target_pos[1]],
                mode='lines',
                line=dict(width=width, color='rgba(150,150,150,0.4)'),
                hoverinfo='none',
                showlegend=False
            ))
        
        # Füge Knoten nach Kategorien hinzu
        for category in categories:
            category_nodes = [node for node in nodes if node["category"] == category]
            node_ids = [node["id"] for node in category_nodes]
            node_indices = [i for i, node in enumerate(nodes) if node["id"] in node_ids]
            
            x = [pos[i][0] for i in node_indices]
            y = [pos[i][1] for i in node_indices]
            
            # Hover-Text
            text = [f"<b>{node['label']}</b><br>Kategorie: {node['category']}<br>{node['description'][:100]}..."
                   for node in category_nodes]
            
            fig.add_trace(go.Scatter(
                x=x,
                y=y,
                mode='markers',
                marker=dict(
                    size=15,
                    color=color_map[category],
                    line=dict(width=1, color='DarkSlateGrey')
                ),
                text=text,
                hoverinfo='text',
                name=category
            ))
        
        # Layout-Konfiguration
        fig.update_layout(
            title=title,
            showlegend=True,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255, 255, 255, 0.8)"
            ),
            width=1000,
            height=800
        )
        
        return fig
    
    def create_cluster_visualization(self, 
                                   num_clusters: int = 5, 
                                   title: str = "Cluster von ähnlichen Lesezeichen") -> go.Figure:
        """
        Erstellt eine Visualisierung der Bookmark-Cluster mit t-SNE.
        
        Args:
            num_clusters: Anzahl der zu visualisierenden Cluster
            title: Titel der Visualisierung
            
        Returns:
            Plotly-Figure mit der Cluster-Visualisierung
        """
        # Hole Cluster
        clusters = self.vector_store.find_clusters(num_clusters=num_clusters)
        
        if not clusters:
            logger.warning("Keine Cluster für die Visualisierung gefunden")
            fig = go.Figure()
            fig.add_annotation(text="Keine Clusterdaten verfügbar", showarrow=False)
            return fig
        
        # Sammle alle Lesezeichen und ihre Vektoren
        all_bookmarks = []
        all_vectors = []
        all_clusters = []
        
        for cluster_id, bookmarks in clusters.items():
            for bookmark in bookmarks:
                try:
                    # Lade den Vektor für dieses Lesezeichen
                    bookmark_info = self.vector_store.client.retrieve(
                        collection_name=self.vector_store.collection_name,
                        ids=[bookmark["id"]],
                        with_vectors=True
                    )
                    
                    if bookmark_info and len(bookmark_info) > 0 and bookmark_info[0].vector:
                        all_bookmarks.append(bookmark)
                        all_vectors.append(bookmark_info[0].vector)
                        all_clusters.append(int(cluster_id))
                except Exception as e:
                    logger.warning(f"Konnte Vektor für Lesezeichen {bookmark['id']} nicht laden: {str(e)}")
        
        if not all_vectors:
            logger.warning("Keine Vektoren für die Visualisierung gefunden")
            fig = go.Figure()
            fig.add_annotation(text="Keine Vektordaten verfügbar", showarrow=False)
            return fig
        
        # Konvertiere die Vektoren in ein NumPy-Array
        vectors_array = np.array(all_vectors)
        
        # Wenn weniger als 3 Vektoren vorhanden sind, erstelle ein einfaches Scatter-Plot ohne t-SNE
        if len(vectors_array) < 3:
            fig = go.Figure()
            
            # Erzeugt einfache x,y-Koordinaten für die wenigen Punkte
            x_coords = np.linspace(-1, 1, len(vectors_array))
            y_coords = np.zeros(len(vectors_array))
            
            for i, (x, y, bookmark, cluster) in enumerate(zip(x_coords, y_coords, all_bookmarks, all_clusters)):
                fig.add_trace(go.Scatter(
                    x=[x],
                    y=[y],
                    mode='markers',
                    marker=dict(
                        size=15,
                        color=px.colors.qualitative.Plotly[cluster % len(px.colors.qualitative.Plotly)]
                    ),
                    text=f"<b>{bookmark['title']}</b><br>Cluster: {cluster}",
                    hoverinfo='text',
                    name=f"Cluster {cluster}"
                ))
            
            fig.update_layout(
                title="Lesezeichen nach Cluster (zu wenige Datenpunkte für t-SNE)",
                showlegend=True,
                xaxis=dict(title='', showticklabels=False),
                yaxis=dict(title='', showticklabels=False)
            )
            
            return fig
        
        # Berechne die Perplexität basierend auf der Anzahl der Datenpunkte
        # Zwischen 5 und 30, abhängig von der Datenmenge
        perplexity = min(max(5, len(vectors_array) // 5), 30)
        
        # Erstelle eine t-SNE-Projektion der Vektoren
        try:
            tsne = TSNE(n_components=2, perplexity=perplexity, random_state=42)
            tsne_results = tsne.fit_transform(vectors_array)
            
            # Erstelle einen DataFrame für die Visualisierung
            df = pd.DataFrame({
                'x': tsne_results[:, 0],
                'y': tsne_results[:, 1],
                'cluster': all_clusters,
                'title': [b["title"] for b in all_bookmarks],
                'description': [b.get("description", "")[:100] + "..." for b in all_bookmarks],
                'category': [b.get("category", "Unkategorisiert") for b in all_bookmarks],
                'url': [b["url"] for b in all_bookmarks]
            })
            
            # Berechne das Zentrum jedes Clusters
            cluster_centers = df.groupby('cluster')[['x', 'y']].mean().reset_index()
            
            # Erstelle die Plotly-Figure
            fig = px.scatter(
                df, 
                x='x', 
                y='y',
                color='cluster',
                hover_data=['title', 'category', 'description'],
                color_discrete_sequence=px.colors.qualitative.Plotly,
                title=title
            )
            
            # Füge Cluster-Beschriftungen hinzu
            for _, row in cluster_centers.iterrows():
                fig.add_annotation(
                    x=row['x'],
                    y=row['y'],
                    text=f"Cluster {int(row['cluster'])}",
                    showarrow=False,
                    font=dict(size=14, color="black", family="Arial Black"),
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="black",
                    borderwidth=1,
                    borderpad=4
                )
            
            # Verbessere das Layout
            fig.update_layout(
                width=1000,
                height=800,
                legend_title_text='Cluster',
                xaxis=dict(title='', showticklabels=False, showgrid=False, zeroline=False),
                yaxis=dict(title='', showticklabels=False, showgrid=False, zeroline=False),
                plot_bgcolor='rgba(240, 240, 240, 0.8)'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Fehler bei der t-SNE-Berechnung: {str(e)}")
            fig = go.Figure()
            fig.add_annotation(text=f"Fehler bei der Visualisierung: {str(e)}", showarrow=False)
            return fig
    
    def create_category_bar_chart(self, title: str = "Anzahl der Lesezeichen pro Kategorie") -> go.Figure:
        """
        Erstellt ein Balkendiagramm der Lesezeichen pro Kategorie.
        
        Args:
            title: Titel der Visualisierung
            
        Returns:
            Plotly-Figure mit dem Balkendiagramm
        """
        # Hole alle Lesezeichen
        bookmarks = self.vector_store.get_all_bookmarks()
        
        if not bookmarks:
            logger.warning("Keine Lesezeichen für die Visualisierung gefunden")
            fig = go.Figure()
            fig.add_annotation(text="Keine Daten verfügbar", showarrow=False)
            return fig
        
        # Zähle Lesezeichen pro Kategorie
        category_counts = {}
        for bookmark in bookmarks:
            category = bookmark.get("category", "Unkategorisiert")
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Sortiere nach Anzahl
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        categories = [item[0] for item in sorted_categories]
        counts = [item[1] for item in sorted_categories]
        
        # Erstelle das Balkendiagramm
        fig = go.Figure(data=[
            go.Bar(
                x=categories,
                y=counts,
                marker_color=px.colors.qualitative.Plotly[:len(categories)],
                text=counts,
                textposition='auto'
            )
        ])
        
        # Layout-Konfiguration
        fig.update_layout(
            title=title,
            xaxis=dict(title='Kategorie'),
            yaxis=dict(title='Anzahl der Lesezeichen'),
            width=800,
            height=500
        )
        
        return fig
    
    def create_simplified_dashboard(self, output_file: str = "bookmark_dashboard.html"):
        """
        Erstellt ein vereinfachtes Dashboard mit einer Tabelle der Lesezeichen.
        
        Args:
            output_file: Pfad zur Ausgabedatei für das HTML-Dashboard
        """
        # Hole alle Lesezeichen
        all_bookmarks = []
        
        # Verwende direkt die Scroll-Methode, um alle Lesezeichen abzurufen
        try:
            response = self.vector_store.client.scroll(
                collection_name=self.vector_store.collection_name,
                scroll_filter=None,
                limit=100,
                with_payload=True,
                with_vectors=False
            )
            
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
                all_bookmarks.append(bookmark)
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Lesezeichen: {str(e)}")
            # Falls Fehler auftritt, verwende die Beispiellesezeichen
            all_bookmarks = self._get_example_bookmarks()
        
        # Falls keine Lesezeichen gefunden wurden, verwende Beispiellesezeichen
        if not all_bookmarks:
            all_bookmarks = self._get_example_bookmarks()
        
        # Erstelle ein einfaches Balkendiagramm mit Kategorien, falls vorhanden
        category_counts = {}
        for bookmark in all_bookmarks:
            category = bookmark.get("category", "Unkategorisiert")
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Sortiere nach Anzahl
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        categories = [item[0] for item in sorted_categories]
        counts = [item[1] for item in sorted_categories]
        
        # Erstelle das Balkendiagramm
        fig = go.Figure(data=[
            go.Bar(
                x=categories,
                y=counts,
                marker_color=px.colors.qualitative.Plotly[:len(categories)],
                text=counts,
                textposition='auto'
            )
        ])
        
        # Layout-Konfiguration
        fig.update_layout(
            title="Anzahl der Lesezeichen pro Kategorie",
            xaxis=dict(title='Kategorie'),
            yaxis=dict(title='Anzahl der Lesezeichen'),
            width=800,
            height=500
        )
        
        # Erstelle ein HTML-File mit einer einfachen Tabelle und dem Balkendiagramm
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Bookmark-Visualisierung</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                    .dashboard-title { text-align: center; margin-bottom: 30px; color: #333; }
                    .viz-container { background-color: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .viz-title { margin-top: 0; color: #444; border-bottom: 1px solid #eee; padding-bottom: 10px; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
                    th { background-color: #f2f2f2; color: #333; }
                    tr:hover { background-color: #f5f5f5; }
                    .category-tag { display: inline-block; padding: 4px 8px; border-radius: 4px; background-color: #e0e0e0; font-size: 12px; }
                </style>
            </head>
            <body>
                <h1 class="dashboard-title">Bookmark-Master Visualisierung</h1>
                
                <div class="viz-container">
                    <h2 class="viz-title">Lesezeichen pro Kategorie</h2>
                    <div id="category-chart"></div>
                </div>
                
                <div class="viz-container">
                    <h2 class="viz-title">Lesezeichen-Übersicht</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Titel</th>
                                <th>Kategorie</th>
                                <th>URL</th>
                                <th>Beschreibung</th>
                            </tr>
                        </thead>
                        <tbody>
            """)
            
            # Füge Tabellenzeilen für jedes Lesezeichen hinzu
            for bookmark in all_bookmarks:
                category = bookmark.get("category", "Unkategorisiert")
                f.write(f"""
                            <tr>
                                <td>{bookmark.get('id', '')}</td>
                                <td>{bookmark.get('title', '')}</td>
                                <td><span class="category-tag">{category}</span></td>
                                <td><a href="{bookmark.get('url', '')}" target="_blank">{bookmark.get('url', '')}</a></td>
                                <td>{bookmark.get('description', '')[:100]}...</td>
                            </tr>
                """)
            
            f.write("""
                        </tbody>
                    </table>
                </div>
                
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <script>
            """)
            
            # Füge die Plotly-Figur hinzu
            f.write(f"var categoryChart = {fig.to_json()};\n")
            
            f.write("""
                    Plotly.newPlot('category-chart', categoryChart.data, categoryChart.layout);
                </script>
            </body>
            </html>
            """)
        
        logger.info(f"Vereinfachtes Dashboard erstellt und gespeichert unter {output_file}")
    
    def _get_example_bookmarks(self) -> List[Dict[str, Any]]:
        """Gibt eine Liste von Beispiel-Lesezeichen zurück."""
        return [
            {
                "id": 1,
                "title": "Python Documentation",
                "description": "Official documentation for the Python programming language",
                "url": "https://docs.python.org/",
                "category": "Technologie"
            },
            {
                "id": 2,
                "title": "GitHub",
                "description": "Platform for code hosting, collaboration, and version control",
                "url": "https://github.com/",
                "category": "Technologie"
            },
            {
                "id": 3, 
                "title": "Stack Overflow",
                "description": "Community for developers to ask and answer programming questions",
                "url": "https://stackoverflow.com/",
                "category": "Technologie"
            },
            {
                "id": 4,
                "title": "Nature",
                "description": "International journal of science",
                "url": "https://www.nature.com/",
                "category": "Wissenschaft"
            },
            {
                "id": 5,
                "title": "Harvard Business Review",
                "description": "Management magazine published by Harvard Business School",
                "url": "https://hbr.org/",
                "category": "Wirtschaft"
            }
        ]
    
    def _calculate_layout(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
        """
        Berechnet ein Layout für den Graphen mit dem Fruchterman-Reingold-Algorithmus.
        
        Args:
            nodes: Liste der Knoten
            edges: Liste der Kanten
            
        Returns:
            Liste von (x, y)-Koordinaten für jeden Knoten
        """
        try:
            import networkx as nx
            
            # Erstelle einen NetworkX-Graphen
            G = nx.Graph()
            
            # Füge Knoten hinzu
            for node in nodes:
                G.add_node(node["id"], **node)
            
            # Füge Kanten hinzu
            for edge in edges:
                G.add_edge(edge["source"], edge["target"], weight=edge.get("weight", 1.0))
            
            # Berechne das Layout
            pos = nx.spring_layout(G, seed=42, k=0.3)
            
            # Konvertiere in eine Liste von Positionen in der Reihenfolge der Knoten
            positions = []
            for node in nodes:
                positions.append(pos[node["id"]])
            
            return positions
            
        except ImportError:
            logger.warning("NetworkX nicht installiert, verwende einfaches Layout")
            # Fallback: Einfaches kreisförmiges Layout
            n = len(nodes)
            positions = []
            for i in range(n):
                angle = 2 * np.pi * i / n
                positions.append((np.cos(angle), np.sin(angle)))
            return positions

def load_test_data(vector_store: BookmarkVectorStore, data_file: Optional[str] = None):
    """
    Lädt Testdaten in den Vector Store.
    
    Args:
        vector_store: Eine Instanz des BookmarkVectorStore
        data_file: Pfad zu einer JSON-Datei mit Testdaten
    """
    # Wenn eine Datei angegeben wurde, lade die Daten daraus
    if data_file and os.path.exists(data_file):
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                bookmarks = json.load(f)
            
            for i, bookmark in enumerate(bookmarks):
                vector_store.add_bookmark(
                    bookmark_id=bookmark.get("id", i+1),
                    title=bookmark.get("title", f"Lesezeichen {i+1}"),
                    description=bookmark.get("description", ""),
                    url=bookmark.get("url", ""),
                    keywords=bookmark.get("keywords", []),
                    category=bookmark.get("category", "Allgemein"),
                    metadata=bookmark.get("metadata", {})
                )
            
            logger.info(f"{len(bookmarks)} Lesezeichen aus {data_file} geladen")
            return
                
        except Exception as e:
            logger.error(f"Fehler beim Laden von {data_file}: {str(e)}")
    
    # Wenn keine Datei angegeben wurde oder ein Fehler aufgetreten ist, lade Beispieldaten
    # Beispielkategorien
    categories = ["Technologie", "Wissenschaft", "Wirtschaft", "Kultur", "News", "Bildung"]
    
    # Technologie-Lesezeichen
    tech_bookmarks = [
        {
            "title": "Python Documentation",
            "description": "Official documentation for the Python programming language",
            "url": "https://docs.python.org/",
            "keywords": ["python", "programming", "documentation", "development"],
            "category": "Technologie"
        },
        {
            "title": "GitHub",
            "description": "Platform for code hosting, collaboration, and version control",
            "url": "https://github.com/",
            "keywords": ["git", "code", "repository", "version control"],
            "category": "Technologie"
        },
        {
            "title": "Stack Overflow",
            "description": "Community for developers to ask and answer programming questions",
            "url": "https://stackoverflow.com/",
            "keywords": ["programming", "questions", "answers", "community"],
            "category": "Technologie"
        },
        {
            "title": "MDN Web Docs",
            "description": "Resources for developers, by developers",
            "url": "https://developer.mozilla.org/",
            "keywords": ["web", "html", "css", "javascript", "documentation"],
            "category": "Technologie"
        }
    ]
    
    # Wissenschaft-Lesezeichen
    science_bookmarks = [
        {
            "title": "Nature",
            "description": "International journal of science",
            "url": "https://www.nature.com/",
            "keywords": ["science", "research", "journal", "academic"],
            "category": "Wissenschaft"
        },
        {
            "title": "Science Magazine",
            "description": "Leading outlet for scientific news and research",
            "url": "https://www.sciencemag.org/",
            "keywords": ["science", "research", "magazine", "news"],
            "category": "Wissenschaft"
        },
        {
            "title": "arXiv",
            "description": "Repository of electronic preprints for scientific papers",
            "url": "https://arxiv.org/",
            "keywords": ["research", "papers", "preprints", "academic"],
            "category": "Wissenschaft"
        }
    ]
    
    # Wirtschaft-Lesezeichen
    business_bookmarks = [
        {
            "title": "Harvard Business Review",
            "description": "Management magazine published by Harvard Business School",
            "url": "https://hbr.org/",
            "keywords": ["business", "management", "leadership", "strategy"],
            "category": "Wirtschaft"
        },
        {
            "title": "Bloomberg",
            "description": "Business and financial news",
            "url": "https://www.bloomberg.com/",
            "keywords": ["business", "finance", "news", "markets"],
            "category": "Wirtschaft"
        }
    ]
    
    # Kultur-Lesezeichen
    culture_bookmarks = [
        {
            "title": "Goodreads",
            "description": "Book reviews and recommendations",
            "url": "https://www.goodreads.com/",
            "keywords": ["books", "reading", "reviews", "recommendations"],
            "category": "Kultur"
        },
        {
            "title": "IMDb",
            "description": "Online database of information related to films and TV programs",
            "url": "https://www.imdb.com/",
            "keywords": ["movies", "tv", "films", "entertainment"],
            "category": "Kultur"
        }
    ]
    
    # Kombiniere alle Lesezeichen
    all_bookmarks = tech_bookmarks + science_bookmarks + business_bookmarks + culture_bookmarks
    
    # Füge sie zum Vector Store hinzu
    for i, bookmark in enumerate(all_bookmarks):
        vector_store.add_bookmark(
            bookmark_id=i+1,
            title=bookmark["title"],
            description=bookmark["description"],
            url=bookmark["url"],
            keywords=bookmark["keywords"],
            category=bookmark["category"]
        )
    
    logger.info(f"{len(all_bookmarks)} Beispiel-Lesezeichen geladen")

def main():
    """Hauptfunktion für die Kommandozeile."""
    parser = argparse.ArgumentParser(description="Visualisiere semantische Verbindungen zwischen Lesezeichen.")
    parser.add_argument("--data-file", help="Pfad zu einer JSON-Datei mit Lesezeichen")
    parser.add_argument("--output", default="bookmark_dashboard.html", help="Ausgabedatei für das Dashboard")
    parser.add_argument("--in-memory", action="store_true", help="Verwende einen In-Memory-Vector-Store")
    parser.add_argument("--host", default="localhost", help="Hostname des Qdrant-Servers")
    parser.add_argument("--port", type=int, default=6333, help="Port des Qdrant-Servers")
    
    args = parser.parse_args()
    
    # Initialisiere den Vector Store
    vector_store = BookmarkVectorStore(
        in_memory=args.in_memory,
        host=args.host,
        port=args.port
    )
    
    # Lade Testdaten, wenn der Store leer ist
    if not vector_store.get_all_bookmarks():
        load_test_data(vector_store, args.data_file)
    
    # Erstelle den Visualizer
    visualizer = BookmarkVisualizer(vector_store)
    
    # Erstelle das Dashboard
    visualizer.create_simplified_dashboard(args.output)
    
    print(f"Dashboard erstellt: {args.output}")
    print("Öffne die Datei in einem Webbrowser, um die Visualisierungen anzuzeigen.")

if __name__ == "__main__":
    main() 