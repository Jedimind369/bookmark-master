# Bookmark Processing Pipeline - Optimized Version

This repository contains an optimized version of the bookmark processing pipeline, designed to handle large datasets efficiently with reduced memory usage and improved performance.

## Key Optimizations

1. **Chunk-based Processing**: Process large files in chunks to reduce memory usage
2. **Parallel Processing**: Utilize multiple worker threads for improved performance
3. **Dynamic Chunk Sizing**: Adjust chunk size based on available memory
4. **Thread-safe UI Updates**: Provide real-time progress updates without blocking the UI
5. **Robust Error Handling**: Handle errors in individual chunks without failing the entire process
6. **Cancellation Support**: Allow graceful cancellation of running processes

## Components

The optimized pipeline consists of the following components:

1. **Chunk Processor** (`scripts/processing/chunk_processor.py`): Core component for chunk-based processing
2. **Pipeline Integration** (`scripts/processing/pipeline_integration.py`): Integration with existing pipeline components
3. **Optimized Hybrid Scraper** (`scripts/scraping/hybrid_scraper_optimized.py`): Optimized version of the hybrid scraper
4. **Optimized Description Generator** (`scripts/ai/enhanced_descriptions_optimized.py`): Optimized version of the description generator
5. **Optimized HTML Report Generator** (`scripts/export/simple_html_report_optimized.py`): Optimized version of the HTML report generator
6. **Optimized Hybrid Pipeline** (`scripts/run_hybrid_pipeline_optimized.py`): Optimized version of the hybrid pipeline

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bookmark-processing.git
   cd bookmark-processing
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements-optimized.txt
   ```

## Usage

### Running the Optimized Pipeline

```bash
python scripts/run_hybrid_pipeline_optimized.py --input-file urls.txt --max-workers 4
```

### Command-line Options

- `--input-file`: Path to the input file containing URLs (one per line)
- `--limit`: Maximum number of URLs to process (default: process all)
- `--max-workers`: Maximum number of worker threads (default: 2)
- `--max-text-length`: Maximum length of extracted text (default: 10000)
- `--dynamic-threshold`: Dynamic threshold for clustering (default: 0.5)
- `--num-clusters`: Number of clusters for semantic analysis (default: 10)
- `--skip-scraping`: Skip the scraping step (default: False)
- `--existing-enriched`: Path to existing enriched data file
- `--scrapingbee-key`: ScrapingBee API key
- `--smartproxy-url`: Smartproxy URL
- `--min-chunk-size`: Minimum chunk size in KB (default: 50)
- `--max-chunk-size`: Maximum chunk size in KB (default: 10000)
- `--memory-target`: Target memory usage percentage (default: 0.7)

### Running Individual Components

#### Hybrid Scraper

```bash
python scripts/scraping/hybrid_scraper_optimized.py --input urls.txt --output data/enriched/enriched.json.gz --max-workers 4
```

#### Description Generator

```bash
python scripts/ai/enhanced_descriptions_optimized.py data/enriched/enriched.json.gz --output-file data/enriched/enhanced.json.gz --max-workers 4
```

#### HTML Report Generator

```bash
python scripts/export/simple_html_report_optimized.py data/enriched/enhanced.json.gz data/reports/report.html --max-workers 4
```

## Testing

To test the optimized pipeline and compare it with the original version:

```bash
./run_test.sh
```

This will:
1. Create a virtual environment
2. Install dependencies
3. Run the test script with 5 URLs
4. Generate performance comparison plots

## Performance Comparison

The optimized pipeline offers significant improvements in:

- **Memory Usage**: Reduced memory footprint, especially for large datasets
- **Processing Speed**: Faster processing through parallel execution
- **Stability**: Improved error handling and recovery
- **Scalability**: Better handling of large datasets

## Documentation

For detailed documentation on the optimizations, see:

- [Optimization Details](scripts/processing/OPTIMIZATION.md): Detailed explanation of the optimizations
- [API Documentation](docs/api.md): API documentation for the optimized components
- [Performance Benchmarks](docs/benchmarks.md): Performance benchmarks comparing original and optimized versions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 