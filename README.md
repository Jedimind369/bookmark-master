# Bookmark Master

Ein modernes Bookmark-Management-System mit Docker-Unterstützung.

## Projektübersicht

Bookmark Master ist eine Anwendung zur Verwaltung von Lesezeichen mit folgenden Funktionen:
- Speichern und Organisieren von Lesezeichen
- Kategorisierung und Tagging
- Volltextsuche
- Benutzerauthentifizierung
- API-Zugriff

## Docker-Implementierung

Das Projekt ist vollständig dockerisiert und umfasst:
- Node.js 20 Alpine als Basis-Image
- PostgreSQL 16 für die Datenbank
- Redis 7 für Caching
- Prometheus und Grafana für Monitoring

## Schnellstart

```bash
# Repository klonen
git clone https://github.com/Jedimind369/bookmark-master.git
cd bookmark-master

# Docker-Container starten
docker-compose up -d
```

## Projektstruktur

- `/app` - Frontend-Anwendung
- `/server` - Backend-API
- `/docs` - Projektdokumentation
- `/scripts` - Hilfsskripte

## Repository-Struktur und Best Practices

Dieses Repository folgt bewährten Praktiken für die Organisation und Wartung von Code:

### Verzeichnisstruktur

- `docker/`: Docker-Konfigurationsdateien (Dockerfile, docker-compose.yml)
- `docs/`: Dokumentation zum Projekt
- `scripts/`: Hilfsskripte für Entwicklung, Deployment und Wartung
- `src/`: Quellcode der Anwendung
  - `client/`: Frontend-Code
  - `server/`: Backend-Code

### Repository-Wartung

Wir haben mehrere Skripte erstellt, um die Integrität und Struktur des Repositories zu gewährleisten:

- `scripts/verify-repo-integrity.sh`: Überprüft die Integrität des Repositories
- `scripts/cleanup-repository.sh`: Bereinigt die Repository-Struktur
- `scripts/backup-to-github.sh`: Erstellt ein Backup des Repositories auf GitHub

### Best Practices

1. **Klare Verzeichnisstruktur**: Wir organisieren Code in logischen Verzeichnissen.
2. **Dokumentation**: Wichtige Prozesse und Konfigurationen sind dokumentiert.
3. **Automatisierung**: Wiederholende Aufgaben werden durch Skripte automatisiert.
4. **Versionierung**: Wir verwenden Git-Tags für wichtige Releases.
5. **Backup**: Regelmäßige Backups sichern den Code.

## Nächste Schritte

Siehe [docs/NEXT-STEPS.md](docs/NEXT-STEPS.md) für die geplanten nächsten Entwicklungsschritte.

## Lizenz

MIT