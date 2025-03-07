# Scraping-Modul

Dieses Modul bietet eine robuste Lösung zum Scrapen und Analysieren großer Mengen von URLs (11.000+) mit der Zyte API und KI-basierter Inhaltsanalyse.

## Funktionen

- **Effizientes Scraping** mit der Zyte API
- **Batch-Verarbeitung** für große URL-Mengen
- **Fehlerbehandlung und Wiederholungsversuche** für fehlgeschlagene URLs
- **Fortschrittsüberwachung** mit geschätzter Verbleibzeit
- **KI-basierte Inhaltsanalyse** mit dynamischer Modellauswahl
- **Parallelverarbeitung** mit konfigurierbaren Limits

## Voraussetzungen

- Python 3.8+
- Zyte API-Schlüssel (https://www.zyte.com/extract-api/)

## Installation

Installiere die erforderlichen Abhängigkeiten:

```bash
pip install aiohttp pandas numpy
```

## Verwendung

### Einfaches Beispiel

```python
import asyncio
from scripts.scraping import ZyteScraper, ContentAnalyzer

async def main():
    # Scrape einige URLs
    scraper = ZyteScraper(api_key="dein-zyte-api-schlüssel")
    urls = ["https://www.example.com", "https://www.python.org"]
    results = await scraper.scrape_urls(urls)
    
    print(f"Erfolgreich gescrapt: {results['successful']}")
    
    # Analysiere die gescrapten Inhalte
    analyzer = ContentAnalyzer()
    stats = analyzer.analyze_all_scraped_files()
    
    print(f"Erfolgreich analysiert: {stats['successful']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Verarbeitung großer URL-Listen

```python
import asyncio
from scripts.scraping import process_large_url_list

async def main():
    # Verarbeite eine große URL-Liste aus einer Datei
    results = await process_large_url_list(
        url_file="urls.txt",  # Datei mit URLs (eine pro Zeile)
        batch_size=100,       # Anzahl der URLs pro Batch
        max_concurrent=10,    # Maximale Anzahl gleichzeitiger Anfragen
        api_key="dein-zyte-api-schlüssel",  # Optional, kann auch als Umgebungsvariable gesetzt werden
        analyze=True          # Ob die gescrapten Inhalte analysiert werden sollen
    )
    
    print(f"Verarbeitung abgeschlossen!")
    print(f"Erfolgsrate: {results['scraping']['success_rate']:.1f}%")
    print(f"Kosten: ${results['analysis'].get('total_cost', 0):.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Verwendung der Kommandozeile

Das Modul kann auch über die Kommandozeile verwendet werden:

```bash
# Setze den API-Schlüssel als Umgebungsvariable
export ZYTE_API_KEY="dein-zyte-api-schlüssel"

# Verarbeite eine URL-Liste
python -m scripts.scraping.batch_processor urls.txt --batch-size 100 --max-concurrent 10
```

## Konfiguration

Die Konfiguration erfolgt über die Datei `settings.py`:

- `ZYTE_API_KEY`: Zyte API-Schlüssel (kann auch als Umgebungsvariable gesetzt werden)
- `ZYTE_API_SETTINGS`: Erweiterte Einstellungen für die Zyte API
- `BATCH_SIZE`: Standardgröße für Batches (100)
- `MAX_CONCURRENT_REQUESTS`: Maximale Anzahl gleichzeitiger Anfragen (10)

## Ausgabe

Die gescrapten Daten werden im Verzeichnis `data/scraped` gespeichert, die analysierten Daten im Verzeichnis `data/analyzed`. Logs werden im Verzeichnis `logs/scraping` gespeichert.

## Fortschrittsüberwachung

Der Fortschritt wird in regelmäßigen Abständen im Verzeichnis `data/progress` gespeichert und kann zur Wiederaufnahme unterbrochener Verarbeitungen verwendet werden. 