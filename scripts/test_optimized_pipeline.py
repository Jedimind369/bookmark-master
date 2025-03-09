#!/usr/bin/env python3
"""
Test script for the optimized bookmark processing pipeline.
This script runs a test of the optimized pipeline with a small set of URLs
and reports on performance metrics.
"""

import os
import sys
import json
import time
import argparse
import logging
import psutil
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import subprocess
import traceback

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"test_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def measure_memory_usage(process_name):
    """Measure memory usage of a process by name."""
    memory_usage = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        if process_name in proc.info['name']:
            memory_usage.append(proc.info['memory_info'].rss / (1024 * 1024))  # Convert to MB
    return sum(memory_usage) if memory_usage else 0

def run_command(cmd, description):
    """Run a command and log its output."""
    logger.info(f"Running {description}...")
    start_time = time.time()
    
    memory_samples = []
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Sample memory usage every second
    while process.poll() is None:
        memory_usage = measure_memory_usage("python")
        memory_samples.append(memory_usage)
        time.sleep(1)
    
    stdout, stderr = process.communicate()
    elapsed_time = time.time() - start_time
    
    if process.returncode == 0:
        logger.info(f"{description} completed successfully in {elapsed_time:.2f} seconds")
        logger.info(f"Peak memory usage: {max(memory_samples) if memory_samples else 0:.2f} MB")
        return True, elapsed_time, memory_samples
    else:
        logger.error(f"{description} failed with return code {process.returncode}")
        logger.error(f"STDOUT: {stdout.decode('utf-8')}")
        logger.error(f"STDERR: {stderr.decode('utf-8')}")
        return False, elapsed_time, memory_samples

def plot_memory_usage(memory_samples, title, output_file):
    """Plot memory usage over time."""
    plt.figure(figsize=(10, 6))
    plt.plot(memory_samples)
    plt.title(title)
    plt.xlabel("Time (seconds)")
    plt.ylabel("Memory Usage (MB)")
    plt.grid(True)
    plt.savefig(output_file)
    logger.info(f"Memory usage plot saved to {output_file}")

def compare_performance(original_time, optimized_time, original_memory, optimized_memory, output_file):
    """Compare performance between original and optimized versions."""
    labels = ['Original', 'Optimized']
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # Time comparison
    ax1.bar(labels, [original_time, optimized_time])
    ax1.set_title('Execution Time Comparison')
    ax1.set_ylabel('Time (seconds)')
    ax1.grid(axis='y')
    
    # Memory comparison
    ax2.bar(labels, [original_memory, optimized_memory])
    ax2.set_title('Peak Memory Usage Comparison')
    ax2.set_ylabel('Memory (MB)')
    ax2.grid(axis='y')
    
    plt.tight_layout()
    plt.savefig(output_file)
    logger.info(f"Performance comparison saved to {output_file}")

def create_test_urls(num_urls=10, output_file="test_urls.txt"):
    """Create a test file with URLs."""
    test_urls = [
        "https://github.com/python/cpython",
        "https://stackoverflow.com/questions/1720421/how-do-i-concatenate-two-lists-in-python",
        "https://www.python.org/dev/peps/pep-0008/",
        "https://docs.python.org/3/tutorial/",
        "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "https://realpython.com/python-f-strings/",
        "https://www.djangoproject.com/",
        "https://flask.palletsprojects.com/",
        "https://pandas.pydata.org/docs/",
        "https://numpy.org/doc/stable/",
        "https://matplotlib.org/stable/tutorials/index.html",
        "https://scikit-learn.org/stable/tutorial/index.html",
        "https://pytorch.org/tutorials/",
        "https://www.tensorflow.org/tutorials",
        "https://jupyter.org/",
    ]
    
    # Select the requested number of URLs
    selected_urls = test_urls[:min(num_urls, len(test_urls))]
    
    # Write URLs to file
    with open(output_file, "w") as f:
        for url in selected_urls:
            f.write(f"{url}\n")
    
    logger.info(f"Created test file with {len(selected_urls)} URLs at {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Test the optimized bookmark processing pipeline")
    parser.add_argument("--num-urls", type=int, default=5, help="Number of URLs to test with")
    parser.add_argument("--max-workers", type=int, default=2, help="Maximum number of worker threads")
    parser.add_argument("--compare-original", action="store_true", help="Compare with original pipeline")
    args = parser.parse_args()
    
    try:
        # Create test data
        test_file = create_test_urls(args.num_urls)
        
        # Create output directories
        reports_dir = Path("data/reports")
        reports_dir.mkdir(exist_ok=True, parents=True)
        plots_dir = Path("data/plots")
        plots_dir.mkdir(exist_ok=True, parents=True)
        
        # Test optimized pipeline
        logger.info("=== Testing Optimized Pipeline ===")
        optimized_cmd = (
            f"python scripts/run_hybrid_pipeline_optimized.py "
            f"--input-file {test_file} "
            f"--max-workers {args.max_workers} "
            f"--min-chunk-size 10 "
            f"--max-chunk-size 1000 "
            f"--memory-target 0.7"
        )
        optimized_success, optimized_time, optimized_memory = run_command(optimized_cmd, "Optimized pipeline")
        
        if optimized_success:
            plot_memory_usage(
                optimized_memory, 
                "Memory Usage - Optimized Pipeline", 
                plots_dir / "optimized_memory_usage.png"
            )
        
        # Test original pipeline if requested
        if args.compare_original:
            logger.info("=== Testing Original Pipeline ===")
            original_cmd = (
                f"python scripts/run_hybrid_pipeline.py "
                f"--input-file {test_file} "
                f"--max-workers {args.max_workers}"
            )
            original_success, original_time, original_memory = run_command(original_cmd, "Original pipeline")
            
            if original_success:
                plot_memory_usage(
                    original_memory, 
                    "Memory Usage - Original Pipeline", 
                    plots_dir / "original_memory_usage.png"
                )
            
            # Compare performance if both tests were successful
            if optimized_success and original_success:
                compare_performance(
                    original_time, 
                    optimized_time, 
                    max(original_memory) if original_memory else 0, 
                    max(optimized_memory) if optimized_memory else 0,
                    plots_dir / "performance_comparison.png"
                )
                
                # Calculate improvement percentages
                time_improvement = ((original_time - optimized_time) / original_time) * 100
                memory_improvement = ((max(original_memory) if original_memory else 0 - 
                                      max(optimized_memory) if optimized_memory else 0) / 
                                     max(original_memory) if original_memory else 1) * 100
                
                logger.info("=== Performance Comparison ===")
                logger.info(f"Time: Original={original_time:.2f}s, Optimized={optimized_time:.2f}s, " 
                           f"Improvement={time_improvement:.2f}%")
                logger.info(f"Memory: Original={max(original_memory) if original_memory else 0:.2f}MB, "
                           f"Optimized={max(optimized_memory) if optimized_memory else 0:.2f}MB, "
                           f"Improvement={memory_improvement:.2f}%")
        
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 