#!/bin/bash
# Setup-Skript für die Testumgebung in CI

set -e

# Farben für die Ausgabe
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Richte Testumgebung ein...${NC}"

# Verzeichnisse erstellen
echo "Erstelle Verzeichnisse..."
mkdir -p data/processed
mkdir -p data/enriched
mkdir -p data/bookmarks
mkdir -p data/embeddings
mkdir -p data/reports
mkdir -p logs
mkdir -p backups
mkdir -p temp

# Erstelle Testdaten
echo "Erstelle Testdaten..."
cat > data/bookmarks/test_bookmarks.json << EOF
[
  {
    "url": "https://example.com",
    "title": "Example Website",
    "description": "Eine Beispiel-Website für Tests",
    "tags": ["test", "example"]
  },
  {
    "url": "https://test.org",
    "title": "Test Organization",
    "description": "Eine Test-Organisation",
    "tags": ["test", "organization"]
  },
  {
    "url": "https://github.com",
    "title": "GitHub",
    "description": "Code-Hosting-Plattform",
    "tags": ["development", "git"]
  }
]
EOF

# Starte Testservices, falls wir nicht in CI sind
if [ -z "$CI" ]; then
    echo -e "${YELLOW}Lokale Test-Services werden gestartet...${NC}"
    
    # Prüfen, ob Docker installiert ist
    if command -v docker &> /dev/null; then
        # Starte Redis für Tests
        if ! docker ps | grep -q "test-redis"; then
            echo "Starte Redis für Tests..."
            docker run --name test-redis -d -p 6379:6379 redis:alpine
        else
            echo "Redis läuft bereits."
        fi
        
        # Starte PostgreSQL für Tests
        if ! docker ps | grep -q "test-postgres"; then
            echo "Starte PostgreSQL für Tests..."
            docker run --name test-postgres -d -p 5432:5432 \
                -e POSTGRES_USER=testuser \
                -e POSTGRES_PASSWORD=testpassword \
                -e POSTGRES_DB=testdb \
                postgres:alpine
        else
            echo "PostgreSQL läuft bereits."
        fi
    else
        echo -e "${RED}Docker nicht gefunden, kann Test-Services nicht starten.${NC}"
        echo "Bitte installiere Docker oder stelle sicher, dass die Dienste manuell gestartet werden."
    fi
fi

# Erstelle eine .env-Datei für Tests
echo "Erstelle .env-Datei für Tests..."
cat > .env.test << EOF
# Test-Konfiguration
NODE_ENV=test
PORT=3001
LOG_LEVEL=info

# Datenbank-Konfiguration
POSTGRES_USER=testuser
POSTGRES_PASSWORD=testpassword
POSTGRES_DB=testdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql://testuser:testpassword@localhost:5432/testdb

# Redis-Konfiguration
REDIS_HOST=localhost
REDIS_PORT=6379

# Processor-Konfiguration
PROCESSOR_URL=http://localhost:5001
MAX_WORKERS=2
MIN_CHUNK_SIZE=50
MAX_CHUNK_SIZE=1000
MEMORY_TARGET=70

# Test-Konfiguration
TEST_TIMEOUT=5000
EOF

# Konfiguriere Python-Testumgebung
if [ -f "processor/requirements.txt" ]; then
    echo "Installiere Python-Abhängigkeiten für Tests..."
    pip install -r processor/requirements.txt
    pip install pytest pytest-cov
fi

# Konfiguriere Node.js-Testumgebung
if [ -f "webapp/package.json" ]; then
    echo "Installiere Node.js-Abhängigkeiten für Tests..."
    cd webapp
    npm install
    cd ..
fi

echo -e "${GREEN}Testumgebung wurde erfolgreich eingerichtet.${NC}" 