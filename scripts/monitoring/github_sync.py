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
import datetime
import requests
import time
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
        
        self.config_path = Path(MONITORING_DATA_DIR) / "github_config.json"
        self.config = self._load_config()
        
        # Setze Standard-Repository-Pfad (aktuelles Arbeitsverzeichnis)
        self.repo_path = Path.cwd()
        self.last_sync_path = Path(MONITORING_DATA_DIR) / "last_sync.json"
        
        # GitHub API-Basis-URL
        self.api_base_url = "https://api.github.com"
        
        # Lade den Access-Token aus der Umgebungsvariable
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
    
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
                message = f"Automatisches {backup_type} Backup vom {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
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
                    backup['git_commit_time'] = datetime.datetime.now().isoformat()
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
    
    def _load_config(self) -> Dict[str, Any]:
        """Lade die GitHub-Konfiguration aus der Datei."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Fehler beim Laden der GitHub-Konfiguration: {str(e)}")
        
        # Standard-Konfiguration
        return {
            "repository": os.environ.get("GITHUB_REPOSITORY", ""),
            "branch": os.environ.get("GITHUB_BRANCH", "main"),
            "auto_sync": os.environ.get("GITHUB_AUTO_SYNC", "false").lower() == "true"
        }
    
    def _save_last_sync(self, data: Dict[str, Any]) -> None:
        """Speichere Informationen über die letzte Synchronisation."""
        try:
            with open(self.last_sync_path, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error(f"Fehler beim Speichern der Sync-Informationen: {str(e)}")
    
    def _load_last_sync(self) -> Dict[str, Any]:
        """Lade Informationen über die letzte Synchronisation."""
        if self.last_sync_path.exists():
            try:
                with open(self.last_sync_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Fehler beim Laden der Sync-Informationen: {str(e)}")
        
        # Standard-Werte, wenn keine Datei existiert
        return {
            "last_sync": None,
            "last_commit": None,
            "status": "Nie synchronisiert"
        }
    
    def _run_git_command(self, command: List[str]) -> Tuple[bool, str]:
        """Führe einen Git-Befehl aus und gib Erfolg und Ausgabe zurück."""
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git-Befehl fehlgeschlagen: {' '.join(command)}")
            logger.error(f"Fehler: {e.stderr.strip()}")
            return False, e.stderr.strip()
    
    def get_repository_info(self) -> Dict[str, Any]:
        """Hole Informationen über das Repository."""
        info = {
            "current_branch": "Unbekannt",
            "last_sync": "Nie",
            "open_issues": 0,
            "remote_url": "Nicht konfiguriert"
        }
        
        # Hole den aktuellen Branch
        success, branch_output = self._run_git_command(["git", "branch", "--show-current"])
        if success:
            info["current_branch"] = branch_output
        
        # Hole die Remote-URL
        success, remote_output = self._run_git_command(["git", "remote", "get-url", "origin"])
        if success:
            info["remote_url"] = remote_output
        
        # Hole Informationen zur letzten Synchronisation
        last_sync = self._load_last_sync()
        if last_sync.get("last_sync"):
            info["last_sync"] = last_sync["last_sync"]
        
        # Hole die Anzahl offener Issues von der GitHub API
        if self.config["repository"]:
            repo_parts = self.config["repository"].split("/")
            if len(repo_parts) == 2:
                owner, repo = repo_parts
                issues = self.get_open_issues_count(owner, repo)
                info["open_issues"] = issues
        
        return info
    
    def get_open_issues_count(self, owner: str, repo: str) -> int:
        """Hole die Anzahl offener Issues vom GitHub-Repository."""
        url = f"{self.api_base_url}/repos/{owner}/{repo}/issues?state=open&per_page=1"
        
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                # Extrahiere die Gesamtzahl aus dem Link-Header, wenn vorhanden
                link_header = response.headers.get("Link", "")
                if 'rel="last"' in link_header:
                    last_page_url = link_header.split('rel="last"')[0].split(",")[-1].strip()[1:-1]
                    from urllib.parse import parse_qs, urlparse
                    query_params = parse_qs(urlparse(last_page_url).query)
                    if "page" in query_params:
                        return int(query_params["page"][0])
                
                # Wenn keine Paginierung oder nur eine Seite vorhanden ist
                return len(response.json())
            else:
                logger.error(f"Fehler beim Abrufen der Issues: {response.status_code}")
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Issues: {str(e)}")
        
        return 0
    
    def get_recent_commits(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Hole die letzten Commits aus dem Repository."""
        commits = []
        
        success, output = self._run_git_command(["git", "log", f"-{limit}", "--pretty=format:%H|%an|%ad|%s", "--date=iso"])
        if success:
            for line in output.split("\n"):
                if line.strip():
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        commit_hash, author, date, message = parts
                        commits.append({
                            "hash": commit_hash[:7],  # Kurzer Hash
                            "author": author,
                            "date": date,
                            "message": message
                        })
        
        return commits
    
    def sync_repository(self) -> Tuple[bool, str]:
        """Synchronisiere das Repository mit dem Remote-Server."""
        logger.info("Starte Repository-Synchronisation")
        
        # Hole den aktuellen Branch
        success, branch_output = self._run_git_command(["git", "branch", "--show-current"])
        if not success:
            return False, f"Fehler beim Ermitteln des aktuellen Branches: {branch_output}"
        
        current_branch = branch_output
        logger.info(f"Aktueller Branch: {current_branch}")
        
        # Prüfe, ob es ungespeicherte Änderungen gibt
        success, status_output = self._run_git_command(["git", "status", "--porcelain"])
        if not success:
            return False, f"Fehler beim Prüfen des Repository-Status: {status_output}"
        
        has_changes = bool(status_output.strip())
        logger.info(f"Ungespeicherte Änderungen gefunden: {has_changes}")
        
        if has_changes:
            # Prüfe, ob es wichtige Änderungen gibt, die committet werden sollen
            important_dirs = ["scripts/monitoring", "config", "data/monitoring"]
            important_changes = False
            
            for dir_path in important_dirs:
                success, dir_status = self._run_git_command(["git", "status", "--porcelain", dir_path])
                if success and dir_status.strip():
                    important_changes = True
                    break
            
            if important_changes:
                logger.info("Wichtige Änderungen gefunden, erstelle Commit")
                
                # Füge Änderungen hinzu und committe sie
                self._run_git_command(["git", "add"] + important_dirs)
                commit_success, commit_output = self._run_git_command([
                    "git", "commit", "-m", 
                    f"Automatische Synchronisation - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ])
                
                if not commit_success:
                    return False, f"Fehler beim Erstellen des Commits: {commit_output}"
                
                logger.info(f"Commit erfolgreich erstellt: {commit_output}")
            else:
                logger.info("Keine wichtigen Änderungen gefunden, kein Commit notwendig")
        
        # Hole Änderungen vom Remote-Repository
        success, pull_output = self._run_git_command(["git", "pull", "origin", current_branch])
        if not success:
            if "diverged" in pull_output.lower():
                logger.warning("WARNUNG: Lokale und Remote-Änderungen divergieren")
                return False, "Lokale und Remote-Änderungen divergieren. Manuelles Eingreifen erforderlich."
            return False, f"Fehler beim Abrufen von Remote-Änderungen: {pull_output}"
        
        logger.info(f"Pull erfolgreich: {pull_output}")
        
        # Pushe Änderungen zum Remote-Repository
        if has_changes and "wichtige Änderungen gefunden" in locals():
            success, push_output = self._run_git_command(["git", "push", "origin", current_branch])
            if not success:
                return False, f"Fehler beim Pushen der Änderungen: {push_output}"
            
            logger.info(f"Push erfolgreich: {push_output}")
        
        # Speichere Informationen zur Synchronisation
        self._save_last_sync({
            "last_sync": datetime.datetime.now().isoformat(),
            "last_commit": self.get_recent_commits(1)[0] if self.get_recent_commits(1) else None,
            "status": "Erfolgreich"
        })
        
        logger.info("Repository-Synchronisation abgeschlossen")
        return True, "Repository erfolgreich synchronisiert"
    
    def push_monitoring_data(self) -> Tuple[bool, str]:
        """Pushe nur die Monitoring-Daten zum Repository."""
        logger.info("Pushe Monitoring-Daten zum Repository")
        
        monitoring_paths = [
            "data/monitoring/api_usage.json",
            "data/monitoring/backups"
        ]
        
        # Prüfe, ob die Dateien existieren
        for path in monitoring_paths:
            if not (self.repo_path / path).exists():
                continue
            
            # Füge die Monitoring-Dateien hinzu
            success, output = self._run_git_command(["git", "add", path])
            if not success:
                return False, f"Fehler beim Hinzufügen von {path}: {output}"
        
        # Prüfe, ob es Änderungen gibt
        success, status_output = self._run_git_command(["git", "status", "--porcelain"])
        if not success:
            return False, f"Fehler beim Prüfen des Repository-Status: {status_output}"
        
        if not status_output.strip():
            return True, "Keine Änderungen in den Monitoring-Daten gefunden"
        
        # Erstelle einen Commit
        commit_success, commit_output = self._run_git_command([
            "git", "commit", "-m", 
            f"Update Monitoring-Daten - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        if not commit_success:
            return False, f"Fehler beim Erstellen des Commits: {commit_output}"
        
        # Hole den aktuellen Branch
        success, branch_output = self._run_git_command(["git", "branch", "--show-current"])
        if not success:
            return False, f"Fehler beim Ermitteln des aktuellen Branches: {branch_output}"
        
        current_branch = branch_output
        
        # Pushe die Änderungen
        push_success, push_output = self._run_git_command(["git", "push", "origin", current_branch])
        if not push_success:
            return False, f"Fehler beim Pushen der Änderungen: {push_output}"
        
        logger.info(f"Monitoring-Daten erfolgreich gepusht: {push_output}")
        return True, "Monitoring-Daten erfolgreich zum Repository gepusht"
    
    def get_open_issues(self) -> List[Dict[str, Any]]:
        """Hole die offenen Issues vom GitHub-Repository."""
        issues = []
        
        if not self.config["repository"]:
            return issues
        
        repo_parts = self.config["repository"].split("/")
        if len(repo_parts) != 2:
            return issues
        
        owner, repo = repo_parts
        url = f"{self.api_base_url}/repos/{owner}/{repo}/issues?state=open"
        
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                for issue in response.json():
                    issues.append({
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "created_at": issue.get("created_at"),
                        "author": issue.get("user", {}).get("login")
                    })
            else:
                logger.error(f"Fehler beim Abrufen der Issues: {response.status_code}")
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Issues: {str(e)}")
        
        return issues
    
    def get_open_pull_requests(self) -> List[Dict[str, Any]]:
        """Hole die offenen Pull Requests vom GitHub-Repository."""
        pull_requests = []
        
        if not self.config["repository"]:
            return pull_requests
        
        repo_parts = self.config["repository"].split("/")
        if len(repo_parts) != 2:
            return pull_requests
        
        owner, repo = repo_parts
        url = f"{self.api_base_url}/repos/{owner}/{repo}/pulls?state=open"
        
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                for pr in response.json():
                    pull_requests.append({
                        "number": pr.get("number"),
                        "title": pr.get("title"),
                        "created_at": pr.get("created_at"),
                        "author": pr.get("user", {}).get("login"),
                        "branch": pr.get("head", {}).get("ref")
                    })
            else:
                logger.error(f"Fehler beim Abrufen der Pull Requests: {response.status_code}")
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Pull Requests: {str(e)}")
        
        return pull_requests

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