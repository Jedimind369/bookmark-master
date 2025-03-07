#!/bin/bash

# cursor_monitor.sh - Einfache Steuerung für den Cursor Monitor

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="$SCRIPT_DIR/cursor_monitor.py"
PID_FILE="$HOME/.cursor_monitor.pid"

# Funktion zum Anzeigen der Hilfe
show_help() {
    echo "Cursor Monitor Steuerung"
    echo "------------------------"
    echo "Verwendung: $0 [Befehl]"
    echo ""
    echo "Befehle:"
    echo "  start       - Startet den Monitor im Hintergrund"
    echo "  stop        - Stoppt den laufenden Monitor"
    echo "  restart     - Neustart des Monitors"
    echo "  toggle      - Schaltet den Monitor ein/aus (ohne ihn zu beenden)"
    echo "  status      - Zeigt den aktuellen Status an"
    echo "  sound       - Schaltet die Tonausgabe ein/aus"
    echo "  interval N  - Setzt das Prüfintervall auf N Sekunden"
    echo "  threshold N - Setzt die Inaktivitätsschwelle auf N Sekunden"
    echo "  network N   - Setzt den Netzwerk-Schwellenwert auf N Bytes/s"
    echo "  cpu N       - Setzt den CPU-Schwellenwert auf N Prozent"
    echo "  notify N    - Setzt das Benachrichtigungsintervall auf N Sekunden"
    echo "  help        - Zeigt diese Hilfe an"
    echo ""
}

# Funktion zum Prüfen, ob der Monitor läuft
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null; then
            return 0  # Läuft
        else
            rm "$PID_FILE"  # PID-Datei löschen, wenn Prozess nicht mehr existiert
        fi
    fi
    return 1  # Läuft nicht
}

# Funktion zum Starten des Monitors
start_monitor() {
    if is_running; then
        echo "Cursor Monitor läuft bereits (PID: $(cat "$PID_FILE"))"
        return
    fi
    
    echo "Starte Cursor Monitor..."
    nohup python3 "$MONITOR_SCRIPT" > /dev/null 2>&1 &
    echo $! > "$PID_FILE"
    echo "Cursor Monitor gestartet (PID: $!)"
}

# Funktion zum Stoppen des Monitors
stop_monitor() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo "Stoppe Cursor Monitor (PID: $PID)..."
        kill "$PID"
        rm "$PID_FILE"
        echo "Cursor Monitor gestoppt"
    else
        echo "Cursor Monitor läuft nicht"
    fi
}

# Hauptlogik
case "$1" in
    start)
        start_monitor
        ;;
    stop)
        stop_monitor
        ;;
    restart)
        stop_monitor
        sleep 1
        start_monitor
        ;;
    toggle)
        if is_running; then
            PID=$(cat "$PID_FILE")
            python3 "$MONITOR_SCRIPT" --toggle
            echo "Cursor Monitor umgeschaltet (PID: $PID bleibt aktiv)"
        else
            echo "Cursor Monitor läuft nicht. Starte ihn zuerst mit 'start'."
        fi
        ;;
    status)
        if is_running; then
            echo "Cursor Monitor läuft (PID: $(cat "$PID_FILE"))"
            python3 "$MONITOR_SCRIPT" --status
        else
            echo "Cursor Monitor läuft nicht"
        fi
        ;;
    sound)
        python3 "$MONITOR_SCRIPT" --sound
        ;;
    interval)
        if [ -z "$2" ]; then
            echo "Fehler: Intervall in Sekunden angeben"
            exit 1
        fi
        python3 "$MONITOR_SCRIPT" --interval "$2"
        ;;
    threshold)
        if [ -z "$2" ]; then
            echo "Fehler: Schwellenwert in Sekunden angeben"
            exit 1
        fi
        python3 "$MONITOR_SCRIPT" --threshold "$2"
        ;;
    network)
        if [ -z "$2" ]; then
            echo "Fehler: Netzwerk-Schwellenwert in Bytes/s angeben"
            exit 1
        fi
        python3 "$MONITOR_SCRIPT" --network "$2"
        ;;
    cpu)
        if [ -z "$2" ]; then
            echo "Fehler: CPU-Schwellenwert in Prozent angeben"
            exit 1
        fi
        python3 "$MONITOR_SCRIPT" --cpu "$2"
        ;;
    notify)
        if [ -z "$2" ]; then
            echo "Fehler: Benachrichtigungsintervall in Sekunden angeben"
            exit 1
        fi
        python3 "$MONITOR_SCRIPT" --notification-interval "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac

exit 0 