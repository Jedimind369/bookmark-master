#!/usr/bin/env python3

"""
Semantic-Modul für das Bookmark-Master-Projekt.

Dieses Modul implementiert semantische Verbindungen zwischen Lesezeichen
mit Hilfe von Vektor-Embeddings und Ähnlichkeitssuche.
"""

from .vector_store import BookmarkVectorStore
from .visualize_connections import BookmarkVisualizer, load_test_data

__all__ = ['BookmarkVectorStore', 'BookmarkVisualizer', 'load_test_data'] 