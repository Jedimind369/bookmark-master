# Monitoring-Setup für den Bookmark-Manager

Dieses Dokument beschreibt das Monitoring-Setup für den Bookmark-Manager, das aus Prometheus für die Metrikerfassung und Grafana für die Visualisierung besteht.

## Übersicht

Das Monitoring-System erfasst verschiedene Metriken aus dem Processor-Service:

- Memory-Nutzung
- Anzahl aktiver Worker
- Verarbeitungsraten und -zeiten
- Fehlerraten
- Chunk-Größen

## Zugriffsdetails

- **Grafana Dashboard**: http://localhost:3001 (Standard-Anmeldedaten: admin/admin)
- **Prometheus**: http://localhost:9091

## Konfigurierung

### Prometheus

Die Konfiguration für Prometheus ist in `prometheus/prometheus.yml` definiert:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'processor'
    scrape_interval: 5s
    static_configs:
      - targets: ['processor:9090']

  - job_name: 'prometheus'
    scrape_interval: 10s
    static_configs:
      - targets: ['localhost:9090']
```

### Grafana

Grafana ist vorkonfiguriert mit:

1. Einer Prometheus-Datenquelle (`grafana/provisioning/datasources/prometheus.yml`)
2. Einem Dashboard für den Processor (`grafana/provisioning/dashboards/processor.json`)

## Wichtige Metriken

### Processor-Metriken

- `bookmark_memory_usage_bytes`: Speichernutzung des Processors
- `bookmark_active_workers`: Anzahl aktiver Worker-Threads
- `bookmark_processing_requests_total`: Gesamtzahl der Verarbeitungsanfragen
- `bookmark_processing_duration_seconds`: Histogram der Verarbeitungszeiten
- `bookmark_processing_errors_total`: Gesamtzahl der Verarbeitungsfehler
- `bookmark_chunk_size_bytes`: Histogram der Chunk-Größen

## Alerts

Für die Produktionsumgebung empfehlen wir die folgenden Alarme:

### Memory-Nutzung

```yaml
- alert: HighMemoryUsage
  expr: bookmark_memory_usage_bytes > 1.5 * 1024 * 1024 * 1024  # 1.5 GB
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Hohe Speichernutzung im Processor"
    description: "Der Processor verwendet mehr als 1.5 GB Speicher seit mehr als 5 Minuten."
```

### Fehlerraten

```yaml
- alert: HighErrorRate
  expr: rate(bookmark_processing_errors_total[5m]) > 0.1
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Hohe Fehlerrate bei der Verarbeitung"
    description: "Die Fehlerrate bei der Verarbeitung liegt über 10% in den letzten 5 Minuten."
```

### Verarbeitungszeit

```yaml
- alert: SlowProcessing
  expr: histogram_quantile(0.95, sum(rate(bookmark_processing_duration_seconds_bucket[5m])) by (le)) > 60
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Langsame Verarbeitung"
    description: "95% der Verarbeitungen dauern länger als 60 Sekunden."
```

## Dashboard-Anpassung

Um das Grafana-Dashboard anzupassen:

1. Melden Sie sich bei Grafana an
2. Navigieren Sie zum "Bookmark Processor" Dashboard
3. Klicken Sie auf das Zahnradsymbol oben rechts
4. Wählen Sie "Dashboard-Einstellungen"
5. Passen Sie die Panels nach Bedarf an
6. Speichern Sie das Dashboard

## Metriken erweitern

Um neue Metriken hinzuzufügen:

1. Erweitern Sie die Metrikerfassung in der `processor/app.py`
2. Aktualisieren Sie das Grafana-Dashboard 
3. Bei Bedarf aktualisieren Sie die Alarmregeln

Beispiel für eine neue Metrik:

```python
# In processor/app.py
bookmark_cache_hits = Counter('bookmark_cache_hits_total', 'Anzahl der Cache-Treffer')

# Bei einem Cache-Treffer
bookmark_cache_hits.inc()
```

## Fehlerbehebung

### Prometheus-Fehler

Wenn Prometheus keine Daten erfasst:

1. Überprüfen Sie, ob der Processor läuft: `docker-compose ps`
2. Überprüfen Sie, ob der Processor die Metriken exportiert: `curl http://processor:9090/metrics`
3. Prüfen Sie die Prometheus-Logs: `docker-compose logs prometheus`
4. Stellen Sie sicher, dass die Netzwerkkonfiguration korrekt ist

### Grafana-Fehler

Wenn Grafana keine Daten anzeigt:

1. Überprüfen Sie, ob Prometheus Daten erfasst
2. Prüfen Sie die Datenquelle in Grafana: Einstellungen -> Datenquellen -> Prometheus
3. Testen Sie die Verbindung zur Datenquelle
4. Prüfen Sie, ob die richtigen Metriken abgefragt werden 