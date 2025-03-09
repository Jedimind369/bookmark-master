# Fahrplan für das Bookmark-Projekt

## 1. Zielsetzung
- **Scraping:** Dynamische Inhalte (Artikeltexte, Metadaten) effizient mit ScrapingBee extrahieren.
- **Persistenz:** Robuste Speicherung aller gescrapten Daten in einer SQLite-Datenbank, um Kosten zu sparen und Datenintegrität zu gewährleisten.
- **KI-Beschreibungserstellung:** Hochwertige, personalisierte Beschreibungen generieren.
- **Semantische Analyse:** Thematische Verbindungen zwischen Lesezeichen herstellen.
- **Dashboard:** Ergebnisse visualisieren und interaktiv nutzbar machen.

## 2. Architektur & Tools
- **Scraping:**  
  - ScrapingBee als Hauptwerkzeug für dynamisches Scraping (JavaScript-Rendering, Proxy-Rotation).  
  - Fallback-Scraper für statische Inhalte bei Bedarf.  
- **Persistenz:**  
  - SQLite-Datenbank zur Speicherung von URL, Titel, Artikeltext, Beschreibungen und Zeitstempel.  
  - GZip-Komprimierung zur Reduktion des Speicherbedarfs.  
- **KI-Schicht:**  
  - GPT-Modelle für die Erzeugung hochwertiger Beschreibungen.  
  - Embedding-Generierung und Clustering zur semantischen Analyse.  
- **Monitoring & Reporting:**  
  - Dashboard (Streamlit) zur Echtzeitüberwachung und Berichterstellung.  

## 3. Implementierungsphasen

### Phase A: Testlauf & SQLite-Setup
1. **SQLite-Datenbank initialisieren:**  
   Erstelle eine robuste lokale Datenbank:
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('bookmarks.db'); conn.execute('CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, title TEXT, content TEXT, scraper TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')"
   ```

2. **Testlauf mit 200 URLs starten:**  
   Führe den Hybrid-Scraper mit einer kleinen Anzahl von URLs aus:
   ```bash
   python hybrid_scraper.py --input sample_200_urls.json --output testrun_$(date +%s).json.gz
   ```

3. **Dashboard parallel starten:**  
   Überwache den Fortschritt im Dashboard:
   ```bash
   streamlit run dashboard.py
   ```

### Phase B: Optimierung & Vollständiger Durchlauf
1. **Merge-Prozess korrigieren:**  
   Stelle sicher, dass Batch-Dateien korrekt zusammengeführt werden:
   ```python
   import json, gzip, glob

   all_data = []
   for batch in glob.glob('data/enriched/hybrid_*_batch*.json.gz'):
       with gzip.open(batch, 'rt') as f:
           all_data.extend(json.load(f))

   with gzip.open('data/enriched/hybrid_fully_enhanced.json.gz', 'wt') as f:
       json.dump(all_data, f)
   ```

2. **Fehlerbehandlung erweitern:**  
   Implementiere Retry-Mechanismen und verbessere das Logging:
   ```python
   from tenacity import retry, wait_exponential, stop_after_attempt

   @retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5))
   def scrape_with_retry(url):
       return scrape_with_scrapingbee(url)
   ```

3. **Vollständiger Lauf mit allen Lesezeichen:**  
   Nach erfolgreichem Testlauf führe die gesamte Pipeline aus:
   ```bash
   python hybrid_scraper.py --input bookmarks_valid_urls.json --output full_dataset.json.gz
   ```

### Phase C: KI-Veredelung & Reporting
1. **KI-Beschreibungen generieren:**  
   Ergänze fehlende oder unzureichende Beschreibungen mithilfe von GPT-Modellen:
   ```bash
   python generate_descriptions.py --input full_dataset.json.gz --output fully_enriched.json.gz
   ```

2. **Semantische Analyse & Clustering:**  
   Generiere Embeddings und führe eine Cluster-Analyse durch:
   ```bash
   python clustering.py --input fully_enriched.json.gz
   ```

3. **Bericht erstellen & Dashboard aktualisieren:**  
   Generiere einen HTML-Bericht und aktualisiere das Dashboard mit den vollständigen Daten:
   ```bash
   python export_report.py --input fully_enriched.json.gz --output final_report.html
   streamlit run dashboard.py --server.port 8502
   ```

## 4. Langfristige Optimierungen
1. **Automatisches Tagging:**  
   Tags basierend auf den generierten Beschreibungen erstellen.
2. **Empfehlungssystem:**  
   Ähnliche Lesezeichen vorschlagen basierend auf semantischen Verbindungen.
3. **Regelmäßige Updates:**  
   Scheduler einrichten, um neue Inhalte automatisch zu scrapen und zu analysieren. 