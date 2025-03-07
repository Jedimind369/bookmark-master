# Anleitung: Cursor-Monitor

## Übersicht

Der Cursor-Monitor ist ein Hilfsprogramm, das den Status von Cursor im Hintergrund überwacht und dich mit visuellen und akustischen Benachrichtigungen informiert, falls Cursor blockiert wird oder nicht mehr reagiert.

## Funktionen

- **Statusüberwachung**: Überprüft regelmäßig, ob Cursor läuft und reagiert
- **Visuelle Benachrichtigungen**: Ein Statusfenster zeigt den aktuellen Zustand von Cursor an
- **Akustische Benachrichtigungen**: Regelmäßige Töne signalisieren, dass Cursor aktiv ist
- **Desktop-Benachrichtigungen**: Systembenachrichtigungen bei Status-Änderungen
- **Blockierungserkennung**: Erkennt, wenn Cursor viel CPU-Leistung verbraucht und möglicherweise hängt

## Installation

### Voraussetzungen

- Python 3.6 oder höher
- Tkinter (in den meisten Python-Installationen enthalten)
- Psutil-Bibliothek
- Optional: Pygame für Soundausgabe

### Abhängigkeiten installieren

```bash
# In der virtuellen Umgebung
pip install psutil pygame
```

## Verwendung

### Starten des Monitors

```bash
# Navigiere zum scripts/utils-Verzeichnis
cd scripts/utils

# Führe das Skript aus
python cursor_monitor.py
```

### Konfigurationsoptionen

Die Konfiguration kann in der Datei `cursor_monitor.py` angepasst werden:

```python
# Konfiguration
CONFIG = {
    "check_interval": 30,  # Intervall in Sekunden für die Überprüfung
    "sound_enabled": True,  # Akustische Benachrichtigungen aktivieren/deaktivieren
    "visual_enabled": True,  # Visuelle Benachrichtigungen aktivieren/deaktivieren
    "cursor_process_names": ["cursor", "Cursor"],  # Mögliche Prozessnamen für Cursor
    "active_sound": "click.wav",  # Ton für aktiven Status
    "alert_sound": "alert.wav",  # Ton für Warnung
}
```

## Benutzerschnittstelle

Das Überwachungsfenster zeigt folgende Informationen:

- **Statusanzeige**: Zeigt an, ob Cursor aktiv, blockiert oder nicht laufend ist
- **Farbkodierung**: 
  - Grün: Cursor ist aktiv und reagiert normal
  - Rot: Cursor ist blockiert oder reagiert langsam
  - Gelb: Cursor ist nicht aktiv
- **Letzter Check**: Zeitpunkt der letzten Statusprüfung
- **Ton aktivieren/deaktivieren**: Option zum Ein-/Ausschalten der akustischen Benachrichtigungen
- **Jetzt prüfen**: Button zum manuellen Überprüfen des Status

## Anpassen der Benachrichtigungen

### Eigene Töne verwenden

Um eigene Sounddateien zu verwenden, platziere WAV-Dateien im Verzeichnis `scripts/utils/sounds/` und aktualisiere die Konfiguration entsprechend:

```python
CONFIG = {
    # ...
    "active_sound": "mein_aktiv_ton.wav",
    "alert_sound": "mein_alarm_ton.wav",
    # ...
}
```

### Benachrichtigungsintervall anpassen

Das Standard-Intervall für Überprüfungen ist 30 Sekunden. Du kannst dies ändern, um häufigere oder seltenere Überprüfungen durchzuführen:

```python
CONFIG = {
    "check_interval": 10,  # Prüfe alle 10 Sekunden
    # ...
}
```

## Fehlerbehebung

### Das Programm startet nicht

- Überprüfe, ob Python korrekt installiert ist
- Stelle sicher, dass alle erforderlichen Abhängigkeiten installiert sind
- Prüfe die Berechtigungen für das Skript und das Verzeichnis

### Keine Töne zu hören

- Prüfe, ob Pygame installiert und die Option "Ton aktivieren" ausgewählt ist
- Stelle sicher, dass dein System-Audio funktioniert
- Überprüfe, ob gültige Sounddateien im richtigen Verzeichnis vorhanden sind

### Cursor wird nicht erkannt

- Überprüfe, ob der korrekte Prozessname in der Konfiguration angegeben ist
- Prüfe, ob der Cursor-Prozess tatsächlich läuft (z.B. im Task-Manager)
- Passe die `cursor_process_names`-Liste an, um den richtigen Prozessnamen zu verwenden

## Erweiterte Nutzung

### Autostart einrichten

#### Windows

1. Erstelle eine Verknüpfung zur `cursor_monitor.py`-Datei
2. Drücke `Win+R`, gib `shell:startup` ein und drücke Enter
3. Kopiere die Verknüpfung in den geöffneten Ordner

#### macOS

1. Öffne die Systemeinstellungen
2. Gehe zu "Benutzer & Gruppen" > "Anmeldeobjekte"
3. Klicke auf "+", navigiere zur `cursor_monitor.py`-Datei und füge sie hinzu

#### Linux

Füge einen Eintrag zu deiner Autostart-Konfiguration hinzu, z.B. in ~/.config/autostart/cursor-monitor.desktop:

```
[Desktop Entry]
Type=Application
Name=Cursor Monitor
Exec=python /pfad/zu/cursor_monitor.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
```

## Anpassung des Skripts

### Erweiterte Blockierungserkennung

Du kannst die `check_if_cursor_blocked`-Funktion anpassen, um zusätzliche Kriterien für die Erkennung von Blockierungen hinzuzufügen:

```python
def check_if_cursor_blocked(self):
    # ... vorhandener Code ...
    
    # Zusätzliche Kriterien hinzufügen
    # z.B. Speicherverbrauch überwachen
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
        # ... Code für Speicherprüfung ...
```

### Zusätzliche Benachrichtigungskanäle

Das Skript kann erweitert werden, um zusätzliche Benachrichtigungskanäle zu unterstützen, wie Slack, E-Mail oder SMS:

```python
def send_slack_notification(self, message):
    # Implementiere Slack-Webhook-Integration
    pass

def send_email_notification(self, subject, message):
    # Implementiere E-Mail-Versand
    pass
``` 