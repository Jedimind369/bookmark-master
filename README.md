# Bookmark Manager

A comprehensive system for parsing, enriching, and analyzing bookmarks using semantic analysis.

## Features

- **Bookmark Parsing**: Extract bookmarks from HTML export files from browsers
- **Content Enrichment**: Scrape and enrich bookmarks with content from the web
- **Semantic Analysis**: Generate embeddings and analyze bookmark relationships
- **Dashboard**: Visualize and explore your bookmarks with a Streamlit dashboard

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bookmark-manager.git
   cd bookmark-manager
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Complete Pipeline

Run the complete pipeline with a single command:

```bash
python scripts/run_pipeline.py path/to/your/bookmarks.html
```

This will:
1. Parse the HTML bookmarks file
2. Enrich the bookmarks with content from the web
3. Generate embeddings for semantic analysis
4. Start the dashboard

### Step-by-Step Usage

If you prefer to run each step separately:

#### 1. Parse HTML Bookmarks

```bash
python -m scripts.processing.process_bookmarks path/to/your/bookmarks.html
```

This will create several JSON files in the `data/processed` directory:
- `bookmarks_structured.json`: Complete bookmark structure
- `bookmarks_urls.json`: All extracted URLs
- `bookmarks_valid_urls.json`: Valid URLs only
- `bookmarks_invalid_urls.json`: Invalid URLs with error information
- `processing_stats.json`: Statistics about the parsing process

#### 2. Enrich Bookmarks with Content

```bash
python -m scripts.scraping.batch_scraper data/processed/bookmarks_valid_urls.json --batch-size 50 --max-workers 5
```

This will create enriched bookmark files in the `data/enriched` directory:
- `enriched_batch_X.json`: Enriched bookmarks for each batch
- `enriched_all.json`: All enriched bookmarks combined
- `enriched_batch_X_stats.json`: Statistics for each batch

#### 3. Generate Embeddings

```bash
python -m scripts.semantic.generate_embeddings data/enriched/enriched_all.json --num-clusters 20
```

This will create embedding files in the `data/embeddings` directory:
- `bookmark_embeddings.pkl`: Serialized embeddings
- `bookmark_clusters.json`: Cluster assignments
- `embedding_stats.json`: Statistics about the embeddings

#### 4. Run the Dashboard

```bash
streamlit run scripts/monitoring/dashboard.py
```

This will start the Streamlit dashboard on http://localhost:8501.

## Dashboard Features

The dashboard includes several tabs:

1. **System Overview**: General system statistics
2. **API Usage**: Monitor API usage and costs
3. **Backup Monitor**: Track backup status
4. **Bookmark Explorer**: Browse and search bookmarks
5. **Semantic Analysis**: Explore semantic relationships between bookmarks
   - Search bookmarks by text
   - Find similar bookmarks
   - Explore bookmark clusters

## Directory Structure

```
bookmark-manager/
├── data/
│   ├── bookmarks/        # Raw bookmark files
│   ├── processed/        # Processed bookmark data
│   ├── enriched/         # Enriched bookmark content
│   └── embeddings/       # Semantic embeddings
├── scripts/
│   ├── processing/       # Bookmark processing scripts
│   ├── scraping/         # Web scraping scripts
│   ├── semantic/         # Semantic analysis scripts
│   ├── monitoring/       # Dashboard and monitoring scripts
│   └── run_pipeline.py   # Main pipeline script
└── logs/                 # Log files
```

## Requirements

- Python 3.8+
- sentence-transformers
- faiss-cpu
- streamlit
- beautifulsoup4
- requests
- pandas
- plotly
- scikit-learn
- tqdm

## License

MIT
