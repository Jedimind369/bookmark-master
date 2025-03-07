# API Kosten-Monitoring

Dieses Modul bietet umfassende Funktionen zur Überwachung und Kontrolle der API-Kosten für verschiedene KI-Modelle (QwQ, Claude, DeepSeek, GPT-4o Mini) im Bookmark-Master-Projekt.

## Funktionen

- **Echtzeit-Kostenüberwachung**: Erfasst alle API-Aufrufe und summiert die Kosten
- **Budget-Limits**: Definierbare Budgetgrenzen mit Warnmeldungen bei Schwellenwerten
- **Detaillierte Statistiken**: Aufschlüsselung der Kosten nach Modellen und Aufgaben
- **Benachrichtigungen**: Desktop- und Slack-Benachrichtigungen bei Budget-Warnungen
- **OpenAI-Integration**: Direkte Abfrage der OpenAI-Nutzungsstatistik
- **Helicone-Integration**: Optional für projektbasierte Kostenkontrolle
- **Automatisches Backup-System**: Tägliche Sicherung der Nutzungsdaten mit Rotationssystem
- **Inkrementelle Backups**: Speichert nur die Änderungen für effiziente Speichernutzung
- **MD5-Integritätsprüfung**: Validiert Backups automatisch vor der Wiederherstellung
- **Interaktives Dashboard**: Visualisiert API-Kosten und Backup-Status in einer Web-Oberfläche
- **GitHub-Integration**: Automatische Synchronisation von Backups mit Git-Repository

## Installation

Das Modul ist Teil des Bookmark-Master-Projekts und erfordert keine zusätzliche Installation. Für die Slack-Benachrichtigungen ist jedoch ein Webhook erforderlich.

Für das Dashboard werden einige zusätzliche Abhängigkeiten benötigt:

```bash
pip install streamlit pandas plotly altair matplotlib
```

## Konfiguration

Die Konfiguration erfolgt über Umgebungsvariablen oder die `config.py` Datei:

```python
# Budgeteinstellungen
API_BUDGET_LIMIT="20.0"              # Gesamtbudget in USD
API_MONITORING_INTERVAL="1800"       # Prüfintervall in Sekunden (Standard: 30 Minuten)

# API-Schlüssel
QWQ_API_KEY="dein-qwq-api-schlüssel"
CLAUDE_API_KEY="dein-claude-api-schlüssel"
DEEPSEEK_API_KEY="dein-deepseek-api-schlüssel"
OPENAI_API_KEY="dein-openai-api-schlüssel"
OPENAI_ORG_ID="deine-openai-organisations-id"

# Optional: Benachrichtigungen
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
SLACK_CHANNEL="#api-budget-alerts"

# Optional: Helicone-Integration
HELICONE_API_KEY="dein-helicone-api-schlüssel"
```

## Verwendung

### Integration in ModelAPIClient

Das Monitoring ist bereits in den `ModelAPIClient` integriert:

```python
from scripts.ai.api_client import ModelAPIClient

# Initialisierung mit Budget-Limit
client = ModelAPIClient(budget_limit=10.0, monitor_enabled=True)

# API-Aufruf (Kosten werden automatisch erfasst)
result = await client.call_model("qwq", "Dein Prompt", max_tokens=100)

# Nutzungsstatistik anzeigen
client.api_monitor.show_usage(detailed=True)
```

### Dashboard starten

Das interaktive Dashboard bietet eine anschauliche Visualisierung der API-Nutzung und Backup-Verwaltung:

```bash
streamlit run scripts/monitoring/dashboard.py
```

Mit dem Dashboard kannst du:
- Die Gesamtkosten und deren Entwicklung im Zeitverlauf anzeigen
- Die Kostenverteilung nach Modellen und Aufgaben analysieren
- Eine Prognose zum Budget-Verbrauch ansehen
- Backups verwalten, erstellen und wiederherstellen
- Die Integrität von Backups prüfen
- Budget-Einstellungen und Warnschwellen anpassen

### GitHub-Synchronisation aktivieren

Die GitHub-Synchronisation ermöglicht die automatische Versionierung von Backups im Git-Repository:

```python
from scripts.monitoring import APIMonitor
from scripts.monitoring.github_sync import create_github_sync

# Monitoring initialisieren
monitor = APIMonitor(budget_limit=20.0)

# GitHub-Synchronisation aktivieren
github_sync = create_github_sync(monitor)

# Alle vorhandenen Backups synchronisieren
success_count, total_count = github_sync.sync_all_backups(push=True)
print(f"{success_count} von {total_count} Backups synchronisiert")
```

Alternativ kann die Synchronisation auch über die Kommandozeile gestartet werden:

```bash
# Alle Backups synchronisieren und zum Remote-Repository pushen
python -m scripts.monitoring.github_sync --sync-all --push

# Ein bestimmtes Backup synchronisieren
python -m scripts.monitoring.github_sync --backup-file data/monitoring/backups/api_usage_backup_2023-10-15_full.json
```

### Simulationstest

Zum Testen der Monitoring-Funktionalität ohne echte API-Aufrufe:

```bash
python -m scripts.monitoring.test_monitoring --simulate --budget 5.0 --target 0.8
```

### Echter Test mit API-Aufrufen

```bash
python -m scripts.monitoring.test_monitoring --real --calls 3 --model qwq --budget 10.0
```

### Backup-Test

Zum Testen der automatischen Backup-Funktionen und Integritätsprüfungen:

```bash
python -m scripts.monitoring.test_monitoring --backup --days 7
```

### Kontinuierliche Überwachung

Starten Sie eine kontinuierliche Überwachung der API-Kosten:

```bash
python -m scripts.monitoring.api_monitor
```

### Backup und Wiederherstellung

Das System erstellt automatisch tägliche Backups in `data/monitoring/backups/`. 
Sie können Backups manuell verwalten:

```python
from scripts.monitoring import APIMonitor

# Monitoring initialisieren
monitor = APIMonitor(budget_limit=20.0)

# Verfügbare Backups auflisten
backups = monitor.list_available_backups()
for backup in backups:
    print(f"Datum: {backup['date']}, Typ: {backup['type']}, Dateigröße: {backup['size']} bytes, Gesamtkosten: ${backup['total_cost']:.2f}")

# Aus einem bestimmten Backup wiederherstellen
success = monitor.restore_from_backup(specific_date="2023-10-15")
if success:
    print("Wiederherstellung erfolgreich")

# Aus dem neuesten Backup wiederherstellen
monitor.restore_from_backup()

# Manuell ein inkrementelles Backup erstellen
monitor._create_backup(incremental=True)

# Manuell ein vollständiges Backup erstellen
monitor._create_full_backup()

# Überprüfe die Integrität eines Backups
is_valid = monitor._verify_backup_integrity("pfad/zum/backup.json")
```

## Datenstruktur

Die API-Nutzungsdaten werden in `data/monitoring/api_usage.json` gespeichert:

```json
{
  "start_date": "2023-10-01T00:00:00",
  "budget_limit": 20.0,
  "total_cost": 5.23,
  "api_calls": [
    {
      "timestamp": "2023-10-01T12:34:56",
      "model": "qwq",
      "tokens_in": 150,
      "tokens_out": 75,
      "cost": 0.0002,
      "task": "bookmark-master-scraping"
    },
    ...
  ],
  "models": {
    "qwq": {
      "calls": 42,
      "tokens_in": 6300,
      "tokens_out": 3150,
      "cost": 0.0084
    },
    ...
  },
  "tasks": {
    "bookmark-master-scraping": {
      "calls": 20,
      "cost": 0.0035
    },
    ...
  },
  "context_info": {
    "github_integration": "MCP Server verbunden",
    "workspace_path": "/Users/jedimind/Downloads/Coding/bookmark-master",
    "git_branch": "main",
    "git_commit": "a1b2c3d4e5f6...",
    "git_repo_path": "/Users/jedimind/Downloads/Coding/bookmark-master"
  }
}
```

## Backup-System

Das System erstellt automatisch tägliche Backups und behält die letzten 7 Tage. 
Die Backup-Metadaten werden in `data/monitoring/backups/backup_metadata.json` gespeichert:

```json
{
  "last_backup_date": "2023-10-15",
  "backup_count": 25,
  "backups": [
    {
      "date": "2023-10-09",
      "file": "api_usage_backup_2023-10-09_full.json",
      "type": "full",
      "size": 15420,
      "total_cost": 3.45,
      "git_commit": "a1b2c3d4e5f6...",
      "git_branch": "main",
      "git_commit_time": "2023-10-09T12:34:56"
    },
    {
      "date": "2023-10-10",
      "file": "api_usage_backup_2023-10-10_incremental.json",
      "type": "incremental",
      "base_backup": "api_usage_backup_2023-10-09_full.json",
      "size": 520,
      "total_cost": 4.25,
      "git_commit": "b2c3d4e5f6g7...",
      "git_branch": "main",
      "git_commit_time": "2023-10-10T14:25:36"
    },
    ...
  ]
}
```

### Vollständige vs. Inkrementelle Backups

- **Vollständige Backups**: Enthalten den kompletten Datenstand, werden für das erste Backup erstellt.
- **Inkrementelle Backups**: Speichern nur Änderungen seit dem letzten vollständigen Backup, sparen Speicherplatz.

### Automatische Wiederherstellung

Bei Fehlern beim Speichern von Daten versucht das System automatisch, 
Daten aus dem neuesten Backup wiederherzustellen, um Datenverlust zu vermeiden.

### Integritätsprüfung

Jedes Backup erhält eine MD5-Prüfsumme, die vor der Wiederherstellung überprüft wird,
um sicherzustellen, dass die Daten nicht beschädigt sind.

### GitHub-Versionierung

Jedes Backup wird automatisch mit dem Git-Repository synchronisiert:
- Commit-Hash wird in den Backup-Metadaten gespeichert
- Automatische Commits bei neuen Backups
- Optionales Pushen zum Remote-Repository
- Wiederherstellung aus bestimmten Git-Versionen möglich

## Benachrichtigungen

Das System sendet Benachrichtigungen bei diesen Ereignissen:

1. **Warnschwellen**: Bei 50%, 75% und 90% des Budgets
2. **Budgetüberschreitung**: Sofortige Warnung bei Überschreitung
3. **Kontinuierliche Updates**: Optional bei regelmäßigen Prüfungen
4. **Backup-Status**: Benachrichtigungen über erfolgreiche/fehlgeschlagene Backups
5. **GitHub-Synchronisation**: Benachrichtigungen über erfolgreiche/fehlgeschlagene Commits und Pushes

## Dashboard

Das Dashboard bietet mehrere Ansichten:

1. **Übersicht**: Gesamtkosten, Kostenentwicklung und Modellverteilung
2. **API-Kosten**: Detaillierte Kostenanalyse nach Modellen und Aufgaben
3. **Backups**: Verwaltung und Integritätsprüfung von Backups
4. **Einstellungen**: Anpassung des Budgets und der Warnschwellen

## Integration mit Helicone

Für eine erweiterte projektbasierte Kostenkontrolle kann [Helicone](https://www.helicone.ai/) integriert werden:

1. Erstellen Sie ein Helicone-Konto
2. Konfigurieren Sie den API-Schlüssel in den Umgebungsvariablen
3. Aktivieren Sie die Helicone-Integration über die Konfigurationsdatei

Das Monitoring-System arbeitet dann nahtlos mit Helicone zusammen, um eine zentralisierte Kostenüberwachung zu ermöglichen.

## Empfehlungen für die Kostenoptimierung

- Setzen Sie ein realistisches Budget basierend auf dem Projektumfang
- Verwenden Sie den Modell-Switcher für kosteneffiziente Modellauswahl
- Implementieren Sie aggressive Caching-Strategien für wiederholte Anfragen
- Überwachen Sie regelmäßig die Nutzungsstatistik mit dem Dashboard
- Nutzen Sie die täglichen Backups zur Analyse von Kostentrends
- Verwenden Sie die GitHub-Integration für eine vollständige Versionierung der Nutzungsdaten 