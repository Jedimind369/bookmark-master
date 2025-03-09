import os
import json
import time
import random
import sys
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from pathlib import Path
from datetime import datetime

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

class BatchScraper:
    """
    Batch scraper for enriching bookmark data with content from the web.
    """
    
    def __init__(self, max_workers=5, timeout=15, retry_count=2, 
                 delay_min=1, delay_max=3, user_agent=None):
        """
        Initialize the batch scraper.
        
        Args:
            max_workers (int): Maximum number of concurrent workers
            timeout (int): Request timeout in seconds
            retry_count (int): Number of retries for failed requests
            delay_min (float): Minimum delay between requests in seconds
            delay_max (float): Maximum delay between requests in seconds
            user_agent (str): User agent string to use for requests
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.retry_count = retry_count
        self.delay_min = delay_min
        self.delay_max = delay_max
        
        if user_agent is None:
            self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        else:
            self.user_agent = user_agent
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        # Statistics
        self.stats = {
            'success': 0,
            'error': 0,
            'retry': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _extract_content(self, response, url):
        """
        Extract content from a response.
        
        Args:
            response (requests.Response): Response object
            url (str): URL of the page
            
        Returns:
            dict: Extracted content
        """
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = ""
            if soup.title:
                title = soup.title.string
            
            # Extract description
            description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '')
            
            # Extract main text content (first few paragraphs)
            paragraphs = [p.text.strip() for p in soup.find_all('p') if p.text.strip()]
            main_content = " ".join(paragraphs[:5])  # First 5 paragraphs
            
            # Extract keywords
            keywords = []
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords:
                keywords_text = meta_keywords.get('content', '')
                if keywords_text:
                    keywords = [k.strip() for k in keywords_text.split(',')]
            
            return {
                'title': title,
                'description': description,
                'content_preview': main_content[:1000],  # First 1000 chars
                'keywords': keywords,
                'content_length': len(response.text),
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'scrape_time': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'error': f"Content extraction error: {str(e)}",
                'status_code': response.status_code,
                'scrape_time': datetime.now().isoformat()
            }
    
    def _scrape_url(self, bookmark):
        """
        Scrape a single URL and enrich the bookmark data.
        
        Args:
            bookmark (dict): Bookmark data
            
        Returns:
            dict: Enriched bookmark data
        """
        url = bookmark['url']
        enriched = bookmark.copy()
        
        # Add scraping metadata
        enriched['scrape_attempts'] = 0
        enriched['scrape_status'] = 'pending'
        
        for attempt in range(self.retry_count + 1):
            try:
                enriched['scrape_attempts'] += 1
                
                # Random delay to avoid rate limiting
                if attempt > 0:
                    self.stats['retry'] += 1
                    delay = random.uniform(self.delay_min * 2, self.delay_max * 2)
                else:
                    delay = random.uniform(self.delay_min, self.delay_max)
                
                time.sleep(delay)
                
                # Make the request
                response = self.session.get(url, timeout=self.timeout)
                
                # Extract content if successful
                if response.status_code == 200:
                    content_data = self._extract_content(response, url)
                    enriched.update(content_data)
                    enriched['scrape_status'] = 'success'
                    self.stats['success'] += 1
                    return enriched
                else:
                    enriched['scrape_status'] = f'error: HTTP {response.status_code}'
                    enriched['error'] = f"HTTP error: {response.status_code}"
            
            except requests.Timeout:
                enriched['scrape_status'] = 'error: timeout'
                enriched['error'] = "Request timed out"
            
            except requests.RequestException as e:
                enriched['scrape_status'] = 'error: request'
                enriched['error'] = f"Request error: {str(e)}"
            
            except Exception as e:
                enriched['scrape_status'] = 'error: unknown'
                enriched['error'] = f"Unknown error: {str(e)}"
        
        # If we get here, all attempts failed
        self.stats['error'] += 1
        return enriched
    
    def process_batch(self, bookmarks, output_file=None):
        """
        Process a batch of bookmarks.
        
        Args:
            bookmarks (list): List of bookmark dictionaries
            output_file (str): Path to save the enriched bookmarks
            
        Returns:
            list: Enriched bookmarks
        """
        self.stats['start_time'] = datetime.now().isoformat()
        
        enriched_bookmarks = []
        
        print(f"Processing {len(bookmarks)} bookmarks with {self.max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Map the scrape_url function to all bookmarks
            results = list(tqdm(
                executor.map(self._scrape_url, bookmarks),
                total=len(bookmarks),
                desc="Scraping bookmarks"
            ))
            
            enriched_bookmarks.extend(results)
        
        self.stats['end_time'] = datetime.now().isoformat()
        
        # Save results if output file is specified
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enriched_bookmarks, f, ensure_ascii=False, indent=2)
            
            # Save statistics
            stats_file = output_file.replace('.json', '_stats.json')
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        print(f"Scraping complete. Statistics:")
        print(f"  Success: {self.stats['success']}")
        print(f"  Error: {self.stats['error']}")
        print(f"  Retry: {self.stats['retry']}")
        
        return enriched_bookmarks
    
    def process_in_batches(self, bookmarks, batch_size=50, output_dir="data/enriched"):
        """
        Process bookmarks in batches.
        
        Args:
            bookmarks (list): List of bookmark dictionaries
            batch_size (int): Size of each batch
            output_dir (str): Directory to save the enriched bookmarks
            
        Returns:
            list: All enriched bookmarks
        """
        os.makedirs(output_dir, exist_ok=True)
        
        all_enriched = []
        
        # Process in batches
        for i in range(0, len(bookmarks), batch_size):
            batch = bookmarks[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(bookmarks) + batch_size - 1) // batch_size
            
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} bookmarks)")
            
            # Process the batch
            output_file = os.path.join(output_dir, f"enriched_batch_{batch_num}.json")
            enriched_batch = self.process_batch(batch, output_file)
            
            all_enriched.extend(enriched_batch)
            
            # Save combined results after each batch
            combined_file = os.path.join(output_dir, "enriched_all.json")
            with open(combined_file, 'w', encoding='utf-8') as f:
                json.dump(all_enriched, f, ensure_ascii=False, indent=2)
            
            print(f"Saved batch {batch_num} results to {output_file}")
            print(f"Saved combined results to {combined_file}")
            
            # Short pause between batches
            if i + batch_size < len(bookmarks):
                pause = random.uniform(2, 5)
                print(f"Pausing for {pause:.1f} seconds before next batch...")
                time.sleep(pause)
        
        return all_enriched

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch scrape bookmark content")
    parser.add_argument("input_file", help="Path to the JSON file with bookmark URLs")
    parser.add_argument("--output-dir", default="data/enriched", 
                        help="Directory to save the enriched bookmarks")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="Size of each batch")
    parser.add_argument("--max-workers", type=int, default=5,
                        help="Maximum number of concurrent workers")
    parser.add_argument("--timeout", type=int, default=15,
                        help="Request timeout in seconds")
    
    args = parser.parse_args()
    
    # Load bookmarks
    with open(args.input_file, 'r', encoding='utf-8') as f:
        bookmarks = json.load(f)
    
    # Initialize scraper
    scraper = BatchScraper(
        max_workers=args.max_workers,
        timeout=args.timeout
    )
    
    # Process bookmarks in batches
    scraper.process_in_batches(
        bookmarks,
        batch_size=args.batch_size,
        output_dir=args.output_dir
    )

if __name__ == "__main__":
    main() 