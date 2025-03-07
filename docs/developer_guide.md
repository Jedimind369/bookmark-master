# Entwicklerhandbuch für Bookmark Master

Dieses Handbuch bietet eine umfassende Anleitung für Entwickler, die das Bookmark-Master-System erweitern oder anpassen möchten. Es erklärt die Architektur des Systems, die wichtigsten Komponenten und wie neue Funktionen integriert werden können.

## Inhaltsverzeichnis

1. [Systemarchitektur](#systemarchitektur)
2. [Kernkomponenten](#kernkomponenten)
3. [Hinzufügen neuer KI-Modelle](#hinzufügen-neuer-ki-modelle)
4. [Erweiterung des Caching-Systems](#erweiterung-des-caching-systems)
5. [Anpassung des Dashboards](#anpassung-des-dashboards)
6. [Implementierung neuer Tests](#implementierung-neuer-tests)
7. [Best Practices](#best-practices)
8. [Fehlerbehebung](#fehlerbehebung)

## Systemarchitektur

Das Bookmark-Master-System besteht aus mehreren Kernkomponenten, die zusammenarbeiten, um eine effiziente und kostengünstige KI-gestützte Bookmark-Verwaltung zu ermöglichen:

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
| Model Switcher   |<--->| Prompt Cache     |<--->| Cost Tracker     |
|                  |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
         ^                       ^                        ^
         |                       |                        |
         v                       v                        v
+----------------------------------------------------------+
|                                                          |
|                       Dashboard                          |
|                                                          |
+----------------------------------------------------------+
```

- **Model Switcher**: Analysiert Anfragen und wählt das optimale KI-Modell aus
- **Prompt Cache**: Speichert Anfragen und Antworten für schnelleren Zugriff und Kosteneinsparung
- **Cost Tracker**: Überwacht und protokolliert API-Kosten und Nutzung
- **Dashboard**: Visualisiert Systemmetriken und bietet Steuerungsmöglichkeiten

## Kernkomponenten

### Model Switcher (`scripts/ai/model_switcher.py`)

Der Model Switcher ist verantwortlich für die Analyse der Komplexität von Anfragen und die Auswahl des optimalen KI-Modells. Die Hauptfunktionen sind:

- `analyze_complexity()`: Bewertet die Komplexität einer Anfrage basierend auf verschiedenen Faktoren
- `select_model()`: Wählt das optimale Modell basierend auf der Komplexitätsanalyse und anderen Faktoren aus

Die Modellkonfiguration wird in der `MODELS`-Datenstruktur definiert, die alle verfügbaren Modelle und ihre Eigenschaften enthält.

### Prompt Cache (`scripts/ai/prompt_cache.py`)

Der Prompt Cache speichert Anfragen und Antworten, um wiederholte API-Aufrufe zu vermeiden. Er unterstützt sowohl exakte als auch semantische Übereinstimmungen. Die Hauptfunktionen sind:

- `cached_call()`: Führt einen API-Aufruf durch, verwendet aber den Cache, wenn möglich
- `get_cached_response()`: Sucht nach einer gecachten Antwort für eine Anfrage
- `cache_response()`: Speichert eine Antwort im Cache
- `clean_expired_cache()`: Entfernt abgelaufene Cache-Einträge
- `optimize_cache_storage()`: Optimiert den Cache basierend auf Nutzungsmustern

### Cost Tracker (`scripts/ai/cost_tracker.py`)

Der Cost Tracker überwacht und protokolliert API-Kosten und Nutzung. Die Hauptfunktionen sind:

- `record_api_call()`: Protokolliert einen API-Aufruf mit Kosten und Metadaten
- `get_cost_summary()`: Liefert eine Zusammenfassung der Kosten
- `get_daily_costs()`: Liefert tägliche Kostenübersichten
- `get_model_costs()`: Liefert Kostenübersichten nach Modell
- `get_optimization_recommendations()`: Generiert Empfehlungen zur Kostenoptimierung

### Dashboard (`dashboard/app.py`)

Das Dashboard visualisiert Systemmetriken und bietet Steuerungsmöglichkeiten. Es verwendet Streamlit für die Benutzeroberfläche und Plotly für interaktive Visualisierungen.

## Hinzufügen neuer KI-Modelle

Um ein neues KI-Modell zum System hinzuzufügen, müssen Sie die folgenden Schritte ausführen:

1. **Modellkonfiguration hinzufügen**: Fügen Sie die Modelldetails zur `MODELS`-Datenstruktur in `model_switcher.py` hinzu:

```python
MODELS = {
    # Bestehende Modelle...
    
    "neues_modell": {
        "name": "Neues Modell",
        "provider": "Anbieter",
        "cost_per_1k_input": 0.50,  # Kosten pro 1000 Input-Token
        "cost_per_1k_output": 1.50,  # Kosten pro 1000 Output-Token
        "gdpr_compliant": True,     # DSGVO-konform?
        "max_tokens": 32000,        # Maximale Token-Anzahl
        "region": "EU",             # Hosting-Region
        "api_endpoint": "https://api.example.com/v1/completions"
    }
}
```

2. **API-Integration implementieren**: Erstellen Sie eine Funktion, die die API des neuen Modells aufruft. Fügen Sie diese Funktion in `api_client.py` hinzu:

```python
def call_new_model_api(prompt, max_tokens=1000):
    """
    Ruft die API des neuen Modells auf.
    
    Args:
        prompt (str): Die Anfrage
        max_tokens (int): Maximale Anzahl der Ausgabe-Token
        
    Returns:
        dict: Die API-Antwort
    """
    # API-Aufruf implementieren
    # ...
    
    return response
```

3. **Modellauswahl anpassen**: Passen Sie die `select_model()`-Funktion an, um das neue Modell zu berücksichtigen.

4. **Tests hinzufügen**: Erstellen Sie Tests für das neue Modell in `tests/test_model_switcher.py`.

## Erweiterung des Caching-Systems

Um das Caching-System zu erweitern oder anzupassen, können Sie die folgenden Bereiche modifizieren:

1. **Cache-Konfiguration**: Die Cache-Konfiguration wird in der `CACHE_CONFIG`-Datenstruktur in `prompt_cache.py` definiert:

```python
CACHE_CONFIG = {
    "ttl_days": 30,                  # Time-to-live für Cache-Einträge (Tage)
    "ttl_hours": 24,                 # Time-to-live für Cache-Einträge (Stunden)
    "semantic_threshold": 0.85,      # Schwellenwert für semantische Übereinstimmungen (0-1)
    "max_cache_entries": 1000,       # Maximale Anzahl von Cache-Einträgen pro Typ
    "embedding_dimension": 384,      # Dimension der Embeddings (abhängig vom Modell)
    "semantic_cache_enabled": True,  # Toggle für semantisches Caching
    "cache_metrics_enabled": True,   # Toggle für Cache-Metriken
    # Neue Konfigurationsoptionen hier hinzufügen
}
```

2. **Neue Cache-Strategien**: Um eine neue Cache-Strategie zu implementieren, erstellen Sie eine neue Funktion in `prompt_cache.py` und integrieren Sie sie in die bestehenden Funktionen.

3. **Cache-Speicherung anpassen**: Die Cache-Speicherung kann angepasst werden, indem Sie die Funktionen `cache_response()` und `get_cached_response()` modifizieren.

## Anpassung des Dashboards

Um das Dashboard anzupassen oder zu erweitern, können Sie die folgenden Bereiche modifizieren:

1. **Neue Tabs hinzufügen**: Fügen Sie neue Tabs zum Dashboard hinzu, indem Sie die `st.tabs()`-Funktion erweitern:

```python
tab1, tab2, tab3, tab4, tab5, new_tab = st.tabs([
    "Übersicht", "Kosten-Details", "Cache-Effizienz", 
    "Modell-Nutzung", "System-Metriken", "Neuer Tab"
])

with new_tab:
    st.header("Neuer Tab")
    # Inhalt des neuen Tabs hier hinzufügen
```

2. **Neue Visualisierungen**: Fügen Sie neue Visualisierungen mit Plotly hinzu:

```python
# Beispiel für ein neues Diagramm
fig = px.line(data, x='x', y='y', title="Neues Diagramm")
st.plotly_chart(fig, use_container_width=True)
```

3. **Neue Datenquellen**: Integrieren Sie neue Datenquellen, indem Sie neue Funktionen zum Abrufen und Verarbeiten von Daten hinzufügen.

## Implementierung neuer Tests

Um neue Tests zu implementieren, folgen Sie diesen Richtlinien:

1. **Unit-Tests**: Fügen Sie neue Unit-Tests in den entsprechenden Testdateien im `tests/`-Verzeichnis hinzu:

```python
def test_new_feature(self):
    """Test für die neue Funktion."""
    # Test-Code hier
    result = new_feature()
    self.assertEqual(result, expected_result)
```

2. **Integrationstests**: Fügen Sie neue Integrationstests in `tests/integration/` hinzu, um die Interaktion zwischen Komponenten zu testen.

3. **Performance-Tests**: Erweitern Sie die Performance-Tests in `tests/performance/locustfile.py`, um die Leistung neuer Funktionen zu testen.

## Best Practices

Bei der Entwicklung für das Bookmark-Master-System sollten Sie die folgenden Best Practices beachten:

1. **Dokumentation**: Dokumentieren Sie alle neuen Funktionen und Änderungen ausführlich.

2. **Fehlerbehandlung**: Implementieren Sie robuste Fehlerbehandlung für alle externen API-Aufrufe und Datenbankoperationen.

3. **Logging**: Verwenden Sie das Logging-System, um wichtige Ereignisse und Fehler zu protokollieren.

4. **Tests**: Schreiben Sie Tests für alle neuen Funktionen und stellen Sie sicher, dass bestehende Tests weiterhin bestehen.

5. **Konfiguration**: Verwenden Sie Konfigurationsdateien für alle umgebungsspezifischen Einstellungen.

6. **Codequalität**: Halten Sie sich an PEP 8 und verwenden Sie Tools wie Black und Flake8 zur Codeformatierung und -überprüfung.

## Fehlerbehebung

Hier sind einige häufige Probleme und ihre Lösungen:

1. **API-Fehler**: Überprüfen Sie die API-Schlüssel und Endpunkte in der Konfiguration.

2. **Cache-Probleme**: Löschen Sie den Cache-Ordner und starten Sie das System neu, wenn der Cache inkonsistent ist.

3. **Datenbank-Fehler**: Überprüfen Sie die Datenbankverbindung und -schema.

4. **Dashboard-Fehler**: Überprüfen Sie die Streamlit-Version und stellen Sie sicher, dass alle Abhängigkeiten installiert sind.

5. **Test-Fehler**: Isolieren Sie fehlgeschlagene Tests und überprüfen Sie die Testumgebung. 