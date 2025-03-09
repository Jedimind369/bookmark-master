#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Streamlit-Dashboard für die Anzeige der in der SQLite-Datenbank gespeicherten Daten.

Bietet eine interaktive Oberfläche zum Durchsuchen und Analysieren der Bookmarks,
einschließlich Visualisierungen und Statistiken.
"""

import os
import sys
import json
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
import plotly.express as px
from pathlib import Path
import matplotlib.pyplot as plt
import pickle
from sklearn.manifold import TSNE
from datetime import datetime

# Füge das Projektverzeichnis zum Pfad hinzu
sys.path.append(str(Path(__file__).parent.parent.parent))

# Importiere die Datenbankklasse
from scripts.database.db_operations import BookmarkDB

# Datenbank-Pfad
DB_PATH = "data/database/bookmarks.db"

# Konfiguriere die Streamlit-Seite
st.set_page_config(
    page_title="Bookmark Explorer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=300)
def get_pages_from_db():
    """
    Holt alle Seiten aus der Datenbank.
    
    Returns:
        pd.DataFrame: DataFrame mit Seitendaten
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # SQL-Abfrage zum Abrufen aller Seiten mit Cluster-Informationen
        query = """
            SELECT p.*, c.cluster_id, c.model
            FROM pages p
            LEFT JOIN clusters c ON p.url = c.url
            ORDER BY p.scrape_time DESC
        """
        
        # Lade die Daten in einen DataFrame
        df = pd.read_sql_query(query, conn)
        
        # Schließe die Verbindung
        conn.close()
        
        # Konvertiere die Spalte "tags" von JSON-String zu Liste
        if 'tags' in df.columns:
            df['tags'] = df['tags'].apply(lambda x: json.loads(x) if isinstance(x, str) and x.strip() else [])
        
        # Fülle NaN-Werte in der cluster_id-Spalte mit -1
        if 'cluster_id' in df.columns:
            df['cluster_id'] = df['cluster_id'].fillna(-1).astype(int)
        
        return df
        
    except sqlite3.Error as e:
        st.error(f"Fehler beim Abrufen der Seiten aus der Datenbank: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_embeddings_from_file(file_path="data/embeddings/hybrid_run/bookmark_embeddings.pkl"):
    """
    Lädt Embeddings aus einer Pickle-Datei.
    
    Args:
        file_path: Pfad zur Pickle-Datei
        
    Returns:
        dict: Dictionary mit URLs als Schlüssel und Embeddings als Werte
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                embeddings = pickle.load(f)
            return embeddings
        else:
            return {}
    except Exception as e:
        st.error(f"Fehler beim Laden der Embeddings: {str(e)}")
        return {}

@st.cache_data(ttl=300)
def get_tsne_data(file_path="data/embeddings/hybrid_run/bookmark_tsne.json"):
    """
    Lädt t-SNE-Daten aus einer JSON-Datei.
    
    Args:
        file_path: Pfad zur JSON-Datei
        
    Returns:
        pd.DataFrame: DataFrame mit t-SNE-Daten
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                tsne_data = json.load(f)
            return pd.DataFrame(tsne_data)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Fehler beim Laden der t-SNE-Daten: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def calculate_cluster_statistics(df):
    """
    Berechnet Statistiken für die Cluster.
    
    Args:
        df: DataFrame mit Seitendaten
        
    Returns:
        pd.DataFrame: DataFrame mit Cluster-Statistiken
    """
    if 'cluster_id' not in df.columns or df.empty:
        return pd.DataFrame()
    
    # Zähle die Anzahl der Seiten pro Cluster
    cluster_counts = df['cluster_id'].value_counts().reset_index()
    cluster_counts.columns = ['cluster_id', 'count']
    
    # Berechne die 3 häufigsten Titel pro Cluster
    cluster_titles = df.groupby('cluster_id')['title'].apply(lambda x: ', '.join(x.dropna().head(3))).reset_index()
    
    # Führe die Ergebnisse zusammen
    cluster_stats = pd.merge(cluster_counts, cluster_titles, on='cluster_id')
    
    return cluster_stats

@st.cache_data(ttl=300)
def calculate_scraper_statistics(df):
    """
    Berechnet Statistiken für die Scraper.
    
    Args:
        df: DataFrame mit Seitendaten
        
    Returns:
        pd.DataFrame: DataFrame mit Scraper-Statistiken
    """
    if 'scraper_used' not in df.columns or df.empty:
        return pd.DataFrame()
    
    # Zähle die Anzahl der Seiten pro Scraper
    scraper_counts = df['scraper_used'].value_counts().reset_index()
    scraper_counts.columns = ['scraper', 'count']
    
    return scraper_counts

@st.cache_data(ttl=300)
def generate_tsne_visualization(df, tsne_df):
    """
    Generiert eine t-SNE-Visualisierung.
    
    Args:
        df: DataFrame mit Seitendaten
        tsne_df: DataFrame mit t-SNE-Daten
        
    Returns:
        alt.Chart: Altair-Chart mit t-SNE-Visualisierung
    """
    if tsne_df.empty or df.empty:
        return None
    
    # Führe die Daten zusammen
    merged_df = pd.merge(tsne_df, df[['url', 'title', 'cluster_id']], on='url', how='left')
    
    # Erstelle die Visualisierung
    chart = alt.Chart(merged_df).mark_circle(size=60).encode(
        x='x:Q',
        y='y:Q',
        color=alt.Color('cluster_id:N', scale=alt.Scale(scheme='category20')),
        tooltip=['title', 'url', 'cluster_id']
    ).properties(
        width=700,
        height=500,
        title='t-SNE-Visualisierung der Bookmarks'
    ).interactive()
    
    return chart

def generate_cluster_visualization(df, cluster_stats):
    """
    Generiert eine Visualisierung der Cluster.
    
    Args:
        df: DataFrame mit Seitendaten
        cluster_stats: DataFrame mit Cluster-Statistiken
        
    Returns:
        px.treemap: Plotly-Treemap mit Cluster-Visualisierung
    """
    if cluster_stats.empty or df.empty:
        return None
    
    # Erstelle die Treemap
    fig = px.treemap(
        cluster_stats,
        path=['cluster_id'],
        values='count',
        hover_data=['title'],
        color='cluster_id',
        color_continuous_scale='RdBu',
        title='Cluster-Verteilung der Bookmarks'
    )
    
    # Passe das Layout an
    fig.update_layout(
        margin=dict(t=50, l=25, r=25, b=25),
        height=500
    )
    
    return fig

def main():
    """Hauptfunktion."""
    # Seitentitel
    st.title("📚 Bookmark Explorer")
    
    # Lade die Daten
    df = get_pages_from_db()
    tsne_df = get_tsne_data()
    embeddings = get_embeddings_from_file()
    
    # Sidebar mit Filter-Optionen
    st.sidebar.title("Filter & Einstellungen")
    
    # Überprüfe, ob Daten vorhanden sind
    if df.empty:
        st.error("Keine Daten in der Datenbank gefunden.")
        return
    
    # Statistiken
    st.sidebar.subheader("Statistiken")
    st.sidebar.info(f"""
        **Anzahl Bookmarks:** {len(df)}  
        **Cluster:** {df['cluster_id'].nunique() if 'cluster_id' in df.columns else 0}  
        **Ordner:** {df['folder'].nunique() if 'folder' in df.columns else 0}  
        **ScrapingBee:** {(df['scraper_used'] == 'scrapingbee').sum() if 'scraper_used' in df.columns else 0}  
        **Fallback:** {(df['scraper_used'] == 'fallback').sum() if 'scraper_used' in df.columns else 0}  
        **Cache:** {(df['scraper_used'] == 'cached').sum() if 'scraper_used' in df.columns else 0}  
    """)
    
    # Filter-Optionen
    st.sidebar.subheader("Filter")
    
    # Filter nach Cluster
    if 'cluster_id' in df.columns:
        cluster_options = ["Alle"] + sorted(df['cluster_id'].dropna().unique().astype(int).astype(str).tolist())
        selected_cluster = st.sidebar.selectbox("Cluster", cluster_options)
    else:
        selected_cluster = "Alle"
    
    # Filter nach Ordner
    if 'folder' in df.columns:
        folder_options = ["Alle"] + sorted(df['folder'].dropna().unique().tolist())
        selected_folder = st.sidebar.selectbox("Ordner", folder_options)
    else:
        selected_folder = "Alle"
    
    # Filter nach Scraper
    if 'scraper_used' in df.columns:
        scraper_options = ["Alle"] + sorted(df['scraper_used'].dropna().unique().tolist())
        selected_scraper = st.sidebar.selectbox("Scraper", scraper_options)
    else:
        selected_scraper = "Alle"
    
    # Textsuche
    search_query = st.sidebar.text_input("Suchbegriff")
    
    # Anwenden der Filter
    filtered_df = df.copy()
    
    if selected_cluster != "Alle" and 'cluster_id' in df.columns:
        filtered_df = filtered_df[filtered_df['cluster_id'].astype(str) == selected_cluster]
    
    if selected_folder != "Alle" and 'folder' in df.columns:
        filtered_df = filtered_df[filtered_df['folder'] == selected_folder]
    
    if selected_scraper != "Alle" and 'scraper_used' in df.columns:
        filtered_df = filtered_df[filtered_df['scraper_used'] == selected_scraper]
    
    if search_query:
        filtered_df = filtered_df[
            filtered_df['title'].fillna('').str.contains(search_query, case=False) |
            filtered_df['description'].fillna('').str.contains(search_query, case=False) |
            filtered_df['url'].fillna('').str.contains(search_query, case=False) |
            filtered_df['article_text'].fillna('').str.contains(search_query, case=False)
        ]
    
    # Zeige die Anzahl der gefilterten Bookmarks
    st.sidebar.info(f"Gefundene Bookmarks: {len(filtered_df)}")
    
    # Exportieren der gefilterten Daten
    if st.sidebar.button("Exportieren (CSV)"):
        csv = filtered_df.to_csv(index=False)
        st.sidebar.download_button(
            label="Download CSV",
            data=csv,
            file_name="filtered_bookmarks.csv",
            mime="text/csv"
        )
    
    # Main-Bereich mit Tabs
    tab1, tab2, tab3 = st.tabs(["Bookmarks", "Visualisierungen", "Analysen"])
    
    # Tab 1: Bookmarks
    with tab1:
        # Anzeige der gefilterten Bookmarks
        st.subheader(f"Bookmarks ({len(filtered_df)})")
        
        # Sortieren
        sort_options = {
            "Neueste zuerst": "scrape_time",
            "Älteste zuerst": "scrape_time (aufsteigend)",
            "Titel (A-Z)": "title",
            "Titel (Z-A)": "title (absteigend)",
            "Cluster": "cluster_id"
        }
        sort_by = st.selectbox("Sortieren nach", list(sort_options.keys()))
        
        # Sortiere die gefilterten Daten
        sort_column = sort_options[sort_by].split(" ")[0]
        ascending = "aufsteigend" in sort_options[sort_by]
        filtered_df = filtered_df.sort_values(by=sort_column, ascending=ascending)
        
        # Zeige die Bookmarks an
        for i, (_, row) in enumerate(filtered_df.iterrows()):
            with st.expander(f"{row.get('title', 'Kein Titel')}"):
                # URL mit Link
                st.markdown(f"**URL:** [{row.get('url', '')}]({row.get('url', '')})")
                
                # Beschreibung
                if row.get('description'):
                    st.markdown(f"**Beschreibung:** {row.get('description', '')}")
                
                # Metadaten
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Ordner:** {row.get('folder', '')}")
                with col2:
                    st.markdown(f"**Cluster:** {row.get('cluster_id', '')}")
                with col3:
                    st.markdown(f"**Scraper:** {row.get('scraper_used', '')}")
                
                # Zeige den Artikeltext an, wenn vorhanden
                if row.get('article_text'):
                    with st.expander("Artikeltext anzeigen"):
                        st.text_area("", row.get('article_text', ''), height=300)
    
    # Tab 2: Visualisierungen
    with tab2:
        st.subheader("Visualisierungen")
        
        # t-SNE-Visualisierung
        st.markdown("#### t-SNE-Visualisierung")
        tsne_chart = generate_tsne_visualization(df, tsne_df)
        if tsne_chart:
            st.altair_chart(tsne_chart, use_container_width=True)
        else:
            st.info("Keine t-SNE-Daten verfügbar.")
        
        # Berechne Cluster-Statistiken
        cluster_stats = calculate_cluster_statistics(df)
        
        # Cluster-Visualisierung
        st.markdown("#### Cluster-Verteilung")
        treemap = generate_cluster_visualization(df, cluster_stats)
        if treemap:
            st.plotly_chart(treemap, use_container_width=True)
        else:
            st.info("Keine Cluster-Daten verfügbar.")
        
        # Scraper-Statistiken
        st.markdown("#### Scraper-Verteilung")
        scraper_stats = calculate_scraper_statistics(df)
        if not scraper_stats.empty:
            # Erstelle ein Balkendiagramm
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(scraper_stats['scraper'], scraper_stats['count'])
            ax.set_title('Verteilung der Scraper')
            ax.set_xlabel('Scraper')
            ax.set_ylabel('Anzahl')
            
            # Füge Beschriftungen hinzu
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{height:.0f}', ha='center', va='bottom')
            
            st.pyplot(fig)
        else:
            st.info("Keine Scraper-Daten verfügbar.")
    
    # Tab 3: Analysen
    with tab3:
        st.subheader("Analysen")
        
        # Folder-Verteilung
        if 'folder' in df.columns:
            st.markdown("#### Ordner-Verteilung")
            folder_counts = df['folder'].value_counts()
            if not folder_counts.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                folder_counts.plot(kind='pie', ax=ax, autopct='%1.1f%%')
                ax.set_title('Verteilung der Ordner')
                ax.set_ylabel('')
                st.pyplot(fig)
            else:
                st.info("Keine Ordner-Daten verfügbar.")
        
        # Zeitliche Verteilung der Bookmarks
        if 'added' in df.columns:
            st.markdown("#### Zeitliche Verteilung")
            # Konvertiere das Datum in ein Datetime-Objekt
            df['added_date'] = pd.to_datetime(df['added'])
            
            # Gruppiere nach Jahr und Monat
            df['year_month'] = df['added_date'].dt.to_period('M')
            monthly_counts = df.groupby('year_month').size().reset_index(name='count')
            monthly_counts['year_month_str'] = monthly_counts['year_month'].astype(str)
            
            # Erstelle ein Liniendiagramm
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(monthly_counts['year_month_str'], monthly_counts['count'], marker='o')
            ax.set_title('Zeitliche Verteilung der Bookmarks')
            ax.set_xlabel('Monat')
            ax.set_ylabel('Anzahl')
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
        
        # Wort-Cloud
        st.markdown("#### Häufige Wörter in Beschreibungen")
        try:
            from wordcloud import WordCloud
            
            # Kombiniere alle Beschreibungen
            all_descriptions = ' '.join(df['description'].dropna().tolist())
            
            if all_descriptions:
                # Erstelle eine Wort-Cloud
                wordcloud = WordCloud(width=800, height=400, background_color='white', contour_width=1, contour_color='steelblue').generate(all_descriptions)
                
                # Zeige die Wort-Cloud an
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis('off')
                st.pyplot(fig)
            else:
                st.info("Keine Beschreibungen für die Wort-Cloud verfügbar.")
        except ImportError:
            st.warning("WordCloud-Paket nicht installiert. Installieren Sie es mit 'pip install wordcloud'.")
    
    # Footer
    st.markdown("---")
    st.markdown(f"Generiert am: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

if __name__ == "__main__":
    main() 