# Cursor Monitor

Ein Tool zur Überwachung des Cursor-Chat-Status mit angenehmen Systemtönen.

## Funktionen

- Überwacht den Status von Cursor-Chats und erkennt Stillstand
- Verwendet ausschließlich angenehme Systemtöne (KEINE Sprachausgabe)
- Kann einfach ein-/ausgeschaltet werden ohne den Prozess zu beenden
- Erkennt Blockierungen durch hohe CPU-Auslastung
- Erkennt Chat-Aktivität durch Netzwerkanalyse
- **NEU**: Grafische Benutzeroberfläche zur einfachen Steuerung
- **NEU**: Verbesserte Tonausgabe für alle Status-Änderungen

## Installation

Keine zusätzliche Installation erforderlich. Das Tool verwendet die folgenden Python-Module:
- psutil
- platform
- signal
- tkinter (für die GUI)

## Verwendung

### Grafische Benutzeroberfläche (empfohlen)

Die einfachste Methode ist die Verwendung der grafischen Benutzeroberfläche:

```bash
# Starte die GUI
./cursor_monitor_gui.py

# Oder verwende den Desktop-Starter
./cursor_monitor_desktop.sh
```

Für macOS-Benutzer: Du kannst auch eine .app-Datei erstellen:

```bash
./create_macos_app.sh
```

Die GUI bietet folgende Funktionen:
- Start/Stop/Toggle des Monitors
- Konfiguration aller Einstellungen
- Test der Systemtöne
- Statusanzeige und Log

### Über das Shell-Script

Alternativ kannst du das mitgelieferte Shell-Script verwenden:

```bash
./cursor_monitor.sh start     # Startet den Monitor im Hintergrund
./cursor_monitor.sh stop      # Stoppt den Monitor
./cursor_monitor.sh restart   # Neustart des Monitors
./cursor_monitor.sh toggle    # Schaltet den Monitor ein/aus (ohne ihn zu beenden)
./cursor_monitor.sh status    # Zeigt den aktuellen Status an
./cursor_monitor.sh sound     # Schaltet die Tonausgabe ein/aus
./cursor_monitor.sh interval 30  # Setzt das Prüfintervall auf 30 Sekunden
./cursor_monitor.sh threshold 5  # Setzt die Inaktivitätsschwelle auf 5 Sekunden
./cursor_monitor.sh network 50   # Setzt den Netzwerk-Schwellenwert auf 50 Bytes/s
./cursor_monitor.sh cpu 90       # Setzt den CPU-Schwellenwert auf 90%
./cursor_monitor.sh notify 300   # Setzt das Benachrichtigungsintervall auf 5 Minuten
./cursor_monitor.sh help      # Zeigt die Hilfe an
```

### Direkte Verwendung des Python-Scripts

Für fortgeschrittene Benutzer kann das Python-Script auch direkt verwendet werden:

```bash
# Starten des Monitors
python3 cursor_monitor.py

# Konfiguration
python3 cursor_monitor.py --toggle           # Ein-/Ausschalten
python3 cursor_monitor.py --sound            # Tonausgabe ein-/ausschalten
python3 cursor_monitor.py --interval 30      # Prüfintervall setzen
python3 cursor_monitor.py --threshold 5      # Inaktivitätsschwelle setzen
python3 cursor_monitor.py --network 50       # Netzwerk-Schwellenwert setzen
python3 cursor_monitor.py --cpu 90           # CPU-Schwellenwert setzen
python3 cursor_monitor.py --notification-interval 300  # Benachrichtigungsintervall setzen
python3 cursor_monitor.py --status           # Status anzeigen
python3 cursor_monitor.py --kill             # Alle laufenden Monitore beenden
```

## Konfiguration

Die Konfiguration wird in der Datei `~/.cursor_monitor_config.json` gespeichert und kann dort auch manuell bearbeitet werden. Am einfachsten ist jedoch die Verwendung der GUI.

## Töne

Der Monitor verwendet folgende Systemtöne:
- **Aktiv**: Tink.aiff (kurzer, hoher Ton)
- **Inaktiv**: Basso.aiff (tiefer Ton)
- **Nicht gestartet**: Submarine.aiff (U-Boot-Sonar-Ton)

## Fehlerbehebung

Wenn der Monitor nicht wie erwartet funktioniert:

1. Starte die GUI und prüfe den Status
2. Teste die Töne über die GUI (Tab "Allgemein" -> "Test-Töne")
3. Starte den Monitor neu über die GUI oder mit `./cursor_monitor.sh restart`
4. Passe die Schwellenwerte an deine Bedürfnisse an
5. Bei Problemen mit der Tonausgabe, prüfe die Systemtöne in `/System/Library/Sounds/`

## Bekannte Probleme

- Auf einigen Systemen kann es vorkommen, dass die Tonausgabe nicht funktioniert. In diesem Fall kannst du die Systemtöne in der GUI testen und gegebenenfalls andere Töne auswählen.
- Die CPU-Erkennung kann auf manchen Systemen zu empfindlich sein. Passe in diesem Fall den CPU-Schwellenwert an. 