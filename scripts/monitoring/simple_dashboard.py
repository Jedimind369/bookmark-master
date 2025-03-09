#!/usr/bin/env python3
"""
Einfaches Streamlit-Dashboard für die Anzeige und Suche von Lesezeichen.

Dieses Skript erstellt ein interaktives Web-Dashboard zur Anzeige und Suche von Lesezeichen.

Verwendung:
    streamlit run scripts/monitoring/simple_dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
import sys
import plotly.express as px
from collections import Counter

# Füge das Hauptverzeichnis zum Pfad hinzu, um Importe zu ermöglichen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import der semantischen Analyse-Komponenten
try:
    from scripts.semantic.bookmark_embeddings import BookmarkEmbeddings
    from scripts.semantic.bookmark_similarity import BookmarkSimilarity
    semantic_imports_successful = True
except ImportError:
    semantic_imports_successful = False

# Seitenkonfiguration
st.set_page_config(
    page_title="Bookmark Explorer",
    page_icon="🔖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS für besseres Aussehen
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    .bookmark-card {
        background-color: #f9f9f9;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-left: 5px solid #4CAF50;
    }
    .bookmark-card h4 {
        margin-top: 0;
        margin-bottom: 0.5rem;
    }
    .folder-tag {
        background-color: #e0e0e0;
        border-radius: 0.25rem;
        padding: 0.2rem 0.5rem;
        margin-right: 0.5rem;
        font-size: 0.8rem;
    }
    .date-tag {
        color: #666;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Funktionen zum Laden der Daten
@st.cache_data(ttl=60)  # Cache für 60 Sekunden
def load_bookmarks(file_path):
    """Lädt die Lesezeichen aus einer JSON-Datei."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            bookmarks = json.load(f)
        return bookmarks
    except Exception as e:
        st.error(f"Fehler beim Laden der Lesezeichen: {str(e)}")
        return []

@st.cache_data
def get_bookmark_stats(bookmarks):
    """Berechnet Statistiken über die Lesezeichen."""
    if not bookmarks:
        return {}
    
    # Zähle die Anzahl der Lesezeichen pro Ordner
    folder_counts = Counter([b.get('folder', 'Unbekannt') for b in bookmarks])
    
    # Extrahiere die Jahre aus den Datumsangaben
    years = []
    for b in bookmarks:
        if 'added' in b and b['added']:
            try:
                year = b['added'].split('-')[0]
                years.append(year)
            except:
                pass
    year_counts = Counter(years)
    
    return {
        'total': len(bookmarks),
        'folders': dict(folder_counts.most_common()),
        'years': dict(sorted(year_counts.items())),
        'unique_folders': len(folder_counts)
    }

# Cache für das Embedding-Modell
@st.cache_resource
def load_embedding_model(model_path):
    """Lädt das Embedding-Modell aus einer Datei."""
    if not semantic_imports_successful:
        return None
    
    try:
        model = BookmarkEmbeddings()
        model.load(model_path)
        return model
    except Exception as e:
        st.error(f"Fehler beim Laden des Embedding-Modells: {str(e)}")
        return None

# Cache für das Similarity-Modell
@st.cache_resource
def get_similarity_model(embedding_model):
    """Initialisiert das Similarity-Modell aus den Embeddings."""
    if not semantic_imports_successful or not embedding_model:
        return None
    
    if embedding_model.is_initialized():
        return BookmarkSimilarity(embedding_model)
    return None

# Hauptfunktion
def main():
    st.title("🔖 Bookmark Explorer")
    
    # Sidebar für die Steuerung
    with st.sidebar:
        st.header("Einstellungen")
        
        # Pfad zur Lesezeichen-Datei
        bookmarks_file = st.text_input(
            "Pfad zur Lesezeichen-Datei",
            value="data/enriched/fully_enhanced.json"
        )
        
        # Pfad zum Embedding-Modell
        embedding_model_path = st.text_input(
            "Pfad zum Embedding-Modell",
            value="data/embeddings/enhanced/bookmark_embeddings.pkl"
        )
        
        # Lade die Daten
        if st.button("Daten laden"):
            st.session_state['bookmarks_loaded'] = True
    
    # Prüfe, ob die Daten geladen werden sollen
    if 'bookmarks_loaded' not in st.session_state:
        st.session_state['bookmarks_loaded'] = False
    
    # Lade die Daten, wenn der Button geklickt wurde
    if st.session_state['bookmarks_loaded']:
        # Lade die Lesezeichen
        bookmarks = load_bookmarks(bookmarks_file)
        
        if not bookmarks:
            st.error(f"Keine Lesezeichen gefunden in: {bookmarks_file}")
            return
        
        # Lade das Embedding-Modell
        embedding_model = None
        similarity_model = None
        
        if os.path.exists(embedding_model_path):
            embedding_model = load_embedding_model(embedding_model_path)
            if embedding_model and embedding_model.is_initialized():
                similarity_model = get_similarity_model(embedding_model)
                st.sidebar.success(f"Embeddings für {embedding_model.get_count()} Lesezeichen geladen")
        
        # Erstelle Tabs für verschiedene Funktionen
        tab1, tab2, tab3, tab4 = st.tabs([
            "Übersicht", "Suche", "Semantische Suche", "Ordner-Explorer"
        ])
        
        # Tab 1: Übersicht
        with tab1:
            st.header("Übersicht")
            
            # Berechne Statistiken
            stats = get_bookmark_stats(bookmarks)
            
            # Zeige Metriken
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Anzahl Lesezeichen", stats['total'])
            
            with col2:
                st.metric("Anzahl Ordner", stats['unique_folders'])
            
            with col3:
                if embedding_model:
                    st.metric("Embedding-Dimension", embedding_model.get_dimension())
                else:
                    st.metric("Embedding-Status", "Nicht geladen")
            
            # Zeige Diagramme
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Top 10 Ordner")
                top_folders = dict(sorted(stats['folders'].items(), key=lambda x: x[1], reverse=True)[:10])
                fig = px.bar(
                    x=list(top_folders.keys()),
                    y=list(top_folders.values()),
                    labels={'x': 'Ordner', 'y': 'Anzahl Lesezeichen'},
                    title="Top 10 Ordner nach Anzahl der Lesezeichen"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Lesezeichen pro Jahr")
                if stats['years']:
                    fig = px.bar(
                        x=list(stats['years'].keys()),
                        y=list(stats['years'].values()),
                        labels={'x': 'Jahr', 'y': 'Anzahl Lesezeichen'},
                        title="Lesezeichen pro Jahr"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Keine Jahresinformationen verfügbar")
        
        # Tab 2: Suche
        with tab2:
            st.header("Lesezeichen-Suche")
            
            # Suchoptionen
            search_query = st.text_input("Suchbegriff")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                search_in_title = st.checkbox("In Titel suchen", value=True)
            
            with col2:
                search_in_url = st.checkbox("In URL suchen", value=True)
            
            with col3:
                search_in_folder = st.checkbox("In Ordner suchen", value=False)
            
            # Führe die Suche durch
            if search_query:
                search_results = []
                
                for bookmark in bookmarks:
                    match = False
                    
                    if search_in_title and 'title' in bookmark:
                        if search_query.lower() in bookmark['title'].lower():
                            match = True
                    
                    if not match and search_in_url and 'url' in bookmark:
                        if search_query.lower() in bookmark['url'].lower():
                            match = True
                    
                    if not match and search_in_folder and 'folder' in bookmark:
                        if search_query.lower() in bookmark['folder'].lower():
                            match = True
                    
                    if match:
                        search_results.append(bookmark)
                
                # Zeige die Ergebnisse
                st.subheader(f"Suchergebnisse ({len(search_results)} Treffer)")
                
                if search_results:
                    for i, bookmark in enumerate(search_results[:100]):  # Begrenze auf 100 Ergebnisse
                        with st.expander(f"{i+1}. {bookmark.get('title', bookmark.get('url', 'Unbekannt'))}"):
                            st.markdown(f"**URL:** [{bookmark.get('url', 'Keine URL')}]({bookmark.get('url', '#')})")
                            st.markdown(f"**Ordner:** {bookmark.get('folder', 'Kein Ordner')}")
                            if 'description' in bookmark and bookmark['description']:
                                st.markdown(f"**Beschreibung:** {bookmark['description']}")
                            if 'tags' in bookmark and bookmark['tags']:
                                st.markdown(f"**Tags:** {', '.join(bookmark['tags']) if isinstance(bookmark['tags'], list) else bookmark['tags']}")
                            if 'added' in bookmark:
                                st.markdown(f"**Hinzugefügt am:** {bookmark.get('added', 'Unbekannt')}")
                else:
                    st.info("Keine Ergebnisse gefunden")
            else:
                st.info("Gib einen Suchbegriff ein, um Lesezeichen zu finden")
        
        # Tab 3: Semantische Suche
        with tab3:
            st.header("Semantische Suche")
            
            if similarity_model:
                # Semantische Suche
                semantic_query = st.text_input("Semantische Suchanfrage")
                top_k = st.slider("Anzahl der Ergebnisse", 5, 50, 10)
                
                if semantic_query:
                    with st.spinner("Suche läuft..."):
                        results = similarity_model.search_by_text(semantic_query, top_k=top_k)
                    
                    st.subheader(f"Suchergebnisse für: '{semantic_query}'")
                    
                    # Finde die vollständigen Lesezeichen-Informationen für die URLs
                    url_to_bookmark = {b['url']: b for b in bookmarks if 'url' in b}
                    
                    for i, (url, score) in enumerate(results):
                        bookmark = url_to_bookmark.get(url, {'url': url})
                        
                        with st.expander(f"{i+1}. Score: {score:.4f} - {bookmark.get('title', url)}"):
                            st.markdown(f"**URL:** [{url}]({url})")
                            st.markdown(f"**Ordner:** {bookmark.get('folder', 'Kein Ordner')}")
                            if 'description' in bookmark and bookmark['description']:
                                st.markdown(f"**Beschreibung:** {bookmark['description']}")
                            if 'tags' in bookmark and bookmark['tags']:
                                st.markdown(f"**Tags:** {', '.join(bookmark['tags']) if isinstance(bookmark['tags'], list) else bookmark['tags']}")
                            if 'added' in bookmark:
                                st.markdown(f"**Hinzugefügt am:** {bookmark.get('added', 'Unbekannt')}")
                            st.progress(score)
            else:
                st.info("Kein Similarity-Modell geladen. Bitte lade ein Embedding-Modell, um die semantische Suche zu aktivieren.")
        
        # Tab 4: Ordner-Explorer
        with tab4:
            st.header("Ordner-Explorer")
            
            # Extrahiere alle Ordner
            all_folders = sorted(set([b.get('folder', 'Unbekannt') for b in bookmarks]))
            
            # Wähle einen Ordner aus
            selected_folder = st.selectbox("Ordner auswählen", all_folders)
            
            if selected_folder:
                # Filtere Lesezeichen nach Ordner
                folder_bookmarks = [b for b in bookmarks if b.get('folder') == selected_folder]
                
                st.subheader(f"Lesezeichen in '{selected_folder}' ({len(folder_bookmarks)})")
                
                # Zeige die Lesezeichen
                for i, bookmark in enumerate(folder_bookmarks):
                    with st.expander(f"{i+1}. {bookmark.get('title', bookmark.get('url', 'Unbekannt'))}"):
                        st.markdown(f"**URL:** [{bookmark.get('url', 'Keine URL')}]({bookmark.get('url', '#')})")
                        st.markdown(f"**Ordner:** {bookmark.get('folder', 'Kein Ordner')}")
                        if 'description' in bookmark and bookmark['description']:
                            st.markdown(f"**Beschreibung:** {bookmark['description']}")
                        if 'tags' in bookmark and bookmark['tags']:
                            st.markdown(f"**Tags:** {', '.join(bookmark['tags']) if isinstance(bookmark['tags'], list) else bookmark['tags']}")
                        if 'added' in bookmark:
                            st.markdown(f"**Hinzugefügt am:** {bookmark.get('added', 'Unbekannt')}")
    else:
        st.info("Klicke auf 'Daten laden', um deine Lesezeichen anzuzeigen")

if __name__ == "__main__":
    main() 