#!/usr/bin/env python3

"""
prompt_cache.py

Implements a hybrid caching system for AI model responses, combining:
1. Exact match caching - For identical prompts
2. Semantic caching - For similar prompts using embeddings

This reduces API costs and improves response times for similar queries.
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union

# Path for cache storage
CACHE_DIR = Path(__file__).parent.parent.parent / "cache" / "ai_responses"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent.parent / "logs" / "cache_usage.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("prompt_cache")

# Cache configuration
CACHE_CONFIG = {
    "ttl_days": 30,                  # Time-to-live for cache entries (days)
    "semantic_threshold": 0.85,      # Similarity threshold for semantic matches (0-1)
    "max_cache_entries": 1000,       # Maximum number of cache entries per type
    "embedding_dimension": 384,      # Dimension of embeddings (depends on the model)
    "semantic_cache_enabled": True,  # Toggle for semantic caching
}

try:
    # Try to import sentence-transformers for embeddings
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')  # Small, fast model
    EMBEDDINGS_AVAILABLE = True
    logger.info("Sentence Transformers loaded successfully for semantic caching")
except ImportError:
    # Fall back to no semantic caching if the library is not available
    EMBEDDINGS_AVAILABLE = False
    logger.warning("Sentence Transformers not available - semantic caching disabled")
    CACHE_CONFIG["semantic_cache_enabled"] = False

def get_cache_key(prompt: str) -> str:
    """
    Generate a cache key for a prompt.
    
    Args:
        prompt (str): The prompt text
        
    Returns:
        str: A hash key for the prompt
    """
    # Create a SHA-256 hash of the prompt
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    return prompt_hash

def clean_cache() -> None:
    """
    Clean expired entries from the cache.
    """
    now = datetime.now()
    expiry_date = now - timedelta(days=CACHE_CONFIG["ttl_days"])
    count_removed = 0
    
    # Check all files in the cache directory
    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            cache_data = json.loads(cache_file.read_text())
            timestamp_str = cache_data.get("timestamp")
            
            if timestamp_str:
                cache_time = datetime.fromisoformat(timestamp_str)
                if cache_time < expiry_date:
                    cache_file.unlink()
                    count_removed += 1
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error processing cache file {cache_file}: {str(e)}")
            # Remove invalid cache files
            cache_file.unlink()
            count_removed += 1
    
    if count_removed > 0:
        logger.info(f"Cleaned {count_removed} expired/invalid cache entries")
    
    # Check if we need to trim the cache to the maximum size
    all_cache_files = list(CACHE_DIR.glob("*_exact.json"))
    if len(all_cache_files) > CACHE_CONFIG["max_cache_entries"]:
        # Sort by modification time (oldest first)
        all_cache_files.sort(key=lambda x: x.stat().st_mtime)
        # Remove oldest entries to get down to the maximum
        files_to_remove = all_cache_files[:len(all_cache_files) - CACHE_CONFIG["max_cache_entries"]]
        for file in files_to_remove:
            file.unlink()
            
            # Also remove the corresponding semantic cache file if it exists
            semantic_file = CACHE_DIR / f"{file.stem.replace('_exact', '')}_semantic.json"
            if semantic_file.exists():
                semantic_file.unlink()
                
        logger.info(f"Trimmed cache to {CACHE_CONFIG['max_cache_entries']} entries")

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        v1, v2: The vectors to compare
        
    Returns:
        float: Similarity score (0-1)
    """
    # Convert to numpy arrays for efficient calculation
    v1_array = np.array(v1)
    v2_array = np.array(v2)
    
    # Calculate dot product and magnitudes
    dot_product = np.dot(v1_array, v2_array)
    norm_v1 = np.linalg.norm(v1_array)
    norm_v2 = np.linalg.norm(v2_array)
    
    # Avoid division by zero
    if norm_v1 == 0 or norm_v2 == 0:
        return 0
    
    # Cosine similarity formula
    similarity = dot_product / (norm_v1 * norm_v2)
    return float(similarity)

def compute_embedding(text: str) -> Optional[List[float]]:
    """
    Compute embedding vector for text.
    
    Args:
        text (str): Text to embed
        
    Returns:
        list[float] or None: Embedding vector or None if not available
    """
    if not EMBEDDINGS_AVAILABLE or not CACHE_CONFIG["semantic_cache_enabled"]:
        return None
    
    try:
        # Generate embedding using sentence-transformers
        embedding = EMBEDDING_MODEL.encode(text)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error computing embedding: {str(e)}")
        return None

def find_similar_cached_response(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Find semantically similar cached responses.
    
    Args:
        prompt (str): The prompt to find similar responses for
        
    Returns:
        dict or None: Most similar cached response or None if no match
    """
    if not EMBEDDINGS_AVAILABLE or not CACHE_CONFIG["semantic_cache_enabled"]:
        return None
    
    try:
        # Compute embedding for the input prompt
        prompt_embedding = compute_embedding(prompt)
        if prompt_embedding is None:
            return None
        
        best_match = None
        best_similarity = 0
        
        # Search all semantic cache files
        for cache_file in CACHE_DIR.glob("*_semantic.json"):
            try:
                cache_data = json.loads(cache_file.read_text())
                cached_embedding = cache_data.get("embedding")
                
                if cached_embedding:
                    # Calculate similarity between prompt and cached item
                    similarity = cosine_similarity(prompt_embedding, cached_embedding)
                    
                    # Keep track of the best match
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = cache_data
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error reading semantic cache file {cache_file}: {str(e)}")
        
        # Return the best match if it exceeds our threshold
        if best_match and best_similarity >= CACHE_CONFIG["semantic_threshold"]:
            logger.info(f"Semantic cache hit with similarity: {best_similarity:.4f}")
            return {
                "response": best_match["response"],
                "original_prompt": best_match["prompt"],
                "similarity": best_similarity
            }
        
        logger.info(f"No semantic match found (best similarity: {best_similarity:.4f})")
        return None
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")
        return None

def cache_response(prompt: str, response: Any, model_id: str = "unknown") -> None:
    """
    Cache a response for both exact and semantic matching.
    
    Args:
        prompt (str): The original prompt
        response (any): The model's response
        model_id (str): Identifier for the model used
    """
    try:
        # Generate cache key
        key = get_cache_key(prompt)
        timestamp = datetime.now().isoformat()
        
        # Prepare cache data
        cache_data = {
            "prompt": prompt,
            "response": response,
            "model_id": model_id,
            "timestamp": timestamp
        }
        
        # Save exact match cache
        exact_cache_file = CACHE_DIR / f"{key}_exact.json"
        with open(exact_cache_file, "w") as f:
            json.dump(cache_data, f)
        
        # If semantic caching is enabled, compute and save embeddings
        if EMBEDDINGS_AVAILABLE and CACHE_CONFIG["semantic_cache_enabled"]:
            # Compute embedding
            embedding = compute_embedding(prompt)
            if embedding:
                # Add embedding to cache data
                semantic_cache_data = cache_data.copy()
                semantic_cache_data["embedding"] = embedding
                
                # Save semantic cache
                semantic_cache_file = CACHE_DIR / f"{key}_semantic.json"
                with open(semantic_cache_file, "w") as f:
                    json.dump(semantic_cache_data, f)
        
        logger.info(f"Cached response for prompt (key: {key})")
        
        # Periodically clean the cache (randomly with 5% probability)
        if np.random.random() < 0.05:
            clean_cache()
    except Exception as e:
        logger.error(f"Error caching response: {str(e)}")

def get_cached_response(prompt: str, use_semantic: bool = True) -> Optional[Dict[str, Any]]:
    """
    Get a cached response for a prompt, trying exact match first, then semantic.
    
    Args:
        prompt (str): The prompt to look up
        use_semantic (bool): Whether to try semantic matching if exact fails
        
    Returns:
        dict or None: Cached response or None if not found
    """
    # Check for exact match first
    key = get_cache_key(prompt)
    exact_cache_file = CACHE_DIR / f"{key}_exact.json"
    
    if exact_cache_file.exists():
        try:
            cache_data = json.loads(exact_cache_file.read_text())
            logger.info(f"Exact cache hit for prompt (key: {key})")
            return {
                "response": cache_data["response"],
                "cache_type": "exact",
                "model_id": cache_data.get("model_id", "unknown"),
                "timestamp": cache_data.get("timestamp")
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error reading exact cache: {str(e)}")
    
    # If no exact match and semantic caching is enabled, try semantic
    if use_semantic and EMBEDDINGS_AVAILABLE and CACHE_CONFIG["semantic_cache_enabled"]:
        semantic_result = find_similar_cached_response(prompt)
        if semantic_result:
            return {
                "response": semantic_result["response"],
                "cache_type": "semantic",
                "similarity": semantic_result["similarity"],
                "original_prompt": semantic_result["original_prompt"]
            }
    
    # No cache hit
    return None

def cached_call(prompt: str, api_call_function, model_id: str = "unknown", 
               use_semantic: bool = True, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get a cached response or call the API if not cached.
    
    Args:
        prompt (str): The prompt to process
        api_call_function (callable): Function to call the AI API if no cache hit
        model_id (str): Model identifier
        use_semantic (bool): Whether to use semantic caching
        force_refresh (bool): Whether to force a fresh API call
        
    Returns:
        dict: Response with metadata
    """
    # Skip cache if forced refresh
    if not force_refresh:
        # Try to get from cache
        cached = get_cached_response(prompt, use_semantic)
        if cached:
            logger.info(f"Cache hit for prompt (type: {cached['cache_type']})")
            return {
                "response": cached["response"],
                "source": cached["cache_type"],
                "model_id": cached.get("model_id", model_id),
                "cached": True,
                **({
                    "similarity": cached["similarity"],
                    "original_prompt": cached["original_prompt"]
                } if cached["cache_type"] == "semantic" else {})
            }
    
    # Cache miss or forced refresh, call the API
    logger.info(f"Cache miss for prompt, calling API with model {model_id}")
    api_response = api_call_function(prompt)
    
    # Cache the new response
    cache_response(prompt, api_response, model_id)
    
    return {
        "response": api_response,
        "source": "api",
        "model_id": model_id,
        "cached": False
    }

# Example usage
if __name__ == "__main__":
    # Define a mock API call function
    def mock_api_call(prompt):
        return f"This is a mock response for: {prompt}"
    
    # Test exact caching
    test_prompt = "What is the capital of France?"
    result1 = cached_call(test_prompt, mock_api_call, "test_model")
    print(f"First call (API): {result1['source']}")
    
    # Should hit exact cache
    result2 = cached_call(test_prompt, mock_api_call, "test_model")
    print(f"Second call (should be cached): {result2['source']}")
    
    # Test semantic caching if available
    if EMBEDDINGS_AVAILABLE:
        similar_prompt = "Tell me the capital city of France."
        result3 = cached_call(similar_prompt, mock_api_call, "test_model")
        print(f"Similar prompt call: {result3['source']}")
        if result3['source'] == 'semantic':
            print(f"Similarity: {result3['similarity']:.4f}")
    
    # Force refresh
    result4 = cached_call(test_prompt, mock_api_call, force_refresh=True)
    print(f"Forced refresh call: {result4['source']}") 