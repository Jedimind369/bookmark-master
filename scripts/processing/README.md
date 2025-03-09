# Chunk-Prozessor

Ein System zur chunk-basierten Verarbeitung großer Dateien mit Speicheroptimierung.

## Überblick

Der Chunk-Prozessor ist eine Lösung für die Verarbeitung großer Dateien und Texte, die folgende Vorteile bietet:

- **Speicheroptimierung**: Verarbeitet Dateien in Chunks, um den Speicherverbrauch zu minimieren
- **Parallelverarbeitung**: Nutzt mehrere Worker-Threads für parallele Verarbeitung
- **Dynamische Chunk-Größe**: Passt die Chunk-Größe basierend auf Dateigröße und verfügbarem Speicher an
- **Fortschrittsüberwachung**: Bietet detaillierte Fortschritts- und Statusupdates
- **Robuste Fehlerbehandlung**: Behandelt Fehler in einzelnen Chunks, ohne die gesamte Verarbeitung abzubrechen
- **Abbruchlogik**: Ermöglicht das kontrollierte Abbrechen der Verarbeitung

## Installation

```bash
# Installiere Abhängigkeiten
pip install -r requirements.txt
```

## Verwendung

### Grundlegende Verwendung

```python
from processing.chunk_processor import ChunkProcessor

# Erstelle Chunk-Prozessor
processor = ChunkProcessor()

# Definiere Verarbeitungsfunktion
def process_chunk(chunk):
    # Verarbeite den Chunk (bytes)
    return len(chunk)  # Beispiel: Zähle Bytes

# Verarbeite eine Datei
result = processor.process_file("pfad/zur/datei.txt", process_chunk)

# Verarbeite einen Text
text = "Dies ist ein Beispieltext..."
result = processor.process_text(text, lambda chunk: len(chunk.split()))  # Zähle Wörter

# Fahre Prozessor herunter, wenn nicht mehr benötigt
processor.shutdown()
```

### Mit Callbacks für UI-Integration

```python
# Callback-Funktionen für UI-Integration
def progress_callback(progress, stats):
    # Aktualisiere Fortschrittsanzeige (progress ist ein Wert zwischen 0.0 und 1.0)
    print(f"Fortschritt: {progress:.1%}")

def status_callback(status, stats):
    # Aktualisiere Statusanzeige
    print(f"Status: {status}")

def error_callback(message, exception):
    # Behandle Fehler
    print(f"Fehler: {message} - {str(exception)}")

def complete_callback(stats):
    # Verarbeitung abgeschlossen
    print(f"Verarbeitung abgeschlossen in {stats['end_time'] - stats['start_time']:.2f} Sekunden")

# Erstelle Chunk-Prozessor mit Callbacks
processor = ChunkProcessor(
    callback_progress=progress_callback,
    callback_status=status_callback,
    callback_error=error_callback,
    callback_complete=complete_callback,
    max_workers=4  # Anzahl der Worker-Threads
)
```

### Anpassung der Chunk-Größe

```python
# Erstelle Chunk-Prozessor mit angepassten Chunk-Größen
processor = ChunkProcessor(
    min_chunk_size=100,  # Minimale Chunk-Größe in KB
    max_chunk_size=5000,  # Maximale Chunk-Größe in KB
    memory_target_percentage=0.5  # Ziel-Speicherauslastung (50%)
)
```

### Abbruch der Verarbeitung

```python
# Starte Verarbeitung in separatem Thread
import threading
thread = threading.Thread(
    target=lambda: processor.process_file("große_datei.txt", process_chunk),
    daemon=True
)
thread.start()

# Später: Breche Verarbeitung ab
processor.cancel()
```

## Beispiele

Siehe die folgenden Dateien für Beispiele:

- `example_ui_integration.py`: Beispiel für die Integration mit einer Tkinter-UI
- `test_chunk_processor.py`: Testfälle und Beispiele für verschiedene Anwendungsfälle

## Leistungsmerkmale

- **Speichereffizienz**: Verarbeitet Dateien beliebiger Größe mit begrenztem Speicherverbrauch
- **Parallelverarbeitung**: Nutzt mehrere CPU-Kerne für beschleunigte Verarbeitung
- **Robustheit**: Behandelt Fehler in einzelnen Chunks, ohne die gesamte Verarbeitung abzubrechen
- **Fortschrittsüberwachung**: Bietet detaillierte Metriken zur Verarbeitungsgeschwindigkeit und Speichernutzung
- **Flexibilität**: Unterstützt sowohl Datei- als auch Textverarbeitung mit benutzerdefinierten Verarbeitungsfunktionen

## Technische Details

### Architektur

Der Chunk-Prozessor verwendet ein Producer-Consumer-Muster:

1. Der Hauptthread liest Chunks aus der Datei und fügt sie zur Task-Queue hinzu
2. Worker-Threads verarbeiten die Chunks parallel und speichern die Ergebnisse in der Result-Queue
3. Der Hauptthread sammelt die Ergebnisse und stellt sie in sortierter Reihenfolge bereit

### Speicheroptimierung

- Dynamische Anpassung der Chunk-Größe basierend auf Dateigröße und verfügbarem Speicher
- Verarbeitung eines Chunks nach dem anderen, um den Speicherverbrauch zu minimieren
- Überwachung des Speicherverbrauchs während der Verarbeitung

### Fehlerbehandlung

- Fehler in einzelnen Chunks werden protokolliert und über Callbacks gemeldet
- Die Verarbeitung wird fortgesetzt, auch wenn einzelne Chunks fehlschlagen
- Detaillierte Fehlerinformationen werden im Ergebnis bereitgestellt

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. 