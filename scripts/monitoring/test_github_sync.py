#!/usr/bin/env python3
"""
Test-Skript für die GitHub-Synchronisation.

Dieses Skript testet die Funktionalität der GitHub-Synchronisation für API-Monitoring-Backups.
"""

import os
import sys
import asyncio
import argparse
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

from scripts.monitoring import APIMonitor
from scripts.monitoring.github_sync import GitHubSync, create_github_sync

async def test_github_sync(test_repo_path=None, create_test_backup=True):
    """
    Testet die GitHub-Synchronisation.
    
    Args:
        test_repo_path: Pfad zum Test-Repository (optional)
        create_test_backup: Ob ein Test-Backup erstellt werden soll
    """
    print(f"\n{'='*20} GITHUB-SYNCHRONISATION TESTEN {'='*20}")
    
    # Wenn kein Test-Repository angegeben wurde, verwende das aktuelle Verzeichnis
    if test_repo_path is None:
        test_repo_path = os.getcwd()
    
    print(f"Verwende Repository: {test_repo_path}")
    
    # Prüfe, ob das Verzeichnis ein Git-Repository ist
    is_git_repo = _is_git_repo(test_repo_path)
    if not is_git_repo:
        print(f"WARNUNG: {test_repo_path} ist kein Git-Repository")
        if input("Möchtest du ein temporäres Git-Repository erstellen? (j/n): ").lower() == 'j':
            test_repo_path = _create_temp_git_repo()
            print(f"Temporäres Git-Repository erstellt: {test_repo_path}")
        else:
            print("Test abgebrochen")
            return
    
    # Initialisiere den API-Monitor
    monitor = APIMonitor()
    
    # Erstelle die GitHub-Synchronisation
    github_sync = GitHubSync(monitor, test_repo_path)
    
    # Zeige Git-Informationen
    branch = github_sync._get_current_branch()
    commit = github_sync._get_current_commit()
    print(f"Git-Branch: {branch}")
    print(f"Git-Commit: {commit}")
    
    # Prüfe, ob Git-Informationen im Kontext gespeichert wurden
    context_info = monitor.list_all_context_information()
    print("\nGespeicherte Kontext-Informationen:")
    for key, value in context_info.items():
        if key.startswith('git_'):
            print(f"  {key}: {value}")
    
    # Erstelle ein Test-Backup, wenn gewünscht
    if create_test_backup:
        print("\nErstelle Test-Backup...")
        
        # Erstelle ein vollständiges Backup
        success = monitor._create_full_backup()
        if success:
            print("Test-Backup erfolgreich erstellt")
            
            # Finde das erstellte Backup
            backup_files = list(monitor.backup_dir.glob("*_full.json"))
            if backup_files:
                latest_backup = max(backup_files, key=os.path.getmtime)
                print(f"Neuestes Backup: {latest_backup}")
                
                # Synchronisiere das Backup mit GitHub
                print("\nSynchronisiere Backup mit GitHub...")
                if github_sync.commit_backup(latest_backup):
                    print("Backup erfolgreich mit GitHub synchronisiert")
                    
                    # Zeige die aktualisierten Metadaten
                    metadata = monitor._load_backup_metadata()
                    backups = metadata.get('backups', [])
                    
                    for backup in backups:
                        if backup.get('file') == os.path.basename(latest_backup):
                            print("\nBackup-Metadaten:")
                            for key, value in backup.items():
                                print(f"  {key}: {value}")
                            break
                else:
                    print("Fehler bei der Synchronisation des Backups")
            else:
                print("Kein Backup gefunden")
        else:
            print("Fehler beim Erstellen des Test-Backups")
    
    # Teste die Synchronisation aller Backups
    print("\nSynchronisiere alle Backups...")
    success_count, total_count = github_sync.sync_all_backups(push=False)
    print(f"{success_count} von {total_count} Backups erfolgreich synchronisiert")
    
    return github_sync

def _is_git_repo(path):
    """Prüft, ob das Verzeichnis ein Git-Repository ist."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except Exception:
        return False

def _create_temp_git_repo():
    """Erstellt ein temporäres Git-Repository für Tests."""
    temp_dir = tempfile.mkdtemp(prefix="git_sync_test_")
    
    try:
        # Initialisiere Git-Repository
        subprocess.run(
            ["git", "init"],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        # Erstelle eine README-Datei
        readme_path = os.path.join(temp_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write("# Test-Repository für GitHub-Synchronisation\n\n")
            f.write(f"Erstellt am: {datetime.now().isoformat()}\n")
        
        # Füge die README-Datei hinzu und erstelle einen Commit
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        return temp_dir
    except Exception as e:
        print(f"Fehler beim Erstellen des temporären Git-Repositories: {str(e)}")
        return None

async def main():
    """Hauptfunktion zum Ausführen des Tests."""
    parser = argparse.ArgumentParser(description="Test der GitHub-Synchronisation")
    parser.add_argument("--repo-path", type=str, help="Pfad zum Git-Repository")
    parser.add_argument("--no-backup", action="store_true", help="Kein Test-Backup erstellen")
    
    args = parser.parse_args()
    
    await test_github_sync(
        test_repo_path=args.repo_path,
        create_test_backup=not args.no_backup
    )

if __name__ == "__main__":
    asyncio.run(main()) 