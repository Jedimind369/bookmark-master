# Bookmark Manager - Optimierte Microservice-Architektur

Dieses Projekt implementiert einen leistungsstarken Bookmark-Manager mit einer modernen Microservice-Architektur und optimierten Verarbeitungskomponenten.

## Architektur

Das System besteht aus folgenden Komponenten:

- **Webapp**: Eine TypeScript/Node.js-Anwendung, die die Benutzeroberfläche und API-Endpunkte bereitstellt
- **Database**: Eine PostgreSQL-Datenbank für die persistente Speicherung von Lesezeichen und Metadaten
- **Redis**: Ein Cache-Service für verbesserte Leistung
- **Processor**: Ein Python-Microservice für die optimierte Verarbeitung von Lesezeichen mit Chunk-basierter Parallelverarbeitung
- **Prometheus**: Ein Monitoring-Service für die Erfassung von Metriken
- **Grafana**: Ein Dashboard-Service für die Visualisierung von Metriken

## Hauptmerkmale

- **Hochleistungs-Verarbeitung**: Chunk-basierte Verarbeitung mit dynamischer Größenanpassung für optimale Speichernutzung
- **Parallele Verarbeitung**: Effiziente Nutzung mehrerer CPU-Kerne für schnellere Verarbeitung
- **Robuste Fehlerbehandlung**: Umfassende Fehlerbehandlung und Wiederherstellungsmechanismen
- **Thread-sichere UI-Updates**: Vermeidung von Race-Conditions bei UI-Updates
- **Umfassendes Monitoring**: Detaillierte Metriken für Leistung, Speichernutzung und Fehler
- **Automatisierte Backups**: Robuste Backup-Strategie für SQLite-Datenbanken mit Integritätsprüfungen
- **Skalierbare Architektur**: Microservice-Architektur für einfache Skalierung und Wartung

## Erste Schritte

### Voraussetzungen

- Docker und Docker Compose
- Git

### Installation

1. Repository klonen:
   ```bash
   git clone https://github.com/yourusername/bookmark-manager.git
   cd bookmark-manager
   ```

2. Umgebungsvariablen konfigurieren:
   ```bash
   cp .env.example .env
   # Bearbeiten Sie die .env-Datei mit Ihren Einstellungen
   ```

3. System starten:
   ```bash
   docker-compose up -d
   ```

4. Zugriff auf die Anwendung:
   - Webapp: http://localhost:3000
   - Grafana-Dashboard: http://localhost:3001 (Benutzername: admin, Passwort: admin)

## Konfiguration

### Processor-Konfiguration

Der Processor-Service kann über Umgebungsvariablen konfiguriert werden:

- `MAX_WORKERS`: Maximale Anzahl paralleler Worker (Standard: Anzahl der CPU-Kerne)
- `MIN_CHUNK_SIZE`: Minimale Chunk-Größe in Bytes (Standard: 1000)
- `MAX_CHUNK_SIZE`: Maximale Chunk-Größe in Bytes (Standard: 10000000)
- `MEMORY_TARGET`: Ziel-Speichernutzung in Prozent (Standard: 70)

### Backup-Konfiguration

Das Backup-Skript kann über folgende Variablen konfiguriert werden:

- `DB_PATH`: Pfad zur SQLite-Datenbank
- `BACKUP_DIR`: Verzeichnis für Backups
- `CLOUD_BACKUP_DIR`: Verzeichnis für Cloud-Backups (optional)
- `RETENTION_DAYS`: Anzahl der Tage, für die Backups aufbewahrt werden sollen

## Entwicklung

### Lokale Entwicklung

1. Repository klonen und Abhängigkeiten installieren:
   ```bash
   git clone https://github.com/yourusername/bookmark-manager.git
   cd bookmark-manager
   
   # Für den Processor
   cd processor
   pip install -r requirements.txt
   
   # Für die Webapp
   cd ../webapp
   npm install
   ```

2. Lokale Entwicklungsserver starten:
   ```bash
   # Processor
   cd processor
   python app.py
   
   # Webapp
   cd webapp
   npm run dev
   ```

### Tests

```bash
# Processor-Tests
cd processor
pytest

# Webapp-Tests
cd webapp
npm test
```

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz - siehe die [LICENSE](LICENSE)-Datei für Details.
