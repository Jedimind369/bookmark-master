#!/usr/bin/env python3
"""
Simple tag generator for bookmarks.

This script generates tags for bookmarks based on their title, description, and content preview.
"""

import os
import sys
import json
import re
from pathlib import Path
from collections import Counter

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# Common words to exclude from tags
STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what', 'when',
    'where', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'some',
    'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'to', 'of', 'in', 'for',
    'on', 'with', 'by', 'at', 'from', 'up', 'about', 'into', 'over', 'after', 'is',
    'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do',
    'does', 'did', 'doing', 'this', 'that', 'these', 'those', 'their', 'his', 'her',
    'its', 'they', 'them', 'their', 'while', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
}

# Domain-specific keywords for common categories
DOMAIN_KEYWORDS = {
    'programming': ['code', 'programming', 'developer', 'software', 'github', 'git', 'repository', 'python', 'javascript', 'java', 'c++', 'coding'],
    'data_science': ['data', 'science', 'machine', 'learning', 'ai', 'artificial', 'intelligence', 'neural', 'network', 'deep', 'pandas', 'numpy', 'tensorflow', 'pytorch'],
    'web_development': ['web', 'html', 'css', 'javascript', 'frontend', 'backend', 'fullstack', 'react', 'angular', 'vue', 'node', 'express', 'django', 'flask'],
    'news': ['news', 'article', 'blog', 'post', 'latest', 'update', 'hacker', 'tech', 'technology'],
    'reference': ['documentation', 'docs', 'reference', 'guide', 'tutorial', 'learn', 'how-to', 'wiki', 'encyclopedia'],
    'tools': ['tool', 'utility', 'app', 'application', 'software', 'service', 'platform']
}

def extract_keywords(text):
    """
    Extract keywords from text.
    
    Args:
        text: Text to extract keywords from
        
    Returns:
        List of keywords
    """
    if not text:
        return []
    
    # Convert to lowercase and split into words
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Remove stop words and short words
    filtered_words = [word for word in words if word not in STOP_WORDS and len(word) > 2]
    
    # Count word frequencies
    word_counts = Counter(filtered_words)
    
    # Get the most common words (up to 10)
    common_words = [word for word, count in word_counts.most_common(10)]
    
    return common_words

def categorize_bookmark(keywords):
    """
    Categorize a bookmark based on its keywords.
    
    Args:
        keywords: List of keywords
        
    Returns:
        List of categories
    """
    categories = []
    
    for category, category_keywords in DOMAIN_KEYWORDS.items():
        # Check if any of the keywords match the category keywords
        if any(keyword in category_keywords for keyword in keywords):
            categories.append(category)
    
    return categories

def generate_tags(bookmark):
    """
    Generate tags for a bookmark.
    
    Args:
        bookmark: Bookmark data
        
    Returns:
        List of tags
    """
    # Combine title, description, and content preview
    text = ' '.join(filter(None, [
        bookmark.get('title', ''),
        bookmark.get('description', ''),
        bookmark.get('content_preview', '')[:500]  # Limit to first 500 chars
    ]))
    
    # Extract keywords
    keywords = extract_keywords(text)
    
    # Categorize bookmark
    categories = categorize_bookmark(keywords)
    
    # Combine keywords and categories
    tags = list(set(keywords[:5] + categories))
    
    return tags[:10]  # Limit to 10 tags

def enrich_bookmarks_with_tags(input_file, output_file):
    """
    Enrich bookmarks with tags.
    
    Args:
        input_file: Path to the input JSON file with enriched bookmarks
        output_file: Path to save the output JSON file
    """
    # Load the enriched bookmarks
    with open(input_file, 'r', encoding='utf-8') as f:
        bookmarks = json.load(f)
    
    print(f"Loaded {len(bookmarks)} bookmarks from {input_file}")
    
    # Process each bookmark
    for i, bookmark in enumerate(bookmarks):
        if not bookmark.get('tags') and bookmark.get('scrape_status') == 'success':
            # Generate tags
            tags = generate_tags(bookmark)
            
            # Update the bookmark with tags
            if tags:
                bookmark['tags'] = tags
                print(f"Added tags to {bookmark['url']}: {bookmark['tags']}")
            else:
                print(f"No tags generated for {bookmark['url']}")
        
        # Print progress
        if (i + 1) % 10 == 0 or i == len(bookmarks) - 1:
            print(f"Progress: {i + 1}/{len(bookmarks)} ({(i + 1)/len(bookmarks)*100:.1f}%)")
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(bookmarks, f, indent=2)
    
    print(f"Saved results to {output_file}")
    print(f"Tags generation complete. Processed {len(bookmarks)} bookmarks.")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate tags for bookmarks")
    parser.add_argument("input_file", help="Path to the input JSON file with enriched bookmarks")
    parser.add_argument("--output-file", default="data/enriched/enriched_with_tags.json",
                        help="Path to save the output JSON file")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    
    # Enrich bookmarks with tags
    enrich_bookmarks_with_tags(args.input_file, args.output_file)

if __name__ == "__main__":
    main() 