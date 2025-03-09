#!/usr/bin/env python3
"""
Enrich bookmarks with tags using the ContentAnalyzer.

This script takes the enriched bookmarks and adds tags using AI analysis.
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.scraping.content_analyzer import ContentAnalyzer

async def enrich_bookmarks_with_tags(input_file, output_file, batch_size=5):
    """
    Enrich bookmarks with tags using the ContentAnalyzer.
    
    Args:
        input_file: Path to the input JSON file with enriched bookmarks
        output_file: Path to save the output JSON file
        batch_size: Number of bookmarks to process in each batch
    """
    # Load the enriched bookmarks
    with open(input_file, 'r', encoding='utf-8') as f:
        bookmarks = json.load(f)
    
    print(f"Loaded {len(bookmarks)} bookmarks from {input_file}")
    
    # Initialize the ContentAnalyzer
    analyzer = ContentAnalyzer(output_dir="data/analyzed")
    
    # Process bookmarks in batches
    total_bookmarks = len(bookmarks)
    processed_count = 0
    
    for i in range(0, total_bookmarks, batch_size):
        batch = bookmarks[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(total_bookmarks + batch_size - 1)//batch_size} ({len(batch)} bookmarks)")
        
        # Process each bookmark in the batch
        for bookmark in batch:
            if not bookmark.get('tags') and bookmark.get('scrape_status') == 'success':
                try:
                    # Create a simplified version of the scraped data for the analyzer
                    scraped_data = {
                        'url': bookmark['url'],
                        'title': bookmark['title'],
                        'description': bookmark.get('description', ''),
                        'content_preview': bookmark.get('content_preview', '')
                    }
                    
                    # Analyze the content
                    analyzed_data = await analyzer.analyze_content(bookmark['url'], scraped_data)
                    
                    # Update the bookmark with tags
                    if 'tags' in analyzed_data and analyzed_data['tags']:
                        bookmark['tags'] = analyzed_data['tags']
                        print(f"Added tags to {bookmark['url']}: {bookmark['tags']}")
                    else:
                        print(f"No tags generated for {bookmark['url']}")
                        
                except Exception as e:
                    print(f"Error analyzing {bookmark['url']}: {str(e)}")
            
            processed_count += 1
            print(f"Progress: {processed_count}/{total_bookmarks} ({processed_count/total_bookmarks*100:.1f}%)")
        
        # Save intermediate results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(bookmarks, f, indent=2)
        
        print(f"Saved intermediate results to {output_file}")
    
    # Save final results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(bookmarks, f, indent=2)
    
    print(f"Saved final results to {output_file}")
    print(f"Tags generation complete. Processed {processed_count} bookmarks.")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Enrich bookmarks with tags using AI")
    parser.add_argument("input_file", help="Path to the input JSON file with enriched bookmarks")
    parser.add_argument("--output-file", default="data/enriched/enriched_with_tags.json",
                        help="Path to save the output JSON file")
    parser.add_argument("--batch-size", type=int, default=5,
                        help="Number of bookmarks to process in each batch")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    
    # Enrich bookmarks with tags
    await enrich_bookmarks_with_tags(args.input_file, args.output_file, args.batch_size)

if __name__ == "__main__":
    asyncio.run(main()) 