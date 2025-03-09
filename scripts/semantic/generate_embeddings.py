import os
import json
import sys
import argparse
from tqdm import tqdm
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.semantic.bookmark_embeddings import BookmarkEmbeddings
from scripts.semantic.bookmark_similarity import BookmarkSimilarity

def prepare_text_for_embedding(bookmark: Dict[str, Any]) -> str:
    """
    Prepare text for embedding by combining relevant fields.
    
    Args:
        bookmark (dict): Bookmark data
        
    Returns:
        str: Combined text for embedding
    """
    # Collect all text fields that might be useful for embedding
    text_parts = []
    
    # Add title with higher weight (repeat it)
    if 'title' in bookmark and bookmark['title']:
        text_parts.append(bookmark['title'])
        text_parts.append(bookmark['title'])  # Repeat for higher weight
    
    # Add folder information for context
    if 'folder' in bookmark and bookmark['folder']:
        text_parts.append(f"Folder: {bookmark['folder']}")
    
    # Add folder path if available
    if 'folder_path' in bookmark and bookmark['folder_path']:
        text_parts.append(f"Path: {bookmark['folder_path']}")
    
    # Add tags if available
    if 'tags' in bookmark and bookmark['tags']:
        if isinstance(bookmark['tags'], list):
            text_parts.append("Tags: " + ", ".join(bookmark['tags']))
        elif isinstance(bookmark['tags'], str):
            text_parts.append("Tags: " + bookmark['tags'])
    
    # Combine all parts
    combined_text = " ".join(text_parts)
    
    # If we have no text, use the URL as a fallback
    if not combined_text.strip() and 'url' in bookmark:
        return f"URL: {bookmark['url']}"
    
    return combined_text

def generate_embeddings(bookmarks: List[Dict[str, Any]], 
                        model_name: str = 'all-MiniLM-L6-v2',
                        output_file: str = 'data/embeddings/bookmark_embeddings.pkl') -> BookmarkEmbeddings:
    """
    Generate embeddings for a list of bookmarks.
    
    Args:
        bookmarks (list): List of bookmark dictionaries
        model_name (str): Name of the sentence-transformers model to use
        output_file (str): Path to save the embeddings
        
    Returns:
        BookmarkEmbeddings: Embeddings model
    """
    print(f"Initializing embedding model: {model_name}")
    embedding_model = BookmarkEmbeddings(model_name=model_name)
    
    # Prepare data for embedding
    print("Preparing text for embeddings...")
    texts = []
    urls = []
    skipped = 0
    
    for bookmark in tqdm(bookmarks, desc="Processing bookmarks"):
        # Skip bookmarks with missing URLs
        if 'url' not in bookmark or not bookmark['url']:
            skipped += 1
            continue
        
        # Prepare text for embedding
        text = prepare_text_for_embedding(bookmark)
        
        texts.append(text)
        urls.append(bookmark['url'])
    
    print(f"Prepared {len(texts)} bookmarks for embedding (skipped {skipped})")
    
    # Generate embeddings
    print("Generating embeddings...")
    embedding_model.add_bookmarks(texts, urls)
    
    # Save embeddings
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    embedding_model.save(output_file)
    
    print(f"Generated and saved embeddings for {embedding_model.get_count()} bookmarks")
    print(f"Embedding dimension: {embedding_model.get_dimension()}")
    
    return embedding_model

def analyze_embeddings(embedding_model: BookmarkEmbeddings, 
                       output_dir: str = 'data/embeddings',
                       num_clusters: int = 20) -> Dict[str, Any]:
    """
    Analyze embeddings using the BookmarkSimilarity class.
    
    Args:
        embedding_model (BookmarkEmbeddings): Embeddings model
        output_dir (str): Directory to save analysis results
        num_clusters (int): Number of clusters to generate
        
    Returns:
        dict: Analysis results
    """
    print("Initializing similarity model...")
    similarity_model = BookmarkSimilarity(embedding_model)
    
    # Generate clusters
    print(f"Generating {num_clusters} clusters...")
    clusters = similarity_model.cluster_bookmarks(num_clusters=num_clusters)
    
    # Compile statistics
    stats = {
        'num_bookmarks': embedding_model.get_count(),
        'embedding_dimension': embedding_model.get_dimension(),
        'num_clusters': len(clusters),
        'clusters': {}
    }
    
    # Add cluster statistics
    for label, urls in clusters.items():
        stats['clusters'][label] = {
            'size': len(urls),
            'sample_urls': urls[:5]  # Include a few sample URLs
        }
    
    # Save analysis results
    os.makedirs(output_dir, exist_ok=True)
    
    # Save clusters
    clusters_file = os.path.join(output_dir, 'bookmark_clusters.json')
    with open(clusters_file, 'w', encoding='utf-8') as f:
        json.dump(clusters, f, ensure_ascii=False, indent=2)
    
    # Save statistics
    stats_file = os.path.join(output_dir, 'embedding_stats.json')
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"Analysis complete. Results saved to {output_dir}")
    print(f"Generated {len(clusters)} clusters")
    
    # Print cluster sizes
    print("Cluster sizes:")
    for label, urls in sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {label}: {len(urls)} bookmarks")
    
    return {
        'similarity_model': similarity_model,
        'clusters': clusters,
        'stats': stats
    }

def load_bookmarks(file_path):
    """
    Lädt Lesezeichen aus einer JSON-Datei.
    
    Args:
        file_path: Pfad zur JSON-Datei
        
    Returns:
        list: Liste von Lesezeichen
    """
    try:
        # Prüfe, ob die Datei eine .gz-Endung hat
        if file_path.endswith('.gz'):
            import gzip
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                bookmarks = json.load(f)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                bookmarks = json.load(f)
        
        print(f"Geladen: {len(bookmarks)} Lesezeichen aus {file_path}")
        return bookmarks
    except Exception as e:
        print(f"Fehler beim Laden der Lesezeichen: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for bookmarks")
    parser.add_argument("input_file", help="Path to the JSON file with enriched bookmarks")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", 
                        help="Name of the sentence-transformers model to use")
    parser.add_argument("--output-dir", default="data/embeddings", 
                        help="Directory to save embeddings and analysis results")
    parser.add_argument("--num-clusters", type=int, default=20,
                        help="Number of clusters to generate")
    parser.add_argument("--skip-clustering", action="store_true",
                        help="Skip the clustering step (useful for large datasets)")
    
    args = parser.parse_args()
    
    # Load enriched bookmarks
    print(f"Loading bookmarks from {args.input_file}")
    bookmarks = load_bookmarks(args.input_file)
    
    print(f"Loaded {len(bookmarks)} bookmarks")
    
    # Generate embeddings
    output_file = os.path.join(args.output_dir, 'bookmark_embeddings.pkl')
    embedding_model = generate_embeddings(
        bookmarks,
        model_name=args.model,
        output_file=output_file
    )
    
    # Analyze embeddings if not skipped
    if not args.skip_clustering:
        try:
            analyze_embeddings(
                embedding_model,
                output_dir=args.output_dir,
                num_clusters=args.num_clusters
            )
        except Exception as e:
            print(f"Error during clustering: {e}")
            print("Clustering failed, but embeddings were successfully generated and saved.")
    else:
        print("Clustering skipped as requested.")
        print(f"Embeddings successfully generated and saved to {output_file}")
        
        # Save basic statistics
        stats = {
            'num_bookmarks': embedding_model.get_count(),
            'embedding_dimension': embedding_model.get_dimension(),
        }
        
        # Save statistics
        stats_file = os.path.join(args.output_dir, 'embedding_stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main() 