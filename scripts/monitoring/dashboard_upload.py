import os
import sys
import json
import streamlit as st
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.scraping.bookmark_parser import BookmarkParser
from scripts.processing.process_bookmarks import process_partial_bookmarks

def main():
    st.set_page_config(
        page_title="Bookmark Processor",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("Bookmark Processor")
    st.write("Lade deine HTML-Lesezeichendatei hoch und verarbeite sie.")
    
    # Datei-Upload
    uploaded_file = st.file_uploader("Wähle eine HTML-Lesezeichendatei", type=["html"])
    
    if uploaded_file is not None:
        # Speichere die hochgeladene Datei temporär
        temp_path = os.path.join("data", "uploads", uploaded_file.name)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"Datei erfolgreich hochgeladen: {uploaded_file.name}")
        
        # Verarbeitungsoptionen
        st.subheader("Verarbeitungsoptionen")
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_index = st.number_input("Startindex", min_value=0, value=0)
            batch_size = st.number_input("Batch-Größe", min_value=10, max_value=100, value=50)
        
        with col2:
            end_index = st.number_input("Endindex (0 = bis zum Ende)", min_value=0, value=200)
            if end_index == 0:
                end_index = None
        
        output_dir = os.path.join("data", "processed", "dashboard_upload")
        
        # Verarbeitungsbutton
        if st.button("Verarbeiten"):
            with st.spinner("Verarbeite Lesezeichen..."):
                try:
                    valid_bookmarks, invalid_bookmarks, stats = process_partial_bookmarks(
                        temp_path,
                        output_dir,
                        start_index=start_index,
                        end_index=end_index,
                        batch_size=batch_size
                    )
                    
                    st.success("Verarbeitung abgeschlossen!")
                    
                    # Zeige Statistiken
                    st.subheader("Verarbeitungsstatistiken")
                    st.json(stats)
                    
                    # Zeige Beispiele für gültige Lesezeichen
                    if valid_bookmarks:
                        st.subheader("Beispiele für gültige Lesezeichen")
                        st.json(valid_bookmarks[:5])
                    
                    # Zeige Beispiele für ungültige Lesezeichen
                    if invalid_bookmarks:
                        st.subheader("Beispiele für ungültige Lesezeichen")
                        st.json(invalid_bookmarks[:5])
                    
                    # Download-Buttons
                    st.subheader("Ergebnisse herunterladen")
                    
                    valid_json = json.dumps(valid_bookmarks, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="Gültige Lesezeichen herunterladen",
                        data=valid_json,
                        file_name="valid_bookmarks.json",
                        mime="application/json"
                    )
                    
                    if invalid_bookmarks:
                        invalid_json = json.dumps(invalid_bookmarks, ensure_ascii=False, indent=2)
                        st.download_button(
                            label="Ungültige Lesezeichen herunterladen",
                            data=invalid_json,
                            file_name="invalid_bookmarks.json",
                            mime="application/json"
                        )
                    
                except Exception as e:
                    st.error(f"Fehler bei der Verarbeitung: {str(e)}")

if __name__ == "__main__":
    main() 