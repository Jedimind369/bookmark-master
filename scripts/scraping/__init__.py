"""
scraping

Ein Modul zur effizienten und robusten Verarbeitung großer Mengen von URLs
mit der Zyte API und KI-basierter Inhaltsanalyse.
"""

from .zyte_scraper import ZyteScraper, scrape_urls
from .content_analyzer import ContentAnalyzer
from .batch_processor import BatchProcessor, process_large_url_list
from .settings import (
    ZYTE_API_KEY,
    ZYTE_API_ENDPOINT,
    ZYTE_API_SETTINGS,
    BATCH_SIZE,
    MAX_CONCURRENT_REQUESTS,
    DATA_DIR,
    LOG_DIR
)

__all__ = [
    'ZyteScraper',
    'scrape_urls',
    'ContentAnalyzer',
    'BatchProcessor',
    'process_large_url_list',
    'ZYTE_API_KEY',
    'ZYTE_API_ENDPOINT',
    'ZYTE_API_SETTINGS',
    'BATCH_SIZE',
    'MAX_CONCURRENT_REQUESTS',
    'DATA_DIR',
    'LOG_DIR'
] 