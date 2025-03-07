#!/usr/bin/env python3
"""
GitHub-Synchronisationsmodul für API-Monitoring-Backups.

Dieses Modul ermöglicht die automatische Synchronisation von Backups mit einem GitHub-Repository
und bietet Funktionen für Versionierung, automatische Commits und Metadaten-Tracking.
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

# MCP-Funktionen für GitHub-Integration
from scripts.monitoring.api_monitor import APIMonitor
from scripts.monitoring.config import (
    MONITORING_DATA_DIR, LOG_FILE, BASE_DIR
)

# Logger-Konfiguration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File Handler
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.INFO)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Handler hinzufügen
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class GitHubSync:
    """
    Klasse für die Synchronisation von Backups mit GitHub.
    
    Diese Klasse bietet Funktionen für:
    - Automatische Commits bei neuen Backups
    - Versionierung von Backup-Metadaten
    - Tracking von Git-Commit-Hashes in Backup-Metadaten
    - Wiederherstellung aus bestimmten Git-Versionen
    """
    
    def __init__(self, api_monitor: APIMonitor, repo_path: Optional[str] = None):
        """
        Initialisiert die GitHub-Synchronisation.
        
        Args:
            api_monitor: Eine Instanz des APIMonitor
            repo_path: Pfad zum Git-Repository (Standard: Projektverzeichnis)
        """
        self.api_monitor = api_monitor
        self.repo_path = repo_path or str(BASE_DIR)
        
        # Prüfe, ob das Verzeichnis ein Git-Repository ist
        if not self._is_git_repo():
            logger.warning(f"Das Verzeichnis {self.repo_path} ist kein Git-Repository")
        
        # Speichere Git-Informationen im Kontext
        self._store_git_info()
    
    def _is_git_repo(self) -> bool:
        """Prüft, ob das Verzeichnis ein Git-Repository ist."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except Exception as e:
            logger.error(f"Fehler bei der Prüfung des Git-Repositories: {str(e)}")
            return False
    
    def _get_current_branch(self) -> str:
        """Ermittelt den aktuellen Git-Branch."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Fehler beim Ermitteln des Git-Branches: {str(e)}")
            return "unknown"
    
    def _get_current_commit(self) -> str:
        """Ermittelt den aktuellen Git-Commit-Hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Fehler beim Ermitteln des Git-Commits: {str(e)}")
            return "unknown"
    
    def _store_git_info(self):
        """Speichert Git-Informationen im Kontext des API-Monitors."""
        try:
            branch = self._get_current_branch()
            commit = self._get_current_commit()
            
            # Speichere im Kontext
            self.api_monitor.store_context_information("git_branch", branch)
            self.api_monitor.store_context_information("git_commit", commit)
            self.api_monitor.store_context_information("git_repo_path", self.repo_path)
            self.api_monitor.store_context_information("git_sync_enabled", True)
            
            logger.info(f"Git-Informationen gespeichert: Branch {branch}, Commit {commit}")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Git-Informationen: {str(e)}")
    
    def commit_backup(self, backup_file: Union[str, Path], message: Optional[str] = None) -> bool:
        """
        Erstellt einen Commit für ein Backup.
        
        Args:
            backup_file: Pfad zur Backup-Datei
            message: Optionale Commit-Nachricht
            
        Returns:
            bool: True, wenn der Commit erfolgreich war
        """
        backup_file = Path(backup_file)
        if not backup_file.exists():
            logger.error(f"Backup-Datei nicht gefunden: {backup_file}")
            return False
        
        # Relative Pfade zum Repository-Root
        try:
            repo_root = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            ).stdout.strip()
            
            # Berechne relativen Pfad
            rel_path = os.path.relpath(str(backup_file), repo_root)
            
            # Prüfe, ob die Datei im Repository ist
            if rel_path.startswith(".."):
                logger.warning(f"Backup-Datei {backup_file} liegt außerhalb des Repositories")
                return False
            
            # Standardnachricht, wenn keine angegeben wurde
            if message is None:
                backup_type = "full" if "full" in backup_file.name else "incremental"
                message = f"Automatisches {backup_type} Backup vom {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Füge die Datei zum Git-Index hinzu
            add_result = subprocess.run(
                ["git", "add", rel_path],
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if add_result.returncode != 0:
                logger.error(f"Fehler beim Hinzufügen der Datei zum Git-Index: {add_result.stderr}")
                return False
            
            # Erstelle den Commit
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if commit_result.returncode != 0:
                # Wenn nichts zu committen ist, ist das kein Fehler
                if "nothing to commit" in commit_result.stderr or "nothing to commit" in commit_result.stdout:
                    logger.info("Keine Änderungen zu committen")
                    return True
                else:
                    logger.error(f"Fehler beim Erstellen des Commits: {commit_result.stderr}")
                    return False
            
            # Hole den neuen Commit-Hash
            new_commit = self._get_current_commit()
            
            # Aktualisiere die Backup-Metadaten mit dem Commit-Hash
            self._update_backup_metadata(backup_file, new_commit)
            
            logger.info(f"Backup {backup_file.name} erfolgreich committet: {new_commit}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git-Fehler: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Fehler beim Committen des Backups: {str(e)}")
            return False
    
    def _update_backup_metadata(self, backup_file: Path, commit_hash: str):
        """
        Aktualisiert die Backup-Metadaten mit dem Commit-Hash.
        
        Args:
            backup_file: Pfad zur Backup-Datei
            commit_hash: Git-Commit-Hash
        """
        try:
            metadata = self.api_monitor._load_backup_metadata()
            backups = metadata.get('backups', [])
            
            # Finde das entsprechende Backup in den Metadaten
            for backup in backups:
                if backup.get('file') == backup_file.name:
                    # Füge Git-Informationen hinzu
                    backup['git_commit'] = commit_hash
                    backup['git_branch'] = self._get_current_branch()
                    backup['git_commit_time'] = datetime.now().isoformat()
                    break
            
            # Speichere die aktualisierten Metadaten
            self.api_monitor._save_backup_metadata(metadata)
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Backup-Metadaten: {str(e)}")
    
    def push_to_remote(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """
        Pusht Änderungen zum Remote-Repository.
        
        Args:
            remote: Name des Remote-Repositories (Standard: origin)
            branch: Name des Branches (Standard: aktueller Branch)
            
        Returns:
            bool: True, wenn der Push erfolgreich war
        """
        if branch is None:
            branch = self._get_current_branch()
        
        try:
            push_result = subprocess.run(
                ["git", "push", remote, branch],
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if push_result.returncode != 0:
                logger.error(f"Fehler beim Pushen zum Remote-Repository: {push_result.stderr}")
                return False
            
            logger.info(f"Änderungen erfolgreich zu {remote}/{branch} gepusht")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Pushen zum Remote-Repository: {str(e)}")
            return False
    
    def sync_backup(self, backup_file: Union[str, Path], push: bool = True) -> bool:
        """
        Synchronisiert ein Backup mit GitHub (Commit + optional Push).
        
        Args:
            backup_file: Pfad zur Backup-Datei
            push: Ob Änderungen gepusht werden sollen
            
        Returns:
            bool: True, wenn die Synchronisation erfolgreich war
        """
        # Commit erstellen
        commit_success = self.commit_backup(backup_file)
        
        # Wenn gewünscht und der Commit erfolgreich war, pushen
        if commit_success and push:
            return self.push_to_remote()
        
        return commit_success
    
    def sync_all_backups(self, push: bool = True) -> Tuple[int, int]:
        """
        Synchronisiert alle Backups mit GitHub.
        
        Args:
            push: Ob Änderungen gepusht werden sollen
            
        Returns:
            Tuple[int, int]: (Anzahl erfolgreicher Syncs, Gesamtanzahl)
        """
        metadata = self.api_monitor._load_backup_metadata()
        backups = metadata.get('backups', [])
        
        success_count = 0
        total_count = len(backups)
        
        for backup in backups:
            if 'file' in backup and 'git_commit' not in backup:
                backup_file = self.api_monitor.backup_dir / backup['file']
                if backup_file.exists():
                    if self.commit_backup(backup_file):
                        success_count += 1
        
        # Wenn gewünscht und mindestens ein Commit erfolgreich war, pushen
        if success_count > 0 and push:
            self.push_to_remote()
        
        return success_count, total_count
    
    def register_backup_hook(self):
        """
        Registriert einen Hook im APIMonitor, um Backups automatisch zu synchronisieren.
        
        Diese Methode speichert eine Referenz auf diese Instanz im Kontext des APIMonitors,
        damit Backups automatisch synchronisiert werden können.
        """
        self.api_monitor.store_context_information("github_sync_instance", self)
        logger.info("GitHub-Sync-Hook für Backups registriert")

# Hilfsfunktion zum Erstellen einer GitHubSync-Instanz
def create_github_sync(api_monitor: Optional[APIMonitor] = None, repo_path: Optional[str] = None) -> GitHubSync:
    """
    Erstellt eine GitHubSync-Instanz.
    
    Args:
        api_monitor: Eine Instanz des APIMonitor (optional)
        repo_path: Pfad zum Git-Repository (optional)
        
    Returns:
        GitHubSync: Eine Instanz der GitHubSync-Klasse
    """
    if api_monitor is None:
        api_monitor = APIMonitor()
    
    sync = GitHubSync(api_monitor, repo_path)
    sync.register_backup_hook()
    
    return sync

# Wenn das Skript direkt ausgeführt wird
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub-Synchronisation für API-Monitoring-Backups")
    parser.add_argument("--sync-all", action="store_true", help="Alle Backups synchronisieren")
    parser.add_argument("--push", action="store_true", help="Änderungen zum Remote-Repository pushen")
    parser.add_argument("--backup-file", type=str, help="Pfad zur Backup-Datei für die Synchronisation")
    
    args = parser.parse_args()
    
    # Erstelle eine GitHubSync-Instanz
    sync = create_github_sync()
    
    if args.sync_all:
        success_count, total_count = sync.sync_all_backups(push=args.push)
        print(f"{success_count} von {total_count} Backups erfolgreich synchronisiert")
    elif args.backup_file:
        if sync.sync_backup(args.backup_file, push=args.push):
            print(f"Backup {args.backup_file} erfolgreich synchronisiert")
        else:
            print(f"Fehler bei der Synchronisation von {args.backup_file}")
    else:
        parser.print_help() 