# Repository-Synchronisation

Diese Dokumentation beschreibt die automatische Repository-Synchronisation für das Bookmark-Master-Projekt.

## Übersicht

Die Repository-Synchronisation stellt sicher, dass das Repository nach wichtigen Änderungen immer aktuell ist. Dies wird durch mehrere Komponenten erreicht:

1. **Bash-Skript für manuelle Synchronisation**: `scripts/utils/repo_sync.sh`
2. **MCP-Monitor für kontinuierliche Überwachung**: `scripts/utils/mcp_repo_monitor.js`
3. **GitHub Action für automatische Synchronisation**: `.github/workflows/repo-sync.yml`
4. **Git-Hook für automatische Synchronisation nach Commits**: `.git/hooks/post-commit`
5. **Systemd-Service/LaunchAgent für kontinuierliche Ausführung**: `scripts/utils/bookmark-repo-monitor.service`

## Installation

Die Installation aller Komponenten erfolgt über das Setup-Skript:

```bash
./scripts/utils/setup_repo_monitor.sh
```

Dieses Skript richtet alle erforderlichen Komponenten ein und startet den Monitor.

## Komponenten

### Bash-Skript für manuelle Synchronisation

Das Skript `scripts/utils/repo_sync.sh` kann manuell ausgeführt werden, um das Repository zu synchronisieren:

```bash
./scripts/utils/repo_sync.sh
```

Es prüft, ob es Änderungen gibt, und führt bei Bedarf einen Commit und Push durch.

### MCP-Monitor für kontinuierliche Überwachung

Der MCP-Monitor `scripts/utils/mcp_repo_monitor.js` überwacht das Repository kontinuierlich und führt bei wichtigen Änderungen automatisch eine Synchronisation durch:

```bash
node scripts/utils/mcp_repo_monitor.js
```

Der Monitor prüft alle 15 Minuten, ob es neue Commits gibt, und führt bei Bedarf eine Synchronisation durch.

### GitHub Action für automatische Synchronisation

Die GitHub Action `.github/workflows/repo-sync.yml` wird bei Push-Events, Pull-Request-Events und täglich um 2 Uhr morgens ausgeführt. Sie führt das Synchronisationsskript aus und erstellt bei wichtigen Änderungen einen Release.

### Git-Hook für automatische Synchronisation nach Commits

Der Git-Hook `.git/hooks/post-commit` wird nach jedem Commit ausgeführt und führt das Synchronisationsskript aus.

### Systemd-Service/LaunchAgent für kontinuierliche Ausführung

Je nach Betriebssystem wird ein Systemd-Service (Linux) oder ein LaunchAgent (macOS) eingerichtet, um den MCP-Monitor kontinuierlich auszuführen.

## Konfiguration

Die Konfiguration der Repository-Synchronisation erfolgt in den jeweiligen Skripten:

- **Wichtige Verzeichnisse**: Die Verzeichnisse, die als wichtig gelten und bei Änderungen eine Synchronisation auslösen, sind in `scripts/utils/repo_sync.sh` und `scripts/utils/mcp_repo_monitor.js` konfiguriert.
- **Prüfintervall**: Das Intervall, in dem der MCP-Monitor das Repository prüft, ist in `scripts/utils/mcp_repo_monitor.js` konfiguriert.
- **GitHub Action-Zeitplan**: Der Zeitplan für die GitHub Action ist in `.github/workflows/repo-sync.yml` konfiguriert.

## Logs

Die Logs der Repository-Synchronisation werden in folgenden Dateien gespeichert:

- **Bash-Skript**: `logs/repo_sync.log`
- **MCP-Monitor**: `logs/mcp_monitor.log`
- **LaunchAgent (macOS)**: `logs/repo-monitor.log` und `logs/repo-monitor-error.log`

## Fehlerbehebung

Bei Problemen mit der Repository-Synchronisation können folgende Schritte durchgeführt werden:

1. **Logs prüfen**: Die Logs enthalten Informationen über Fehler und Warnungen.
2. **Manuelle Synchronisation**: Das Skript `scripts/utils/repo_sync.sh` kann manuell ausgeführt werden, um das Repository zu synchronisieren.
3. **Monitor neu starten**: Der MCP-Monitor kann neu gestartet werden, indem der Systemd-Service oder LaunchAgent neu gestartet wird.
4. **Setup neu ausführen**: Das Setup-Skript `scripts/utils/setup_repo_monitor.sh` kann erneut ausgeführt werden, um alle Komponenten neu einzurichten. 