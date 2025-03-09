#!/usr/bin/env python3
"""
Extract bookmarks from the structured JSON file into a flat list format.
"""

import json
import os
import sys
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

def extract_bookmarks(items, result=None):
    """
    Recursively extract all bookmarks from a nested structure.
    
    Args:
        items: List of items (bookmarks or folders)
        result: List to store extracted bookmarks
        
    Returns:
        List of bookmark objects
    """
    if result is None:
        result = []
    
    for item in items:
        if item['type'] == 'bookmark':
            result.append({
                'title': item['title'],
                'url': item['url'],
                'folder': item['folder'],
                'depth': item['depth'],
                'added': item['added'],
                'last_modified': item['last_modified'],
                'description': item['description'],
                'tags': item['tags']
            })
        elif item['type'] == 'folder' and 'items' in item:
            extract_bookmarks(item['items'], result)
    
    return result

def main():
    """Main function to extract bookmarks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract bookmarks from structured JSON")
    parser.add_argument("input_file", help="Path to the structured JSON file")
    parser.add_argument("--output-file", default="data/processed/simple_process/all_valid_bookmarks.json",
                        help="Path to save the extracted bookmarks")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    
    # Load the structured bookmarks
    with open(args.input_file, 'r') as f:
        data = json.load(f)
    
    # Extract all bookmarks
    all_bookmarks = extract_bookmarks(data['bookmarks'])
    
    # Save to a new file
    with open(args.output_file, 'w') as f:
        json.dump(all_bookmarks, f, indent=2)
    
    print(f'Extracted {len(all_bookmarks)} bookmarks to {args.output_file}')

if __name__ == "__main__":
    main() 