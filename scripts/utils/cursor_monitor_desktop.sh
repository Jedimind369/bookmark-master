#!/bin/bash

# cursor_monitor_desktop.sh - Startet die Cursor Monitor GUI

# Finde den Pfad zum Skript
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUI_SCRIPT="$SCRIPT_DIR/cursor_monitor_gui.py"

# Starte die GUI
python3 "$GUI_SCRIPT" 