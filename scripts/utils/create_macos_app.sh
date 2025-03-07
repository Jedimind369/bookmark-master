#!/bin/bash

# create_macos_app.sh - Erstellt eine macOS .app-Datei für den Cursor Monitor

# Finde den Pfad zum Skript
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUI_SCRIPT="$SCRIPT_DIR/cursor_monitor_gui.py"
APP_NAME="Cursor Monitor.app"
APP_PATH="$HOME/Applications/$APP_NAME"

# Erstelle die App-Struktur
echo "Erstelle $APP_NAME..."
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Erstelle die Info.plist
cat > "$APP_PATH/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>CursorMonitor</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.cursor.monitor</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Cursor Monitor</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Erstelle das Starter-Skript
cat > "$APP_PATH/Contents/MacOS/CursorMonitor" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
python3 "$GUI_SCRIPT"
EOF

# Mache das Starter-Skript ausführbar
chmod +x "$APP_PATH/Contents/MacOS/CursorMonitor"

# Kopiere ein Icon (falls vorhanden)
if [ -f "$SCRIPT_DIR/cursor_monitor_icon.icns" ]; then
    cp "$SCRIPT_DIR/cursor_monitor_icon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
fi

echo "App erstellt: $APP_PATH"
echo "Du kannst die App jetzt über Launchpad oder Finder starten." 