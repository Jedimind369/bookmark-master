#!/usr/bin/env python3
"""
Test script for semantic analysis components.
This script tests the BookmarkEmbeddings and BookmarkSimilarity classes
with sample bookmark data.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.semantic.bookmark_embeddings import BookmarkEmbeddings
from scripts.semantic.bookmark_similarity import BookmarkSimilarity

def load_test_data(file_path):
    """Load test bookmark data from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading test data: {e}")
        return None

def extract_bookmarks_from_nested_structure(data):
    """Extract bookmarks from the nested folder structure."""
    bookmarks = []
    
    def extract_from_folder(folder):
        if "items" not in folder:
            return
            
        for item in folder["items"]:
            if item["type"] == "bookmark":
                # Add parent folder information to the bookmark
                item["folder"] = folder.get("name", "")
                bookmarks.append(item)
            elif item["type"] == "folder":
                extract_from_folder(item)
    
    # Start extraction from the root level
    if "bookmarks" in data:
        for item in data["bookmarks"]:
            if item["type"] == "folder":
                extract_from_folder(item)
            elif item["type"] == "bookmark":
                bookmarks.append(item)
    
    return bookmarks

def prepare_bookmark_texts(bookmarks):
    """Prepare text content from bookmarks for embedding."""
    texts = []
    urls = []
    url_to_bookmark = {}
    
    for bookmark in bookmarks:
        if "url" not in bookmark or not bookmark["url"]:
            continue
            
        # Combine title and folder for better semantic representation
        text_parts = []
        if bookmark.get("title"):
            text_parts.append(bookmark["title"])
        if bookmark.get("folder"):
            text_parts.append(f"Folder: {bookmark['folder']}")
            
        combined_text = " ".join(text_parts).strip()
        if combined_text:
            texts.append(combined_text)
            urls.append(bookmark["url"])
            url_to_bookmark[bookmark["url"]] = bookmark
    
    return texts, urls, url_to_bookmark

def test_embeddings():
    """Test the BookmarkEmbeddings class."""
    print("\n=== Testing BookmarkEmbeddings ===")
    
    # Initialize the embeddings model
    start_time = time.time()
    embeddings_model = BookmarkEmbeddings()
    print(f"Model initialization time: {time.time() - start_time:.2f} seconds")
    
    # Load test data
    test_file = "data/bookmarks/test_bookmarks.json"
    data = load_test_data(test_file)
    if not data:
        print("No test data available.")
        return None, None
    
    # Extract bookmarks from nested structure
    bookmarks = extract_bookmarks_from_nested_structure(data)
    print(f"Extracted {len(bookmarks)} bookmarks from nested structure")
    
    # Prepare texts and URLs
    texts, urls, url_to_bookmark = prepare_bookmark_texts(bookmarks)
    print(f"Prepared {len(texts)} bookmarks for embedding")
    
    if not texts:
        print("No bookmark texts available for embedding.")
        return None, None
    
    # Generate embeddings
    start_time = time.time()
    embeddings_model.add_bookmarks(texts, urls)
    print(f"Embedding generation time: {time.time() - start_time:.2f} seconds")
    print(f"Embedding dimension: {embeddings_model.get_dimension()}")
    
    # Test getting an embedding
    if urls:
        test_url = urls[0]
        embedding = embeddings_model.get_embedding(test_url)
        print(f"Retrieved embedding for {test_url}: shape={embedding.shape}")
    
    # Test saving and loading
    save_path = "data/semantic/test_embeddings.pkl"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    embeddings_model.save(save_path)
    print(f"Saved embeddings to {save_path}")
    
    new_model = BookmarkEmbeddings()
    new_model.load(save_path)
    print(f"Loaded embeddings: {new_model.get_count()} bookmarks")
    
    return embeddings_model, url_to_bookmark

def test_similarity(embeddings_model, url_to_bookmark):
    """Test the BookmarkSimilarity class."""
    if not embeddings_model or not url_to_bookmark:
        return
        
    print("\n=== Testing BookmarkSimilarity ===")
    
    # Initialize the similarity model
    start_time = time.time()
    similarity_model = BookmarkSimilarity(embeddings_model)
    print(f"Similarity model initialization time: {time.time() - start_time:.2f} seconds")
    
    # Test finding similar bookmarks
    urls = embeddings_model.get_urls()
    if urls:
        test_url = urls[0]
        print(f"\nFinding bookmarks similar to: {test_url}")
        print(f"Title: {url_to_bookmark[test_url].get('title', 'N/A')}")
        
        similar = similarity_model.find_similar_bookmarks(test_url, top_k=3)
        print("\nSimilar bookmarks:")
        for url, score in similar:
            print(f"- {url_to_bookmark[url].get('title', 'N/A')} (score: {score:.4f})")
    
    # Test text search
    test_query = "development"
    print(f"\nSearching for bookmarks related to: '{test_query}'")
    results = similarity_model.search_by_text(test_query, top_k=3)
    print("\nSearch results:")
    for url, score in results:
        print(f"- {url_to_bookmark[url].get('title', 'N/A')} (score: {score:.4f})")
    
    # Test clustering
    print("\nClustering bookmarks:")
    clusters = similarity_model.cluster_bookmarks(num_clusters=min(3, len(urls)))
    for label, cluster_urls in clusters.items():
        print(f"\nCluster: {label}")
        for i, url in enumerate(cluster_urls[:3]):  # Show only first 3 bookmarks per cluster
            print(f"- {url_to_bookmark[url].get('title', 'N/A')}")
        if len(cluster_urls) > 3:
            print(f"  ... and {len(cluster_urls) - 3} more")

def main():
    """Main function to run the tests."""
    print("Starting semantic analysis tests...")
    
    # Test embeddings
    embeddings_model, url_to_bookmark = test_embeddings()
    
    # Test similarity
    test_similarity(embeddings_model, url_to_bookmark)
    
    print("\nTests completed.")

if __name__ == "__main__":
    main() 