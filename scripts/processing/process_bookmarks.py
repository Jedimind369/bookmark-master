import os
import json
import sys
from tqdm import tqdm
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.scraping.bookmark_parser import BookmarkParser

def process_full_bookmarks(input_file, output_dir):
    """
    Process a full HTML bookmarks file and save structured data to JSON.
    
    Args:
        input_file (str): Path to the HTML bookmarks file
        output_dir (str): Directory to save the output JSON files
    
    Returns:
        tuple: (parsed_data, bookmark_urls, stats)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize parser
    parser = BookmarkParser()
    
    print(f"Parsing bookmarks file: {input_file}")
    try:
        # Parse the full bookmarks file
        parsed_data = parser.parse_file(input_file)
        
        # Extract URLs and metadata
        print("Extracting URLs and metadata...")
        bookmark_urls = parser.extract_urls(parsed_data)
        
        # Validate URLs
        print("Validating URLs...")
        valid_bookmarks = []
        invalid_bookmarks = []
        
        for bookmark in tqdm(bookmark_urls):
            try:
                if parser._is_valid_url(bookmark['url']):
                    valid_bookmarks.append(bookmark)
                else:
                    invalid_bookmarks.append({
                        "bookmark": bookmark,
                        "error": "Invalid URL format"
                    })
            except Exception as e:
                invalid_bookmarks.append({
                    "bookmark": bookmark,
                    "error": str(e)
                })
        
        # Save structured data
        structured_file = os.path.join(output_dir, "bookmarks_structured.json")
        urls_file = os.path.join(output_dir, "bookmarks_urls.json")
        valid_urls_file = os.path.join(output_dir, "bookmarks_valid_urls.json")
        invalid_urls_file = os.path.join(output_dir, "bookmarks_invalid_urls.json")
        
        parser.save_to_file(parsed_data, structured_file)
        parser.save_urls_to_file(bookmark_urls, urls_file)
        parser.save_bookmarks_to_file(valid_bookmarks, valid_urls_file)
        
        with open(invalid_urls_file, 'w', encoding='utf-8') as f:
            json.dump(invalid_bookmarks, f, ensure_ascii=False, indent=2)
        
        # Compile statistics
        stats = {
            "total_bookmarks": len(bookmark_urls),
            "valid_bookmarks": len(valid_bookmarks),
            "invalid_bookmarks": len(invalid_bookmarks),
            "folders": len(parsed_data.get("folders", [])),
            "browser_type": parsed_data.get("browser", "unknown")
        }
        
        # Save statistics
        stats_file = os.path.join(output_dir, "processing_stats.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"Processing complete. Statistics:")
        print(f"  Total bookmarks: {stats['total_bookmarks']}")
        print(f"  Valid bookmarks: {stats['valid_bookmarks']}")
        print(f"  Invalid bookmarks: {stats['invalid_bookmarks']}")
        print(f"  Folders: {stats['folders']}")
        print(f"  Browser type: {stats['browser_type']}")
        print(f"Results saved to {output_dir}")
        
        return parsed_data, valid_bookmarks, stats
        
    except Exception as e:
        print(f"Error processing bookmarks file: {str(e)}")
        raise

def process_partial_bookmarks(input_file, output_dir, start_index=0, end_index=None, batch_size=50):
    """
    Process a subset of bookmarks from an HTML file in batches.
    
    Args:
        input_file (str): Path to the HTML bookmarks file
        output_dir (str): Directory to save the output JSON files
        start_index (int): Starting index for bookmark processing
        end_index (int): Ending index for bookmark processing (None = process until end)
        batch_size (int): Size of each processing batch
    
    Returns:
        tuple: (valid_bookmarks, invalid_bookmarks, stats)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize parser
    parser = BookmarkParser()
    
    print(f"Parsing bookmarks file: {input_file}")
    try:
        # Parse the full bookmarks file
        parsed_data = parser.parse_file(input_file)
        
        # Extract URLs and metadata
        print("Extracting URLs and metadata...")
        all_bookmarks = parser.extract_urls(parsed_data)
        
        # Select the subset of bookmarks to process
        if end_index is None:
            end_index = len(all_bookmarks)
        
        selected_bookmarks = all_bookmarks[start_index:end_index]
        print(f"Processing {len(selected_bookmarks)} of {len(all_bookmarks)} bookmarks (indices {start_index} to {end_index-1})")
        
        # Process in batches
        all_valid = []
        all_invalid = []
        total_batches = (len(selected_bookmarks) + batch_size - 1) // batch_size
        
        for i in range(0, len(selected_bookmarks), batch_size):
            batch = selected_bookmarks[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} bookmarks)")
            
            # Validate URLs
            valid_batch = []
            invalid_batch = []
            
            for bookmark in tqdm(batch, desc=f"Batch {batch_num}"):
                try:
                    if parser._is_valid_url(bookmark['url']):
                        valid_batch.append(bookmark)
                    else:
                        invalid_batch.append({
                            "bookmark": bookmark,
                            "error": "Invalid URL format"
                        })
                except Exception as e:
                    invalid_batch.append({
                        "bookmark": bookmark,
                        "error": str(e)
                    })
            
            # Save batch results
            batch_dir = os.path.join(output_dir, f"batch_{batch_num}")
            os.makedirs(batch_dir, exist_ok=True)
            
            valid_file = os.path.join(batch_dir, "valid_bookmarks.json")
            invalid_file = os.path.join(batch_dir, "invalid_bookmarks.json")
            
            parser.save_bookmarks_to_file(valid_batch, valid_file)
            
            with open(invalid_file, 'w', encoding='utf-8') as f:
                json.dump(invalid_batch, f, ensure_ascii=False, indent=2)
            
            # Add to overall results
            all_valid.extend(valid_batch)
            all_invalid.extend(invalid_batch)
            
            print(f"Batch {batch_num} complete: {len(valid_batch)} valid, {len(invalid_batch)} invalid bookmarks")
        
        # Save overall results
        valid_urls_file = os.path.join(output_dir, "all_valid_bookmarks.json")
        invalid_urls_file = os.path.join(output_dir, "all_invalid_bookmarks.json")
        
        parser.save_bookmarks_to_file(all_valid, valid_urls_file)
        
        with open(invalid_urls_file, 'w', encoding='utf-8') as f:
            json.dump(all_invalid, f, ensure_ascii=False, indent=2)
        
        # Compile statistics
        stats = {
            "total_processed": len(selected_bookmarks),
            "valid_bookmarks": len(all_valid),
            "invalid_bookmarks": len(all_invalid),
            "start_index": start_index,
            "end_index": end_index,
            "batch_size": batch_size,
            "total_batches": total_batches,
            "browser_type": parsed_data.get("browser", "unknown")
        }
        
        # Save statistics
        stats_file = os.path.join(output_dir, "processing_stats.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"Processing complete. Statistics:")
        print(f"  Processed bookmarks: {stats['total_processed']}")
        print(f"  Valid bookmarks: {stats['valid_bookmarks']}")
        print(f"  Invalid bookmarks: {stats['invalid_bookmarks']}")
        print(f"Results saved to {output_dir}")
        
        return all_valid, all_invalid, stats
        
    except Exception as e:
        print(f"Error processing bookmarks file: {str(e)}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process HTML bookmarks file")
    parser.add_argument("input_file", help="Path to the HTML bookmarks file")
    parser.add_argument("--output-dir", default="data/processed", 
                        help="Directory to save the output JSON files")
    parser.add_argument("--start", type=int, default=0,
                        help="Starting index for bookmark processing")
    parser.add_argument("--end", type=int, default=None,
                        help="Ending index for bookmark processing (None = process until end)")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="Size of each processing batch")
    
    args = parser.parse_args()
    
    if args.start > 0 or args.end is not None:
        process_partial_bookmarks(
            args.input_file,
            args.output_dir,
            start_index=args.start,
            end_index=args.end,
            batch_size=args.batch_size
        )
    else:
        process_full_bookmarks(args.input_file, args.output_dir) 