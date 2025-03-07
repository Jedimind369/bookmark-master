# Semantischer Teil des Bookmark-Master Projekts

Dieser Teil des Projekts implementiert semantische Verbindungen zwischen Lesezeichen mithilfe von Vektor-Embeddings und Ähnlichkeitssuche. Durch die Verwendung von Qdrant als Vector Store und SentenceTransformers für die Generierung von Embeddings können ähnliche Lesezeichen gefunden und visualisiert werden.

## Komponenten

### 1. Vector Store (`vector_store.py`)

Die Klasse `BookmarkVectorStore` verwaltet semantische Verbindungen zwischen Lesezeichen:

- **Funktionalitäten**:
  - Speichern von Lesezeichen mit Vektor-Embeddings
  - Ähnlichkeitssuche zwischen Lesezeichen
  - Clustering von ähnlichen Lesezeichen
  - Kategorisierung und effiziente Filterung

- **Technologien**:
  - **Qdrant**: Vektor-Datenbank für das Speichern und Suchen von ähnlichen Vektoren
  - **SentenceTransformers**: Erstellen semantischer Embeddings aus Text

### 2. Visualisierung (`visualize_connections.py`)

Die Klasse `BookmarkVisualizer` visualisiert die semantischen Verbindungen:

- **Funktionalitäten**:
  - Netzwerkgraphen mit semantischen Verbindungen
  - Cluster-Visualisierung mit t-SNE
  - Kategorienbasierte Statistiken
  - Interaktives Dashboard

- **Technologien**:
  - **Plotly**: Interaktive Visualisierungen
  - **t-SNE**: Dimensionsreduktion für die Visualisierung hochdimensionaler Vektoren
  - **NetworkX**: Graphalgorithmen für das Layout

## Verwendung

### Vector Store einrichten

```python
from scripts.semantic.vector_store import BookmarkVectorStore

# In-Memory-Speicher für Tests
vector_store = BookmarkVectorStore(in_memory=True)

# Oder mit einem laufenden Qdrant-Server
vector_store = BookmarkVectorStore(
    host="localhost", 
    port=6333,
    collection_name="bookmarks"
)

# Lesezeichen hinzufügen
vector_store.add_bookmark(
    bookmark_id=1,
    title="Python Programming",
    description="A guide to Python programming language",
    url="https://python.org",
    keywords=["python", "programming", "guide"],
    category="Technology"
)

# Ähnliche Lesezeichen finden
similar = vector_store.find_similar(
    query="JavaScript tutorials",  # Entweder mit Textabfrage
    score_threshold=0.7
)

# Oder basierend auf einem vorhandenen Lesezeichen
similar = vector_store.find_similar(
    bookmark_id=1,  # Oder mit einer Bookmark-ID
    limit=5,
    category="Technology"  # Optionaler Kategoriefilter
)
```

### Visualisierungen erstellen

```python
from scripts.semantic.visualize_connections import BookmarkVisualizer

# Initialisiere den Visualizer
visualizer = BookmarkVisualizer(vector_store)

# Netzwerkgraph erstellen
network_fig = visualizer.create_network_graph(
    similarity_threshold=0.7,
    max_bookmarks=100
)

# Cluster-Visualisierung erstellen
cluster_fig = visualizer.create_cluster_visualization(num_clusters=5)

# Kategorie-Balkendiagramm erstellen
category_fig = visualizer.create_category_bar_chart()

# Vollständiges Dashboard erstellen
visualizer.create_dashboard(output_file="bookmark_dashboard.html")
```

## Kommandozeilennutzung

Der `visualize_connections.py` kann auch direkt von der Kommandozeile aus verwendet werden:

```bash
# Testdaten laden und Dashboard erstellen (In-Memory-Modus)
python -m scripts.semantic.visualize_connections --in-memory

# Mit bestehender Qdrant-Instanz und eigenen Daten
python -m scripts.semantic.visualize_connections --host localhost --port 6333 --data-file my_bookmarks.json
```

## Abhängigkeiten

Die folgenden Pakete werden benötigt:
```bash
pip install qdrant-client sentence-transformers numpy pandas plotly scikit-learn networkx
```

## Integration in das Bookmark-Master-Dashboard

Die semantische Komponente kann in das Hauptdashboard des Bookmark-Master-Projekts integriert werden. Die Visualisierungen können als iframes oder als eigenständige Seiten eingebunden werden.

## Weiterentwicklungsmöglichkeiten

1. **Echtzeit-Updates**: Automatische Aktualisierung der Embeddings bei Änderungen
2. **Custom Embeddings**: Unterstützung für branchenspezifische oder domänenspezifische Modelle
3. **Interaktive Empfehlungen**: Empfehlungssystem basierend auf Nutzerinteraktion
4. **Erweiterte Metriken**: Implementierung von PageRank oder anderen Graphalgorithmen 