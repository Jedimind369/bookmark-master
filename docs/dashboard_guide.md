# Dashboard Benutzerhandbuch

## Übersicht

Das AI-System Dashboard bietet eine umfassende Überwachung und Visualisierung der AI-API-Nutzung, Kosten, Cache-Effizienz und Systemmetriken. Es ermöglicht Ihnen, die Leistung und Kosten Ihres AI-Systems in Echtzeit zu verfolgen und zu optimieren.

## Starten des Dashboards

Um das Dashboard zu starten, führen Sie den folgenden Befehl im Hauptverzeichnis des Projekts aus:

```bash
cd dashboard
streamlit run app.py
```

Das Dashboard wird standardmäßig unter http://localhost:8501 geöffnet.

## Dashboard-Funktionen

Das Dashboard ist in mehrere Tabs unterteilt, die verschiedene Aspekte des AI-Systems abdecken:

### 1. Übersicht

Der Übersichts-Tab bietet einen schnellen Überblick über die wichtigsten Metriken des Systems:

- **Wichtigste Kennzahlen**: Heutige Kosten, Cache-Trefferrate, CPU-Auslastung und Speicherauslastung
- **Systemmetriken über Zeit**: Interaktive Grafik, die CPU-Auslastung, Speicherauslastung und Cache-Trefferrate über Zeit anzeigt
- **Tägliche Kosten**: Balkendiagramm der täglichen API-Kosten
- **Optimierungsempfehlungen**: Automatisch generierte Vorschläge zur Optimierung des Systems

### 2. Kosten-Details

Der Kosten-Details-Tab bietet detaillierte Informationen zu den API-Kosten:

- **Kostenzusammenfassung**: Heutige Kosten, Monatskosten, Gesamtkosten und Cache-Trefferrate
- **Budget-Nutzung**: Fortschrittsbalken für tägliches und monatliches Budget
- **Tägliche Kosten**: Detailliertes Balkendiagramm der täglichen API-Kosten
- **Kostentrend-Analyse**: Liniendiagramm mit gleitendem Durchschnitt und Kostenprognose

### 3. Cache-Effizienz

Der Cache-Effizienz-Tab zeigt Informationen zur Leistung des Prompt-Caches:

- **Cache-Statistiken**: Anzahl der Cache-Einträge, Cache-Größe, Trefferrate und eingesparte Zeit
- **Cache-Treffer-Verteilung**: Kreisdiagramm der Verteilung von exakten Treffern, semantischen Treffern und Fehlschlägen
- **Cache-Effizienz über Zeit**: Liniendiagramm der Cache-Trefferrate über Zeit
- **Cache-Optimierungsvorschläge**: Automatisch generierte Vorschläge zur Optimierung des Caches

### 4. Modell-Nutzung

Der Modell-Nutzung-Tab zeigt Informationen zur Nutzung verschiedener AI-Modelle:

- **Modellkosten-Tabelle**: Detaillierte Tabelle mit Kosten und Nutzung pro Modell
- **Kostenverteilung nach Modell**: Kreisdiagramm der Kostenverteilung nach Modell
- **Nutzung nach Modell**: Balkendiagramm der API-Aufrufe nach Modell
- **Kosten-Effizienz-Analyse**: Vergleich der Kosten pro Token für verschiedene Modelle

### 5. System-Metriken

Der System-Metriken-Tab zeigt detaillierte Informationen zur Systemleistung:

- **Systemressourcen**: CPU-Auslastung, Speicherauslastung, Festplattennutzung und Python-Prozesse
- **CPU-Auslastung über Zeit**: Liniendiagramm der CPU-Auslastung
- **Speicherauslastung über Zeit**: Liniendiagramm der Speicherauslastung
- **Detaillierte Systemressourcen**: Erweiterte Informationen zu CPU, Speicher und Netzwerk

## Dashboard-Steuerung

In der Seitenleiste finden Sie Optionen zur Steuerung des Dashboards:

- **Automatische Aktualisierung**: Aktivieren Sie diese Option, um das Dashboard automatisch zu aktualisieren
- **Aktualisierungsintervall**: Stellen Sie ein, wie oft das Dashboard aktualisiert werden soll (in Sekunden)
- **Zeitraum für Datenvisualisierung**: Wählen Sie den Zeitraum für die Datenvisualisierung (24 Stunden, 7 Tage, 1 Monat)
- **Jetzt aktualisieren**: Klicken Sie auf diese Schaltfläche, um das Dashboard sofort zu aktualisieren

## Tipps zur Nutzung

- **Interaktive Grafiken**: Alle Grafiken sind interaktiv. Sie können mit der Maus über Datenpunkte fahren, um Details anzuzeigen, zoomen und die Ansicht anpassen.
- **Zeitraum anpassen**: Nutzen Sie die Zeitraumauswahl in der Seitenleiste, um den Zeitraum für alle Grafiken anzupassen.
- **Optimierungsempfehlungen**: Achten Sie auf die Optimierungsempfehlungen, um die Leistung und Kosten Ihres AI-Systems zu verbessern.
- **Regelmäßige Überwachung**: Überprüfen Sie das Dashboard regelmäßig, um Trends zu erkennen und potenzielle Probleme frühzeitig zu identifizieren.

## Fehlerbehebung

- **Dashboard startet nicht**: Stellen Sie sicher, dass alle Abhängigkeiten installiert sind (`pip install -r requirements.txt`).
- **Keine Daten sichtbar**: Überprüfen Sie, ob die Datenbank und Cache-Verzeichnisse existieren und Lese-/Schreibrechte haben.
- **Fehler bei der Aktualisierung**: Überprüfen Sie die Logs im Terminal, in dem das Dashboard läuft, für detaillierte Fehlermeldungen.

## Weitere Ressourcen

- [Streamlit Dokumentation](https://docs.streamlit.io/)
- [Plotly Dokumentation](https://plotly.com/python/)
- [Projekt README](../README.md) 