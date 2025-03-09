import os
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.semantic.bookmark_embeddings import BookmarkEmbeddings
from scripts.semantic.bookmark_similarity import BookmarkSimilarity

# Cache the embedding model loading
@st.cache_resource
def load_embedding_model(model_path):
    """Load the embedding model from a file."""
    try:
        model = BookmarkEmbeddings()
        model.load(model_path)
        return model
    except Exception as e:
        st.error(f"Error loading embedding model: {str(e)}")
        return None

# Cache the similarity model initialization
@st.cache_resource
def get_similarity_model(embedding_model):
    """Initialize the similarity model from embeddings."""
    if embedding_model and embedding_model.is_initialized():
        return BookmarkSimilarity(embedding_model)
    return None

# Cache the cluster data loading
@st.cache_data
def load_cluster_data(cluster_file):
    """Load cluster data from a file."""
    try:
        with open(cluster_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading cluster data: {str(e)}")
        return {}

# Cache the embedding stats loading
@st.cache_data
def load_embedding_stats(stats_file):
    """Load embedding statistics from a file."""
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading embedding stats: {str(e)}")
        return {}

def render_semantic_tab():
    """Render the semantic analysis tab in the dashboard."""
    st.header("Semantic Analysis")
    
    # Sidebar for model selection and controls
    with st.sidebar:
        st.subheader("Semantic Analysis Controls")
        
        # Model selection
        model_path = st.text_input(
            "Embedding Model Path",
            value="data/embeddings/bookmark_embeddings.pkl",
            help="Path to the saved embedding model file"
        )
        
        # Cluster settings
        cluster_file = st.text_input(
            "Cluster Data Path",
            value="data/embeddings/bookmark_clusters.json",
            help="Path to the saved cluster data file"
        )
        
        stats_file = st.text_input(
            "Embedding Stats Path",
            value="data/embeddings/embedding_stats.json",
            help="Path to the saved embedding statistics file"
        )
        
        # Load test data button
        if st.button("Load Test Data"):
            # This is just a placeholder - in a real implementation,
            # you would load some test data here
            st.session_state['use_test_data'] = True
            st.success("Test data loaded!")
    
    # Check if model files exist
    model_exists = os.path.exists(model_path)
    clusters_exist = os.path.exists(cluster_file)
    stats_exist = os.path.exists(stats_file)
    
    if not model_exists:
        st.warning(f"Embedding model file not found: {model_path}")
    
    if not clusters_exist:
        st.warning(f"Cluster data file not found: {cluster_file}")
    
    if not stats_exist:
        st.warning(f"Embedding stats file not found: {stats_file}")
    
    # Load embedding model if it exists
    embedding_model = None
    if model_exists:
        embedding_model = load_embedding_model(model_path)
    
    # Load similarity model if embedding model is loaded
    similarity_model = None
    if embedding_model and embedding_model.is_initialized():
        similarity_model = get_similarity_model(embedding_model)
        st.success(f"Loaded embeddings for {embedding_model.get_count()} bookmarks")
    
    # Load cluster data if it exists
    clusters = {}
    if clusters_exist:
        clusters = load_cluster_data(cluster_file)
    
    # Load embedding stats if they exist
    embedding_stats = {}
    if stats_exist:
        embedding_stats = load_embedding_stats(stats_file)
    
    # Create tabs for different semantic features
    tab1, tab2, tab3, tab4 = st.tabs([
        "Overview", "Search", "Similarity", "Clusters"
    ])
    
    # Tab 1: Overview
    with tab1:
        st.subheader("Embedding Overview")
        
        if embedding_model and embedding_model.is_initialized():
            # Display basic statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Bookmarks", embedding_model.get_count())
            
            with col2:
                st.metric("Embedding Dimension", embedding_model.get_dimension())
            
            with col3:
                st.metric("Clusters", len(clusters) if clusters else 0)
            
            # Display embedding stats if available
            if embedding_stats:
                st.subheader("Cluster Statistics")
                
                # Create a DataFrame for cluster statistics
                if 'clusters' in embedding_stats:
                    cluster_stats = []
                    for label, data in embedding_stats['clusters'].items():
                        cluster_stats.append({
                            'Cluster': label,
                            'Size': data['size']
                        })
                    
                    if cluster_stats:
                        df = pd.DataFrame(cluster_stats)
                        
                        # Create a bar chart of cluster sizes
                        fig = px.bar(
                            df, 
                            x='Cluster', 
                            y='Size',
                            title='Bookmark Distribution by Cluster',
                            labels={'Size': 'Number of Bookmarks', 'Cluster': 'Cluster Label'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No embedding model loaded. Please load an embedding model to see statistics.")
    
    # Tab 2: Search
    with tab2:
        st.subheader("Semantic Search")
        
        if similarity_model:
            query = st.text_input("Enter search query")
            top_k = st.slider("Number of results", 5, 50, 10)
            
            if query:
                with st.spinner("Searching..."):
                    results = similarity_model.search_by_text(query, top_k=top_k)
                
                st.subheader(f"Search Results for: '{query}'")
                
                for i, (url, score) in enumerate(results):
                    with st.expander(f"{i+1}. Score: {score:.4f} - {url}"):
                        st.markdown(f"[Open URL]({url})")
                        st.progress(score)
        else:
            st.info("No similarity model loaded. Please load an embedding model to enable search.")
    
    # Tab 3: Similarity
    with tab3:
        st.subheader("Find Similar Bookmarks")
        
        if similarity_model:
            # Get all URLs
            urls = embedding_model.get_urls()
            
            # Create a selectbox for URL selection
            # Use a text input with autocomplete for better UX with many URLs
            selected_url = st.selectbox(
                "Select a bookmark",
                options=urls,
                format_func=lambda x: x[:50] + "..." if len(x) > 50 else x
            )
            
            top_k = st.slider("Number of similar bookmarks", 5, 20, 5, key="similar_slider")
            
            if selected_url:
                with st.spinner("Finding similar bookmarks..."):
                    similar = similarity_model.find_similar_bookmarks(selected_url, top_k=top_k)
                
                st.subheader(f"Bookmarks similar to:")
                st.markdown(f"[{selected_url}]({selected_url})")
                
                for i, (url, score) in enumerate(similar):
                    if url != selected_url:  # Skip the selected URL itself
                        with st.expander(f"{i}. Score: {score:.4f} - {url}"):
                            st.markdown(f"[Open URL]({url})")
                            st.progress(score)
        else:
            st.info("No similarity model loaded. Please load an embedding model to find similar bookmarks.")
    
    # Tab 4: Clusters
    with tab4:
        st.subheader("Bookmark Clusters")
        
        if clusters:
            # Sort clusters by size
            sorted_clusters = sorted(
                clusters.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
            
            # Display clusters
            for label, urls in sorted_clusters:
                with st.expander(f"{label} ({len(urls)} bookmarks)"):
                    # Display a sample of URLs
                    for i, url in enumerate(urls[:10]):  # Show only first 10
                        st.markdown(f"{i+1}. [{url}]({url})")
                    
                    # Show a "See more" button if there are more than 10 URLs
                    if len(urls) > 10:
                        if st.button(f"See all {len(urls)} bookmarks", key=f"see_more_{label}"):
                            for i, url in enumerate(urls):
                                st.markdown(f"{i+1}. [{url}]({url})")
        else:
            st.info("No cluster data loaded. Please load cluster data to view bookmark clusters.")

if __name__ == "__main__":
    st.set_page_config(
        page_title="Bookmark Semantic Analysis",
        page_icon="📚",
        layout="wide"
    )
    
    render_semantic_tab() 