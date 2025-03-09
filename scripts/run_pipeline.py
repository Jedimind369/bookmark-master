#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from scripts.processing.process_bookmarks import process_full_bookmarks
from scripts.scraping.batch_scraper import BatchScraper

def setup_directories():
    """Create necessary directories for the pipeline."""
    directories = [
        "data/processed",
        "data/enriched",
        "data/embeddings",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print(f"Created directories: {', '.join(directories)}")

def log_step(step_name, message):
    """Log a pipeline step."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {step_name}: {message}"
    
    print(log_message)
    
    # Write to log file
    with open("logs/pipeline.log", "a") as f:
        f.write(log_message + "\n")

def run_step(step_name, command):
    """Run a pipeline step as a subprocess."""
    log_step(step_name, f"Running command: {command}")
    
    try:
        # Run the command and capture output
        process = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Log success
        log_step(step_name, "Completed successfully")
        
        return True, process.stdout
    
    except subprocess.CalledProcessError as e:
        # Log error
        log_step(step_name, f"Failed with error: {e}")
        log_step(step_name, f"Error output: {e.stderr}")
        
        return False, e.stderr

def run_pipeline(args):
    """Run the complete bookmark processing pipeline."""
    # Start time
    start_time = time.time()
    
    # Setup directories
    setup_directories()
    
    # Step 1: Parse HTML bookmarks
    log_step("STEP 1", "Parsing HTML bookmarks")
    
    if args.skip_parsing:
        log_step("STEP 1", "Skipped (--skip-parsing flag used)")
    else:
        try:
            parsed_data, valid_bookmarks, stats = process_full_bookmarks(
                args.input_file,
                "data/processed"
            )
            
            log_step("STEP 1", f"Parsed {stats['total_bookmarks']} bookmarks, {stats['valid_bookmarks']} valid")
        except Exception as e:
            log_step("STEP 1", f"Failed with error: {str(e)}")
            return False
    
    # Step 2: Enrich bookmarks with content
    log_step("STEP 2", "Enriching bookmarks with content")
    
    if args.skip_enrichment:
        log_step("STEP 2", "Skipped (--skip-enrichment flag used)")
    else:
        try:
            # Load valid bookmarks
            with open("data/processed/bookmarks_valid_urls.json", "r") as f:
                valid_bookmarks = json.load(f)
            
            # Initialize scraper
            scraper = BatchScraper(
                max_workers=args.max_workers,
                timeout=args.timeout
            )
            
            # Process in batches
            scraper.process_in_batches(
                valid_bookmarks,
                batch_size=args.batch_size,
                output_dir="data/enriched"
            )
            
            log_step("STEP 2", f"Enriched {scraper.stats['success']} bookmarks successfully, {scraper.stats['error']} errors")
        except Exception as e:
            log_step("STEP 2", f"Failed with error: {str(e)}")
            return False
    
    # Step 3: Generate embeddings
    log_step("STEP 3", "Generating embeddings")
    
    if args.skip_embeddings:
        log_step("STEP 3", "Skipped (--skip-embeddings flag used)")
    else:
        success, output = run_step(
            "STEP 3",
            f"python -m scripts.semantic.generate_embeddings data/enriched/enriched_all.json --model {args.model} --num-clusters {args.num_clusters}"
        )
        
        if not success:
            return False
    
    # Step 4: Run dashboard
    log_step("STEP 4", "Starting dashboard")
    
    if args.skip_dashboard:
        log_step("STEP 4", "Skipped (--skip-dashboard flag used)")
    else:
        # Run in background
        dashboard_cmd = "streamlit run scripts/monitoring/dashboard.py"
        
        if args.dashboard_port:
            dashboard_cmd += f" --server.port {args.dashboard_port}"
        
        log_step("STEP 4", f"Running dashboard command: {dashboard_cmd}")
        
        # Use subprocess.Popen to run in background
        subprocess.Popen(
            dashboard_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        log_step("STEP 4", "Dashboard started in background")
    
    # End time
    end_time = time.time()
    duration = end_time - start_time
    
    log_step("PIPELINE", f"Completed in {duration:.2f} seconds")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Run the complete bookmark processing pipeline")
    
    # Input file
    parser.add_argument("input_file", help="Path to the HTML bookmarks file")
    
    # Step control flags
    parser.add_argument("--skip-parsing", action="store_true", help="Skip HTML parsing step")
    parser.add_argument("--skip-enrichment", action="store_true", help="Skip content enrichment step")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip embedding generation step")
    parser.add_argument("--skip-dashboard", action="store_true", help="Skip dashboard startup")
    
    # Enrichment parameters
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for enrichment")
    parser.add_argument("--max-workers", type=int, default=5, help="Max workers for enrichment")
    parser.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds")
    
    # Embedding parameters
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="Embedding model name")
    parser.add_argument("--num-clusters", type=int, default=20, help="Number of clusters to generate")
    
    # Dashboard parameters
    parser.add_argument("--dashboard-port", type=int, help="Port for Streamlit dashboard")
    
    args = parser.parse_args()
    
    # Run the pipeline
    success = run_pipeline(args)
    
    if success:
        print("Pipeline completed successfully!")
    else:
        print("Pipeline failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 