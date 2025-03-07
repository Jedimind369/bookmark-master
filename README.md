# Bookmark Master

Ein intelligentes Bookmark-Verwaltungssystem mit dynamischer Modellauswahl, hybridem Caching und Kostenoptimierung.

## Features

### Dynamische Modellauswahl (`model_switcher.py`)
- Analysiert die Komplexität von Prompts und Code-Kontexten
- Berücksichtigt Sicherheits- und DSGVO-Schlüsselwörter
- Wählt das geeignete KI-Modell basierend auf Komplexität und Anforderungen
- Nutzt historische Daten aus dem CostTracker zur Optimierung

### Hybrides Caching-System (`prompt_cache.py`)
- Unterstützt exakte und semantische Cache-Treffer
- Time-To-Live (TTL) für Cache-Einträge
- Berechnet Kosteneinsparungen durch Caching
- Bietet Optimierungsempfehlungen für Cache-Einstellungen
- **NEU**: Automatische Cache-Wartung und -Optimierung
- **NEU**: Adaptive Anpassung des semantischen Schwellenwerts

### Kostentracking (`cost_tracker.py`)
- Protokolliert API-Kosten und Nutzung
- Liefert Kostenübersichten nach Modell und Zeitraum
- Budget-Warnungen bei Überschreitung von Schwellenwerten
- Empfiehlt Optimierungsmaßnahmen zur Kostenreduzierung

### Dashboard (`dashboard/app.py`)
- **NEU**: Übersichts-Tab mit den wichtigsten Metriken auf einen Blick
- **NEU**: Interaktive Zeitreihen-Grafiken für Systemmetriken
- **NEU**: Erweiterte Visualisierungen mit Plotly
- **NEU**: Anpassbare Zeiträume für Datenvisualisierung
- Echtzeit-Visualisierung von Systemmetriken
- Übersicht über Cache-Statistiken und Cache-Trefferquote
- Kostentracking und Budget-Überwachung
- Interaktive Diagramme für Modellnutzung und Kosten

### Cursor-Monitor (`scripts/utils/cursor_monitor.py`)
- Überwacht den Status von Cursor-Prozessen
- Sendet visuelle und akustische Benachrichtigungen bei Blockaden
- Desktop-Benachrichtigungen bei kritischen Zuständen
- Konfigurierbare Prüfintervalle und Benachrichtigungsoptionen

### CI/CD-Pipeline
- **NEU**: Erweiterte CI/CD-Pipeline mit mehreren Phasen
- **NEU**: Code-Qualitätsprüfungen (Linting, Formatting, Type Checking)
- **NEU**: Integration Tests für Systemkomponenten
- **NEU**: Performance Tests mit Locust
- **NEU**: Automatisierte Dashboard-Tests
- Automatisierte Tests mit GitHub Actions
- Linting und Code-Qualitätsprüfungen
- Coverage-Berichte für Testabdeckung
- Automatische Deployment-Prozesse

## Installation

### Anforderungen
- Python 3.8+
- Pip

### Setup

1. Repository klonen:
   ```bash
   git clone https://github.com/yourusername/bookmark-master.git
   cd bookmark-master
   ```

2. Virtuelle Umgebung erstellen und aktivieren:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Unter Windows: venv\Scripts\activate
   ```

3. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

## Verwendung

### Dashboard starten

```bash
streamlit run dashboard/app.py
```

Das Dashboard ist dann unter http://localhost:8501 verfügbar.

Eine detaillierte Anleitung zur Verwendung des Dashboards finden Sie in [docs/dashboard_guide.md](docs/dashboard_guide.md).

### Cursor-Monitor starten

```bash
python3 scripts/utils/cursor_monitor.py
```

Der Cursor-Monitor zeigt ein Fenster mit dem aktuellen Status und sendet Benachrichtigungen bei Problemen.

### Tests ausführen

Unit Tests:
```bash
python -m unittest discover tests/
```

Integration Tests:
```bash
python -m pytest tests/integration/
```

Performance Tests:
```bash
cd tests/performance
python -m locust -f locustfile.py
```

## Dokumentation

- [Dashboard Benutzerhandbuch](docs/dashboard_guide.md) - Anleitung zur Verwendung des Dashboards
- [RAG Erweiterungskonzept](docs/RAG_Idee.md) - Konzept für zukünftige RAG-Funktionalität

## Lizenz

MIT

## Zukünftige Erweiterungen

- Retrieval-Augmented Generation (RAG) für semantische Suche
- Weitere Sprach- und Frameworks-Unterstützung
- Mobile App für Unterwegs-Zugriff
- Erweiterte Zusammenfassungs- und Kategorisierungsfunktionen
- Integration mit externen Wissensquellen
- Erweiterte Analysen und Visualisierungen im Dashboard

Mehr Informationen zu den geplanten RAG-Funktionen finden Sie in [docs/RAG_Idee.md](docs/RAG_Idee.md).
