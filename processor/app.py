#!/usr/bin/env python3
"""
Optimierter Verarbeitungs-Microservice mit API und Prometheus-Metriken
"""

import os
import sys
import json
import time
import logging
import psutil
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
from prometheus_client import start_http_server, Counter, Gauge, Histogram
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app

# Import der optimierten Verarbeitungskomponenten
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processing.chunk_processor import ChunkProcessor
from processing.pipeline_integration import PipelineIntegration

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus Metriken
PROCESSING_REQUESTS = Counter('bookmark_processing_requests_total', 'Total processing requests')
PROCESSING_ERRORS = Counter('bookmark_processing_errors_total', 'Total processing errors')
PROCESSING_TIME = Histogram('bookmark_processing_duration_seconds', 'Time spent processing')
MEMORY_USAGE = Gauge('bookmark_memory_usage_bytes', 'Memory usage in bytes')
ACTIVE_WORKERS = Gauge('bookmark_active_workers', 'Number of active worker threads')
CHUNK_SIZE = Histogram('bookmark_chunk_size_bytes', 'Size of processed chunks')

# Flask App
app = Flask(__name__)

# Prometheus Metrics Endpoint
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

# Konfiguration aus Umgebungsvariablen
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 2))
MIN_CHUNK_SIZE = int(os.environ.get('MIN_CHUNK_SIZE', 50))
MAX_CHUNK_SIZE = int(os.environ.get('MAX_CHUNK_SIZE', 10000))
MEMORY_TARGET = float(os.environ.get('MEMORY_TARGET', 0.7))

# Initialisierung der Pipeline-Integration
pipeline = PipelineIntegration(
    max_workers=MAX_WORKERS,
    min_chunk_size=MIN_CHUNK_SIZE,
    max_chunk_size=MAX_CHUNK_SIZE,
    memory_target_percentage=MEMORY_TARGET
)

# Prometheus Callbacks
def prometheus_progress_callback(progress, stats):
    """Callback für Prometheus-Metriken bei Fortschrittsänderungen"""
    MEMORY_USAGE.set(stats.get('memory_usage', 0))
    ACTIVE_WORKERS.set(stats.get('active_workers', 0))
    if 'chunk_size' in stats:
        CHUNK_SIZE.observe(stats['chunk_size'])

def prometheus_status_callback(status, stats):
    """Callback für Prometheus-Metriken bei Statusänderungen"""
    logger.info(f"Status: {status}, Stats: {stats}")

def prometheus_error_callback(message, exception):
    """Callback für Prometheus-Metriken bei Fehlern"""
    PROCESSING_ERRORS.inc()
    logger.error(f"Error: {message}, Exception: {str(exception)}")

def prometheus_complete_callback(stats):
    """Callback für Prometheus-Metriken bei Abschluss"""
    logger.info(f"Processing completed. Stats: {stats}")

# Setze Callbacks
pipeline.set_callback('progress', prometheus_progress_callback)
pipeline.set_callback('status', prometheus_status_callback)
pipeline.set_callback('error', prometheus_error_callback)
pipeline.set_callback('complete', prometheus_complete_callback)

# Hilfsfunktion für Speichernutzung
def get_memory_usage():
    """Gibt die aktuelle Speichernutzung in Bytes zurück"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss

# API-Endpunkte
@app.route('/health', methods=['GET'])
def health_check():
    """Gesundheitscheck-Endpunkt"""
    memory_usage = get_memory_usage()
    MEMORY_USAGE.set(memory_usage)
    
    return jsonify({
        "status": "healthy",
        "memory_usage": memory_usage,
        "max_workers": MAX_WORKERS,
        "min_chunk_size": MIN_CHUNK_SIZE,
        "max_chunk_size": MAX_CHUNK_SIZE,
        "memory_target": MEMORY_TARGET
    })

@app.route('/process/json', methods=['POST'])
def process_json():
    """Verarbeitet eine JSON-Datei mit dem optimierten Processor"""
    PROCESSING_REQUESTS.inc()
    start_time = time.time()
    
    try:
        data = request.json
        input_file = data.get('input_file')
        output_file = data.get('output_file')
        processor_func_name = data.get('processor_func', 'default')
        
        logger.info(f"Processing JSON file: {input_file} -> {output_file} with {processor_func_name}")
        
        # Hier würde die tatsächliche Verarbeitungslogik implementiert
        # Beispiel:
        result = pipeline.process_json_file(
            input_file=input_file,
            output_file=output_file,
            processor_func=getattr(pipeline, f"process_{processor_func_name}", pipeline.process_default)
        )
        
        processing_time = time.time() - start_time
        PROCESSING_TIME.observe(processing_time)
        
        return jsonify({
            "status": "success",
            "processing_time": processing_time,
            "result": result
        })
    
    except Exception as e:
        PROCESSING_ERRORS.inc()
        logger.error(f"Error during processing: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/process/urls', methods=['POST'])
def process_urls():
    """Verarbeitet eine URL-Liste mit dem optimierten Processor"""
    PROCESSING_REQUESTS.inc()
    start_time = time.time()
    
    try:
        data = request.json
        input_file = data.get('input_file')
        output_file = data.get('output_file')
        limit = data.get('limit')
        
        logger.info(f"Processing URL list: {input_file} -> {output_file} with limit {limit}")
        
        result = pipeline.process_url_list(
            input_file=input_file,
            output_file=output_file,
            limit=limit
        )
        
        processing_time = time.time() - start_time
        PROCESSING_TIME.observe(processing_time)
        
        return jsonify({
            "status": "success",
            "processing_time": processing_time,
            "result": result
        })
    
    except Exception as e:
        PROCESSING_ERRORS.inc()
        logger.error(f"Error during URL processing: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/process/report', methods=['POST'])
def generate_report():
    """Generiert einen HTML-Bericht aus einer JSON-Datei"""
    PROCESSING_REQUESTS.inc()
    start_time = time.time()
    
    try:
        data = request.json
        input_file = data.get('input_file')
        output_file = data.get('output_file')
        
        logger.info(f"Generating report: {input_file} -> {output_file}")
        
        result = pipeline.generate_html_report(
            input_file=input_file,
            output_file=output_file
        )
        
        processing_time = time.time() - start_time
        PROCESSING_TIME.observe(processing_time)
        
        return jsonify({
            "status": "success",
            "processing_time": processing_time,
            "result": result
        })
    
    except Exception as e:
        PROCESSING_ERRORS.inc()
        logger.error(f"Error during report generation: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Gibt aktuelle Statistiken zurück"""
    memory_usage = get_memory_usage()
    MEMORY_USAGE.set(memory_usage)
    
    return jsonify({
        "memory_usage": memory_usage,
        "max_workers": MAX_WORKERS,
        "min_chunk_size": MIN_CHUNK_SIZE,
        "max_chunk_size": MAX_CHUNK_SIZE,
        "memory_target": MEMORY_TARGET,
        "active_workers": pipeline.get_active_workers() if hasattr(pipeline, 'get_active_workers') else 0
    })

if __name__ == '__main__':
    # Start Prometheus metrics server
    start_http_server(9090)
    logger.info(f"Prometheus metrics server started on port 9090")
    
    # Start Flask app
    logger.info(f"Starting processor service with MAX_WORKERS={MAX_WORKERS}")
    app.run(host='0.0.0.0', port=5000) 