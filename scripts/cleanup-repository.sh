#!/bin/bash

# Skript zur Bereinigung des Repositories
# Dieses Skript entfernt Duplikate und optimiert die Repository-Struktur

echo "Starte Repository-Bereinigung..."

# Wechsle zum Repository-Root-Verzeichnis
cd "$(git rev-parse --show-toplevel)" || exit 1

# Entferne das doppelte Unterverzeichnis, falls vorhanden
if [ -d "./bookmark-master" ]; then
  echo "Entferne doppeltes Unterverzeichnis 'bookmark-master'..."
  
  # Prüfe, ob es Dateien gibt, die nur im Unterverzeichnis existieren
  UNIQUE_FILES=$(find ./bookmark-master -type f | while read file; do
    rel_path=${file#./bookmark-master/}
    if [ ! -f "./$rel_path" ]; then
      echo "$file"
    fi
  done)
  
  if [ -n "$UNIQUE_FILES" ]; then
    echo "WARNUNG: Die folgenden Dateien existieren nur im Unterverzeichnis und würden verloren gehen:"
    echo "$UNIQUE_FILES"
    read -p "Möchtest du diese Dateien in das Hauptverzeichnis kopieren? (j/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Jj]$ ]]; then
      echo "Kopiere einzigartige Dateien..."
      find ./bookmark-master -type f | while read file; do
        rel_path=${file#./bookmark-master/}
        if [ ! -f "./$rel_path" ]; then
          mkdir -p "$(dirname "./$rel_path")"
          cp "$file" "./$rel_path"
          echo "Kopiert: $rel_path"
        fi
      done
    fi
  fi
  
  # Entferne das Unterverzeichnis aus dem Git-Repository
  git rm -r --cached bookmark-master
  
  # Entferne das Unterverzeichnis physisch
  rm -rf bookmark-master
  
  echo "Unterverzeichnis 'bookmark-master' wurde entfernt."
fi

# Entferne das backup-Verzeichnis aus dem Git-Repository, falls gewünscht
if [ -d "./backup" ]; then
  read -p "Möchtest du das 'backup'-Verzeichnis aus dem Git-Repository entfernen? (j/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Jj]$ ]]; then
    echo "Entferne 'backup'-Verzeichnis aus dem Git-Repository..."
    git rm -r --cached backup
    echo "backup" >> .gitignore
    echo "'backup'-Verzeichnis wurde aus dem Git-Repository entfernt und zu .gitignore hinzugefügt."
  fi
fi

# Optimiere .gitignore
if [ ! -f ".gitignore" ]; then
  echo "Erstelle .gitignore-Datei..."
  cat > .gitignore << EOL
# Abhängigkeiten
node_modules/
npm-debug.log
yarn-debug.log
yarn-error.log
package-lock.json

# Umgebungsvariablen
.env
.env.local
.env.development
.env.test
.env.production

# Build-Verzeichnisse
dist/
build/
coverage/

# Logs
logs/
*.log

# Betriebssystem-Dateien
.DS_Store
Thumbs.db

# IDE-Dateien
.idea/
.vscode/
*.sublime-*
*.swp
*.swo

# Temporäre Dateien
tmp/
temp/

# Backup-Verzeichnisse
backup/
EOL
  echo ".gitignore-Datei wurde erstellt."
else
  echo "Aktualisiere .gitignore-Datei..."
  if ! grep -q "backup/" .gitignore; then
    echo "backup/" >> .gitignore
    echo "'backup/' wurde zu .gitignore hinzugefügt."
  fi
fi

# Committe die Änderungen
echo "Committe die Änderungen..."
git add .gitignore
git commit -m "Repository-Struktur bereinigt: Duplikate entfernt und .gitignore optimiert"

echo "Repository-Bereinigung abgeschlossen."
echo "Führe 'git push' aus, um die Änderungen zum Remote-Repository zu pushen." 