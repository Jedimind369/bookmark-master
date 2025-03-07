#!/usr/bin/env python3
"""
api_monitor.py

Eine Klasse zum Überwachen und Steuern der API-Kosten für verschiedene KI-Modelle.
Unterstützt Kostentracking, Budgetlimits und Warnmeldungen.
"""

import os
import json
import time
import logging
import platform
import requests
import datetime
import subprocess
import hashlib  # Für MD5-Checksummen
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import shutil
from datetime import datetime, timedelta

# Importiere Konfiguration
from scripts.monitoring.config import (
    MONITORING_DATA_DIR, 
    USAGE_FILE, 
    LOG_FILE,
    DEFAULT_BUDGET, 
    WARNING_THRESHOLDS,
    SLACK_WEBHOOK_URL,
    SLACK_ENABLED,
    HELICONE_API_KEY,
    HELICONE_ENABLED,
    OPENAI_API_KEY,
    OPENAI_ORG_ID,
    MONITORING_INTERVAL,
    MODEL_COSTS
)

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api_monitor")

class APIMonitor:
    """
    Überwacht und kontrolliert API-Kosten für verschiedene KI-Modelle.
    Unterstützt Kostentracking, Budgetlimits und Warnmeldungen.
    """
    
    def __init__(self, budget_limit: float = DEFAULT_BUDGET, warning_thresholds: List[float] = None):
        """
        Initialisiert den API-Monitor.
        
        Args:
            budget_limit: Budgetlimit in USD
            warning_thresholds: Liste von Schwellenwerten (0-1), bei denen Warnungen ausgegeben werden sollen
        """
        self.budget_limit = budget_limit
        self.warning_thresholds = warning_thresholds if warning_thresholds else WARNING_THRESHOLDS
        self.warning_thresholds.sort()  # Stellen Sie sicher, dass die Schwellenwerte in aufsteigender Reihenfolge sind
        self.triggered_warnings = set()  # Bereits ausgelöste Warnungen
        
        # Initialisiere die Datenverzeichnisse und -dateien
        MONITORING_DATA_DIR.mkdir(exist_ok=True, parents=True)
        self.usage_file = USAGE_FILE
        
        # Backup-Verzeichnis erstellen
        self.backup_dir = MONITORING_DATA_DIR / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Metadaten-Datei für Backups
        self.backup_metadata_file = self.backup_dir / "backup_metadata.json"
        
        # Maximale Anzahl täglicher Backups, die behalten werden sollen
        self.max_daily_backups = 7
        
        # Lade vorhandene Daten oder initialisiere neue
        self._init_data()
        
        # Flag um zu verfolgen, ob bereits Warnungen für bestimmte Schwellenwerte gesendet wurden
        self._warnings_sent = {threshold: False for threshold in self.warning_thresholds}
        
        # Initialer Budget-Check
        self._check_budget()
        
        logger.info(f"API-Monitor initialisiert. Budget-Limit: ${budget_limit:.2f}")
    
    def _init_data(self):
        """Lädt vorhandene Nutzungsdaten oder initialisiert neue."""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r') as f:
                    self.data = json.load(f)
                    logger.info(f"Nutzungsdaten geladen: {len(self.data.get('api_calls', []))} API-Aufrufe.")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Fehler beim Laden der Nutzungsdaten: {str(e)}. Neue Daten werden initialisiert.")
                self._create_new_data()
        else:
            self._create_new_data()
        
        # Überprüfen, ob ein tägliches Backup erforderlich ist
        self._check_and_create_daily_backup()
    
    def _create_new_data(self):
        """Erstellt eine neue Datenstruktur für die API-Nutzungsverfolgung."""
        self.data = {
            "start_date": datetime.now().isoformat(),
            "budget_limit": self.budget_limit,
            "total_cost": 0.0,
            "api_calls": [],
            "models": {},
            "tasks": {},
            "context_info": {}
        }
        self._save_data()
        logger.info("Neue Nutzungsdaten initialisiert.")
    
    def _save_data(self):
        """Speichert die Nutzungsdaten in der Datei und erstellt bei Bedarf ein Backup."""
        try:
            # Temporäre Datei zum sicheren Speichern
            temp_file = f"{self.usage_file}.tmp"
            
            # Zuerst in eine temporäre Datei schreiben
            with open(temp_file, 'w') as f:
                json.dump(self.data, f, indent=2)
                
            # Dann die temporäre Datei an den endgültigen Speicherort verschieben
            shutil.move(temp_file, self.usage_file)
            
            logger.debug(f"Nutzungsdaten erfolgreich gespeichert: {self.usage_file}")
            
            # Prüfen, ob ein Backup erforderlich ist
            self._check_and_create_daily_backup()
            
        except IOError as e:
            logger.error(f"Fehler beim Speichern der Nutzungsdaten: {str(e)}")
            
            # Versuchen, aus dem letzten Backup wiederherzustellen, wenn das Speichern fehlschlägt
            if self._has_recent_backup():
                self.restore_from_backup()
    
    def _check_and_create_daily_backup(self):
        """Überprüft, ob heute bereits ein Backup erstellt wurde und erstellt bei Bedarf eines."""
        today = datetime.now().date().isoformat()
        
        # Metadaten laden oder initialisieren
        metadata = self._load_backup_metadata()
        
        # Prüfen, ob heute bereits ein Backup erstellt wurde
        if metadata.get('last_backup_date') != today:
            # Entscheide, ob ein vollständiges oder inkrementelles Backup erstellt werden soll
            if not metadata.get('backups'):
                # Erstes Backup ist immer vollständig
                success = self._create_backup(incremental=False)
            else:
                # Für spätere Backups, inkrementell speichern
                success = self._create_backup(incremental=True)
            
            if success:
                # Metadaten aktualisieren
                metadata['last_backup_date'] = today
                metadata['backup_count'] = metadata.get('backup_count', 0) + 1
                
                # Backup-Typ und Referenzdaten ermitteln
                backup_type = "incremental" if (metadata.get('backups') and len(metadata['backups']) > 0) else "full"
                base_backup = metadata['backups'][-1]['file'] if (backup_type == "incremental" and metadata.get('backups')) else None
                
                backup_file = self.backup_dir / f"api_usage_backup_{today}_{backup_type}.json"
                
                metadata['backups'].append({
                    'date': today,
                    'file': os.path.basename(backup_file),
                    'type': backup_type,
                    'base_backup': base_backup,
                    'size': os.path.getsize(backup_file),
                    'total_cost': self.data['total_cost']
                })
                
                # Alte Backups entfernen, wenn die maximale Anzahl überschritten wird
                self._cleanup_old_backups(metadata)
                
                # Metadaten speichern
                self._save_backup_metadata(metadata)
    
    def _load_backup_metadata(self) -> Dict:
        """Lädt die Backup-Metadaten oder erstellt sie, wenn sie nicht existieren."""
        if os.path.exists(self.backup_metadata_file):
            try:
                with open(self.backup_metadata_file, 'r') as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"Fehler beim Laden der Backup-Metadaten: {str(e)}")
        
        # Standardmetadaten zurückgeben, wenn keine existieren
        return {
            'last_backup_date': None,
            'backup_count': 0,
            'backups': []
        }
    
    def _save_backup_metadata(self, metadata: Dict):
        """Speichert die Backup-Metadaten."""
        try:
            with open(self.backup_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except IOError as e:
            logger.error(f"Fehler beim Speichern der Backup-Metadaten: {str(e)}")
    
    def _create_backup(self, incremental=False):
        """
        Erstellt ein Backup der aktuellen Nutzungsdaten mit Integritätsprüfung.
        
        Args:
            incremental: Ob ein inkrementelles Backup erstellt werden soll.
        
        Returns:
            bool: True, wenn das Backup erfolgreich erstellt wurde.
        """
        today = datetime.now().date().isoformat()
        
        # Bestimme den Backup-Typ für den Dateinamen
        backup_type = "incremental" if incremental else "full"
        backup_file = self.backup_dir / f"api_usage_backup_{today}_{backup_type}.json"
        
        try:
            if incremental:
                # Inkrementelles Backup: Nur Änderungen speichern
                last_backup_file = self._get_last_full_backup()
                if last_backup_file and os.path.exists(last_backup_file):
                    try:
                        # Lade das letzte vollständige Backup
                        with open(last_backup_file, 'r') as f:
                            base_data = json.load(f)
                        
                        # Erstelle ein Dictionary mit den Änderungen
                        incremental_data = {
                            "backup_type": "incremental",
                            "base_backup": os.path.basename(last_backup_file),
                            "timestamp": datetime.now().isoformat(),
                            "changes": self._compute_data_diff(base_data)
                        }
                        
                        # Speichere die inkrementellen Änderungen
                        with open(backup_file, 'w') as f:
                            json.dump(incremental_data, f, indent=2)
                            
                        # Erstelle eine Prüfsumme
                        self._create_checksum(backup_file)
                        
                        # Synchronisiere mit GitHub, wenn aktiviert
                        self._sync_with_github(backup_file)
                        
                        logger.info(f"Inkrementelles Backup erstellt: {backup_file}")
                        return True
                    except Exception as e:
                        logger.error(f"Fehler beim Erstellen des inkrementellen Backups: {str(e)}")
                        # Fallback auf vollständiges Backup
                        return self._create_full_backup()
                else:
                    # Kein Basis-Backup gefunden, erstelle ein vollständiges Backup
                    logger.warning("Kein Basis-Backup für inkrementelles Backup gefunden, erstelle vollständiges Backup")
                    return self._create_full_backup()
            else:
                # Vollständiges Backup
                return self._create_full_backup()
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Backups: {str(e)}")
            return False
    
    def _create_full_backup(self):
        """Erstellt ein vollständiges Backup der aktuellen Nutzungsdaten."""
        today = datetime.now().date().isoformat()
        backup_file = self.backup_dir / f"api_usage_backup_{today}_full.json"
        
        try:
            # Kopiere die aktuelle Datei ins Backup
            shutil.copy2(self.usage_file, backup_file)
            
            # Erstelle eine MD5-Prüfsumme für das Backup
            self._create_checksum(backup_file)
            
            # Synchronisiere mit GitHub, wenn aktiviert
            self._sync_with_github(backup_file)
            
            logger.info(f"Vollständiges Backup erstellt: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des vollständigen Backups: {str(e)}")
            return False
    
    def _create_checksum(self, file_path):
        """Erstellt eine MD5-Prüfsumme für eine Datei und speichert sie."""
        try:
            checksum_file = str(file_path) + ".md5"
            
            # Generiere MD5-Hash
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                # Lese die Datei in Chunks, um den Speicherverbrauch zu reduzieren
                chunk = f.read(8192)
                while chunk:
                    file_hash.update(chunk)
                    chunk = f.read(8192)
            
            # Speichere die Prüfsumme in einer separaten Datei
            with open(checksum_file, 'w') as f:
                f.write(file_hash.hexdigest())
            
            return True
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Prüfsumme für {file_path}: {str(e)}")
            return False
    
    def _compute_data_diff(self, base_data):
        """
        Berechnet den Unterschied zwischen dem aktuellen Datenstand und einem Basis-Datensatz.
        
        Args:
            base_data: Der Basis-Datensatz, gegen den die Differenz berechnet wird.
            
        Returns:
            Dict: Ein Dictionary mit den Änderungen
        """
        diff = {}
        
        # Identifiziere geänderte Top-Level-Felder
        for key, value in self.data.items():
            if key not in base_data:
                # Neues Feld
                diff[key] = value
            elif key == "api_calls":
                # Für API-Aufrufe nur die neuen Einträge speichern
                base_calls_count = len(base_data.get("api_calls", []))
                current_calls = self.data.get("api_calls", [])
                
                if len(current_calls) > base_calls_count:
                    # Es gibt neue Aufrufe, speichere nur diese
                    diff["api_calls"] = current_calls[base_calls_count:]
            elif isinstance(value, dict) and isinstance(base_data[key], dict):
                # Für verschachtelte Dictionaries (Modelle, Aufgaben)
                nested_diff = {}
                
                for nested_key, nested_value in value.items():
                    if nested_key not in base_data[key]:
                        # Neuer Schlüssel
                        nested_diff[nested_key] = nested_value
                    elif nested_value != base_data[key][nested_key]:
                        # Geänderter Wert
                        nested_diff[nested_key] = nested_value
                        
                if nested_diff:
                    diff[key] = nested_diff
            elif value != base_data[key]:
                # Einfacher geänderter Wert
                diff[key] = value
        
        return diff
    
    def _get_last_full_backup(self):
        """
        Findet das letzte vollständige Backup.
        
        Returns:
            str: Pfad zum letzten vollständigen Backup oder None
        """
        metadata = self._load_backup_metadata()
        backups = metadata.get('backups', [])
        
        # Durchlaufe die Backups rückwärts, um das neueste vollständige Backup zu finden
        for backup in reversed(backups):
            if backup.get('type') == 'full':
                backup_path = self.backup_dir / backup['file']
                if os.path.exists(backup_path):
                    return backup_path
        
        return None
    
    def _verify_backup_integrity(self, backup_path):
        """Überprüft die Integrität eines Backups anhand der MD5-Prüfsumme."""
        try:
            checksum_file = str(backup_path) + ".md5"
            
            # Prüfe, ob die Checksum-Datei existiert
            if not os.path.exists(checksum_file):
                logger.warning(f"Keine Prüfsumme für Backup {backup_path} gefunden")
                return False
            
            # Lade die gespeicherte Prüfsumme
            with open(checksum_file, 'r') as f:
                stored_checksum = f.read().strip()
            
            # Berechne die aktuelle Prüfsumme
            with open(backup_path, 'rb') as f:
                file_hash = hashlib.md5()
                chunk = f.read(8192)
                while chunk:
                    file_hash.update(chunk)
                    chunk = f.read(8192)
            
            current_checksum = file_hash.hexdigest()
            
            # Vergleiche die Prüfsummen
            if stored_checksum == current_checksum:
                return True
            else:
                logger.error(f"Integritätsprüfung fehlgeschlagen für {backup_path}. "
                             f"Gespeichert: {stored_checksum}, Aktuell: {current_checksum}")
                return False
            
        except Exception as e:
            logger.error(f"Fehler bei der Integritätsprüfung für {backup_path}: {str(e)}")
            return False
    
    def _cleanup_old_backups(self, metadata: Dict):
        """Entfernt alte Backups, wenn die maximale Anzahl überschritten wird."""
        backups = metadata.get('backups', [])
        
        # Wenn wir mehr Backups haben als erlaubt
        if len(backups) > self.max_daily_backups:
            # Sortieren nach Datum (älteste zuerst)
            backups.sort(key=lambda x: x['date'])
            
            # Die ältesten entfernen
            for old_backup in backups[:(len(backups) - self.max_daily_backups)]:
                backup_path = self.backup_dir / old_backup['file']
                try:
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                        logger.info(f"Altes Backup entfernt: {backup_path}")
                except IOError as e:
                    logger.error(f"Fehler beim Entfernen eines alten Backups: {str(e)}")
            
            # Metadaten aktualisieren
            metadata['backups'] = backups[(len(backups) - self.max_daily_backups):]
    
    def _has_recent_backup(self) -> bool:
        """Überprüft, ob ein kürzlich erstelltes Backup existiert."""
        metadata = self._load_backup_metadata()
        backups = metadata.get('backups', [])
        
        if not backups:
            return False
            
        # Prüfen, ob das letzte Backup innerhalb der letzten 24 Stunden liegt
        last_backup = backups[-1]
        backup_date = datetime.fromisoformat(last_backup['date'])
        now = datetime.now()
        
        return (now.date() - backup_date.date()) < timedelta(days=1)
    
    def restore_from_backup(self, specific_date: str = None) -> bool:
        """
        Stellt Daten aus einem Backup wieder her.
        
        Args:
            specific_date: Optional. Das Datum des Backups im Format 'YYYY-MM-DD'. 
                           Wenn nicht angegeben, wird das neueste Backup verwendet.
                           
        Returns:
            bool: True, wenn die Wiederherstellung erfolgreich war, sonst False.
        """
        metadata = self._load_backup_metadata()
        backups = metadata.get('backups', [])
        
        if not backups:
            logger.error("Keine Backups gefunden für die Wiederherstellung")
            return False
        
        # Backup auswählen (entweder das angegebene oder das neueste)
        target_backup = None
        if specific_date:
            for backup in backups:
                if backup['date'] == specific_date:
                    target_backup = backup
                    break
            
            if not target_backup:
                logger.error(f"Kein Backup für das Datum {specific_date} gefunden")
                return False
        else:
            # Neuestes Backup auswählen
            target_backup = backups[-1]
        
        backup_path = self.backup_dir / target_backup['file']
        
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup-Datei nicht gefunden: {backup_path}")
                return False
            
            # Prüfe die Integrität des Backups vor der Wiederherstellung
            if not self._verify_backup_integrity(backup_path):
                logger.error(f"Integritätsprüfung fehlgeschlagen für {backup_path}. Wiederherstellung abgebrochen.")
                return False
            
            # Verarbeitung basierend auf dem Backup-Typ
            if target_backup.get('type') == 'incremental':
                # Für inkrementelle Backups müssen wir das Basis-Backup laden und dann die Änderungen anwenden
                logger.info(f"Inkrementelles Backup gefunden, wende Änderungen auf Basis-Backup an")
                
                # Lade das inkrementelle Backup
                with open(backup_path, 'r') as f:
                    incremental_data = json.load(f)
                
                # Finde das Basis-Backup
                base_backup_name = incremental_data.get('base_backup')
                if not base_backup_name:
                    logger.error("Inkrementelles Backup ohne Basis-Backup-Referenz")
                    return False
                    
                base_backup_path = self.backup_dir / base_backup_name
                if not os.path.exists(base_backup_path):
                    logger.error(f"Basis-Backup nicht gefunden: {base_backup_path}")
                    return False
                    
                # Prüfe die Integrität des Basis-Backups
                if not self._verify_backup_integrity(base_backup_path):
                    logger.error(f"Integritätsprüfung des Basis-Backups fehlgeschlagen: {base_backup_path}")
                    return False
                    
                # Lade das Basis-Backup
                with open(base_backup_path, 'r') as f:
                    self.data = json.load(f)
                    
                # Wende die inkrementellen Änderungen an
                changes = incremental_data.get('changes', {})
                self._apply_incremental_changes(changes)
                
            else:
                # Für vollständige Backups einfach die Daten laden
                with open(backup_path, 'r') as f:
                    self.data = json.load(f)
            
            # Aktualisierte Daten speichern
            with open(self.usage_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            
            logger.info(f"Daten erfolgreich aus Backup vom {target_backup['date']} wiederhergestellt")
            return True
            
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Fehler bei der Wiederherstellung aus dem Backup: {str(e)}")
            return False
    
    def _apply_incremental_changes(self, changes):
        """
        Wendet inkrementelle Änderungen auf den aktuellen Datenstand an.
        
        Args:
            changes: Dictionary mit den Änderungen aus dem inkrementellen Backup
        """
        for key, value in changes.items():
            if key == "api_calls" and isinstance(value, list):
                # Für API-Aufrufe, füge die neuen hinzu
                if "api_calls" not in self.data:
                    self.data["api_calls"] = []
                self.data["api_calls"].extend(value)
            elif isinstance(value, dict) and isinstance(self.data.get(key), dict):
                # Für verschachtelte Dictionaries (Modelle, Aufgaben)
                for nested_key, nested_value in value.items():
                    self.data[key][nested_key] = nested_value
            else:
                # Einfacher Wert
                self.data[key] = value
        
        logger.info("Inkrementelle Änderungen erfolgreich angewendet")
    
    def list_available_backups(self) -> List[Dict]:
        """
        Listet alle verfügbaren Backups auf.
        
        Returns:
            List[Dict]: Eine Liste von Dictionaries mit Informationen zu jedem Backup.
        """
        metadata = self._load_backup_metadata()
        return metadata.get('backups', [])
    
    def check_openai_usage(self) -> Dict[str, Any]:
        """
        Überprüft die aktuelle OpenAI API-Nutzung direkt über die OpenAI API.
        
        Returns:
            Ein Dictionary mit den Nutzungsdaten oder leeres Dictionary bei Fehler
        """
        if not OPENAI_API_KEY or not OPENAI_ORG_ID:
            logger.warning("OpenAI API-Schlüssel oder Organisations-ID fehlt. Kann Nutzung nicht überprüfen.")
            return {}
        
        try:
            # Aktuellen Monat und Jahr für den Datumsbereich bestimmen
            now = datetime.datetime.now()
            start_date = datetime.datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
            
            # API-Anfrage an OpenAI
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Organization": OPENAI_ORG_ID
            }
            
            response = requests.get(
                f"https://api.openai.com/v1/usage?start_date={start_date}&end_date={end_date}",
                headers=headers
            )
            
            if response.status_code == 200:
                usage_data = response.json()
                
                # Gesamtkosten berechnen
                total_cost = usage_data.get("total_usage", 0) / 100  # OpenAI gibt Beträge in Cent zurück
                
                # Prüfen Sie Budget-Schwellenwerte
                usage_ratio = total_cost / self.budget_limit
                
                for threshold in self.warning_thresholds:
                    if usage_ratio >= threshold and threshold not in self.triggered_warnings:
                        self.triggered_warnings.add(threshold)
                        percentage = int(threshold * 100)
                        message = f"⚠️ WARNUNG: OpenAI API-Kosten haben {percentage}% des Budgets erreicht (${total_cost:.2f} von ${self.budget_limit:.2f})"
                        self.send_alert(message)
                
                logger.info(f"OpenAI API-Nutzung überprüft. Aktuelle Kosten: ${total_cost:.2f}")
                return usage_data
            else:
                logger.error(f"Fehler bei der OpenAI API-Anfrage: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Fehler bei der Überprüfung der OpenAI API-Nutzung: {str(e)}")
            return {}
    
    def record_api_call(self, model: str, cost: float, tokens_in: int = 0, tokens_out: int = 0, task: str = "default"):
        """
        Zeichnet einen API-Aufruf auf und aktualisiert die Nutzungsdaten.
        
        Args:
            model: Name des verwendeten Modells
            cost: Kosten des API-Aufrufs in USD
            tokens_in: Anzahl der Eingabe-Tokens
            tokens_out: Anzahl der Ausgabe-Tokens
            task: Name der Aufgabe/des Projekts
        """
        timestamp = datetime.datetime.now().isoformat()
        
        # Neuen API-Aufruf hinzufügen
        api_call = {
            "timestamp": timestamp,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost": cost,
            "task": task
        }
        self.data["api_calls"].append(api_call)
        
        # Gesamtkosten aktualisieren
        self.data["total_cost"] += cost
        
        # Modellspezifische Daten aktualisieren
        if model not in self.data["models"]:
            self.data["models"][model] = {
                "calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost": 0.0
            }
        
        self.data["models"][model]["calls"] += 1
        self.data["models"][model]["tokens_in"] += tokens_in
        self.data["models"][model]["tokens_out"] += tokens_out
        self.data["models"][model]["cost"] += cost
        
        # Aufgabenspezifische Daten aktualisieren
        if task not in self.data["tasks"]:
            self.data["tasks"][task] = {
                "calls": 0,
                "cost": 0.0
            }
        
        self.data["tasks"][task]["calls"] += 1
        self.data["tasks"][task]["cost"] += cost
        
        # Daten speichern
        self._save_data()
        
        # Budget-Warnungen prüfen
        total_cost = self.data["total_cost"]
        usage_ratio = total_cost / self.budget_limit
        
        for threshold in self.warning_thresholds:
            if usage_ratio >= threshold and threshold not in self.triggered_warnings:
                self.triggered_warnings.add(threshold)
                percentage = int(threshold * 100)
                message = f"⚠️ WARNUNG: API-Kosten haben {percentage}% des Budgets erreicht (${total_cost:.2f} von ${self.budget_limit:.2f})"
                logger.warning(message)
                self.send_alert(message)
        
        # Bei Budgetüberschreitung
        if total_cost > self.budget_limit:
            message = f"🛑 KRITISCH: Budget überschritten! Aktuelle Kosten: ${total_cost:.2f}, Budget: ${self.budget_limit:.2f}"
            logger.critical(message)
            self.send_alert(message)
        
        logger.debug(f"API-Aufruf aufgezeichnet: {model}, ${cost:.4f}, Aufgabe: {task}")
    
    def send_alert(self, message: str):
        """
        Sendet eine Benachrichtigung über Desktop-Benachrichtigung und optional über Slack.
        
        Args:
            message: Die Nachricht, die gesendet werden soll
        """
        # Desktop-Benachrichtigung
        try:
            self._send_desktop_notification("API Budget Alert", message)
        except Exception as e:
            logger.error(f"Fehler beim Senden der Desktop-Benachrichtigung: {str(e)}")
        
        # Slack-Benachrichtigung, falls konfiguriert
        if SLACK_ENABLED:
            try:
                payload = {
                    "text": message,
                    "channel": SLACK_CHANNEL
                }
                response = requests.post(SLACK_WEBHOOK_URL, json=payload)
                if response.status_code != 200:
                    logger.error(f"Fehler beim Senden der Slack-Benachrichtigung: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Fehler beim Senden der Slack-Benachrichtigung: {str(e)}")
    
    def _send_desktop_notification(self, title: str, message: str):
        """
        Sendet eine Desktop-Benachrichtigung, abhängig vom Betriebssystem.
        
        Args:
            title: Titel der Benachrichtigung
            message: Inhalt der Benachrichtigung
        """
        system = platform.system()
        
        try:
            if system == "Darwin":  # macOS
                # Escapen Sie die Anführungszeichen im Titel und in der Nachricht
                escaped_title = title.replace('"', '\\"')
                escaped_message = message.replace('"', '\\"')
                subprocess.run(['osascript', '-e', f'display notification "{escaped_message}" with title "{escaped_title}"'])
            
            elif system == "Linux":
                subprocess.run(['notify-send', title, message])
            
            elif system == "Windows":
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=10)
            
            else:
                logger.warning(f"Desktop-Benachrichtigungen werden auf {system} nicht unterstützt.")
        
        except Exception as e:
            logger.error(f"Fehler beim Senden der Desktop-Benachrichtigung: {str(e)}")
    
    def show_usage(self, detailed: bool = False):
        """
        Zeigt eine Übersicht der API-Kosten und Nutzungsstatistik.
        
        Args:
            detailed: Ob detaillierte Informationen angezeigt werden sollen
        """
        total_cost = self.data["total_cost"]
        total_calls = len(self.data["api_calls"])
        
        print("\n" + "="*60)
        print(f"API-NUTZUNGSSTATISTIK (Stand: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        print("="*60)
        
        print(f"\nGesamtkosten: ${total_cost:.2f} von ${self.budget_limit:.2f} ({total_cost/self.budget_limit*100:.1f}%)")
        print(f"Gesamtaufrufe: {total_calls}")
        
        print("\nKosten pro Modell:")
        print("-"*60)
        for model, stats in self.data["models"].items():
            model_desc = MODEL_COSTS.get(model, {}).get("description", model)
            print(f"{model_desc}: ${stats['cost']:.2f} ({stats['calls']} Aufrufe, {stats['tokens_in']:,} In-Tokens, {stats['tokens_out']:,} Out-Tokens)")
        
        print("\nKosten pro Aufgabe:")
        print("-"*60)
        for task, stats in self.data["tasks"].items():
            print(f"{task}: ${stats['cost']:.2f} ({stats['calls']} Aufrufe)")
        
        # Detaillierte Statistik
        if detailed and total_calls > 0:
            print("\nLetzten 5 API-Aufrufe:")
            print("-"*60)
            recent_calls = sorted(self.data["api_calls"], key=lambda x: x["timestamp"], reverse=True)[:5]
            
            for call in recent_calls:
                timestamp = datetime.datetime.fromisoformat(call["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                print(f"{timestamp} - {call['model']} - ${call['cost']:.4f} - {call['task']}")
        
        print("\n" + "="*60)

    def _check_budget(self):
        """Überprüft, ob das Budget überschritten wurde oder Schwellenwerte erreicht wurden."""
        if not self.data:
            return
            
        total_cost = self.data['total_cost']
        percentage_used = (total_cost / self.budget_limit) * 100
        
        # Budget überschritten?
        if total_cost > self.budget_limit and not self._warnings_sent.get(100):
            message = f"⚠️ BUDGET ÜBERSCHRITTEN: ${total_cost:.2f} von ${self.budget_limit:.2f} (100%+)"
            self.send_alert(message)
            self._warnings_sent[100] = True
            logger.warning(message)
            
        # Schwellenwerte prüfen
        for threshold in sorted(self.warning_thresholds):
            threshold_value = self.budget_limit * (threshold / 100)
            if total_cost >= threshold_value and not self._warnings_sent.get(threshold):
                message = f"⚠️ Budget-Warnung: ${total_cost:.2f} von ${self.budget_limit:.2f} ({threshold}% des Limits)"
                self.send_alert(message)
                self._warnings_sent[threshold] = True
                logger.warning(message)

    def store_context_information(self, key: str, value: Any) -> None:
        """
        Speichert wichtige Kontextinformationen, die später abgerufen werden können.
        
        Diese Methode ermöglicht es, wichtige Systeminformationen zu persistieren, damit
        sie über verschiedene Sitzungen hinweg erhalten bleiben.
        
        Args:
            key: Der Schlüssel für die Information
            value: Der zu speichernde Wert (muss JSON-serialisierbar sein)
        """
        if 'context_info' not in self.data:
            self.data['context_info'] = {}
        
        self.data['context_info'][key] = value
        self._save_data()
        logger.info(f"Kontextinformation gespeichert: {key}")

    def get_context_information(self, key: str, default: Any = None) -> Any:
        """
        Ruft gespeicherte Kontextinformationen ab.
        
        Args:
            key: Der Schlüssel für die Information
            default: Standardwert, falls der Schlüssel nicht existiert
            
        Returns:
            Der gespeicherte Wert oder der Standardwert
        """
        if not self.data.get('context_info'):
            return default
        
        return self.data['context_info'].get(key, default)

    def list_all_context_information(self) -> Dict[str, Any]:
        """
        Listet alle gespeicherten Kontextinformationen auf.
        
        Returns:
            Ein Dictionary mit allen gespeicherten Kontextinformationen
        """
        return self.data.get('context_info', {})

    def _sync_with_github(self, backup_file: Path) -> bool:
        """
        Synchronisiert ein Backup mit GitHub, wenn die GitHub-Synchronisation aktiviert ist.
        
        Args:
            backup_file: Pfad zur Backup-Datei
            
        Returns:
            bool: True, wenn die Synchronisation erfolgreich war oder nicht aktiviert ist
        """
        try:
            # Prüfe, ob GitHub-Synchronisation aktiviert ist
            github_sync = self.get_context_information("github_sync_instance")
            if github_sync:
                logger.info(f"Synchronisiere Backup {backup_file.name} mit GitHub")
                return github_sync.sync_backup(backup_file, push=False)
            return True
        except Exception as e:
            logger.error(f"Fehler bei der GitHub-Synchronisation: {str(e)}")
            return False

def monitor_loop(interval: int = MONITORING_INTERVAL):
    """
    Überwacht kontinuierlich die API-Kosten in einem Loop.
    
    Args:
        interval: Zeit zwischen den Überprüfungen in Sekunden
    """
    monitor = APIMonitor()
    logger.info(f"API-Kostenüberwachung gestartet. Intervall: {interval}s")
    
    try:
        while True:
            # Prüfe OpenAI API-Nutzung (für gpt4o_mini)
            monitor.check_openai_usage()
            
            # Zeige aktuelle Nutzung
            monitor.show_usage()
            
            # Warte bis zur nächsten Überprüfung
            time.sleep(interval)
            
    except KeyboardInterrupt:
        logger.info("API-Kostenüberwachung beendet.")
    except Exception as e:
        logger.error(f"Fehler in der Überwachungsschleife: {str(e)}")

if __name__ == "__main__":
    # Starte Überwachungsschleife
    monitor_loop() 