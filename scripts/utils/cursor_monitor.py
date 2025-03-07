#!/usr/bin/env python3

"""
cursor_monitor.py - Version 2.1

Überwacht den Status von Cursor-Chats und erkennt Stillstand.
Verwendet ausschließlich angenehme Systemtöne und kann einfach ein-/ausgeschaltet werden.
KEINE SPRACHAUSGABE - NUR SYSTEMTÖNE!
"""

import os
import sys
import time
import subprocess
import psutil
import platform
from pathlib import Path
import datetime
import argparse
import json
import signal

# Konfigurationsdatei
CONFIG_FILE = Path.home() / ".cursor_monitor_config.json"

# Standard-Konfiguration
DEFAULT_CONFIG = {
    "enabled": True,                # Monitor aktiviert/deaktiviert
    "check_interval": 30,           # Intervall in Sekunden für die Überprüfung (30s)
    "cursor_process_names": ["cursor", "Cursor", "cursor.app", "Cursor.app"],  # Mögliche Prozessnamen für Cursor
    "inactivity_threshold": 10,     # Zeit in Sekunden, nach der Cursor-Chat als inaktiv gilt
    "debug": True,                  # Debug-Ausgaben aktiviert
    "sound_enabled": True,          # Tonausgabe aktiviert
    "network_threshold": 100,       # Schwellenwert für Netzwerkaktivität in Bytes/s
    "last_status": "unknown",       # Letzter bekannter Status
    "notification_interval": 120,   # Nur alle 120 Sekunden benachrichtigen
    "cpu_threshold": 90,            # CPU-Schwellenwert in Prozent für Blockierung
}

# Pfade für Sounddateien
SCRIPT_DIR = Path(__file__).parent
SOUNDS_DIR = SCRIPT_DIR / "sounds"
SOUNDS_DIR.mkdir(exist_ok=True)

# Status-Datei für Toggle
STATUS_FILE = Path.home() / ".cursor_monitor_status"

# Lade Konfiguration
CONFIG = DEFAULT_CONFIG.copy()

def load_config():
    """Lädt die Konfiguration aus der Datei."""
    global CONFIG
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                CONFIG.update(user_config)
                log(f"Konfiguration geladen: {CONFIG_FILE}")
    except Exception as e:
        log(f"Fehler beim Laden der Konfiguration: {e}")

def save_config():
    """Speichert die Konfiguration in der Datei."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(CONFIG, f, indent=2)
            log(f"Konfiguration gespeichert: {CONFIG_FILE}")
    except Exception as e:
        log(f"Fehler beim Speichern der Konfiguration: {e}")

# Logging-Funktion
def log(message):
    """Gibt eine Nachricht mit Zeitstempel aus, wenn Debug aktiviert ist."""
    if CONFIG["debug"]:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

# Einfacher Toggle-Mechanismus
def toggle_monitor():
    """Schaltet den Monitor ein oder aus."""
    if STATUS_FILE.exists():
        STATUS_FILE.unlink()
        log("Monitor deaktiviert")
        return False
    else:
        STATUS_FILE.touch()
        log("Monitor aktiviert")
        return True

def is_monitor_enabled():
    """Prüft, ob der Monitor aktiviert ist."""
    return STATUS_FILE.exists()

class CursorMonitor:
    """Überwacht den Status von Cursor-Chats und erkennt Stillstand."""
    
    def __init__(self):
        """Initialisiere den Monitor."""
        self.cursor_status = "unknown"
        self.last_check_time = 0
        self.last_activity_time = time.time()
        self.cursor_pid = None
        self.running = True
        self.last_network_io = None
        self.last_network_check = time.time()
        self.network_activity_history = []  # Speichert die letzten Netzwerkaktivitätswerte
        self.last_network_bytes = 0
        self.last_significant_network_activity = 0
        self.last_status_announcement = 0  # Initialisiere mit 0, damit erste Benachrichtigung sofort erfolgt
        self.last_cpu_check = 0
        self.cpu_history = []
        self.activity_status_history = []  # Speichert die letzten Aktivitätsstatus
        self.consecutive_inactive_count = 0  # Zählt aufeinanderfolgende Inaktivitätserkennungen
        
        # Aktiviere den Monitor beim Start
        if not STATUS_FILE.exists():
            STATUS_FILE.touch()
        
        # Initialisiere Sound-System
        self.system_sound_available = False
        
        if platform.system() == "Darwin":  # macOS
            self.system_sound_available = True
            log("macOS-Soundausgabe aktiviert.")
            
            # Erstelle Beispiel-Sounddateien mit angenehmen Systemtönen
            self._create_system_sound_file("active", "Tink.aiff")
            self._create_system_sound_file("inactive", "Basso.aiff")
            self._create_system_sound_file("not_running", "Submarine.aiff")
        elif platform.system() == "Windows":
            try:
                import winsound
                self.system_sound_available = True
                log("Windows-Soundausgabe aktiviert.")
            except ImportError:
                log("Winsound nicht verfügbar.")
        elif platform.system() == "Linux":
            # Prüfe, ob aplay verfügbar ist
            try:
                subprocess.run(["which", "aplay"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.system_sound_available = True
                log("Linux-Soundausgabe (aplay) aktiviert.")
            except subprocess.SubprocessError:
                log("aplay nicht verfügbar.")
        
        if not self.system_sound_available:
            log("Keine Soundausgabe verfügbar. Akustische Benachrichtigungen deaktiviert.")
    
    def _create_system_sound_file(self, status, system_sound):
        """Erstellt eine Sounddatei mit einem angenehmen Systemton."""
        try:
            if platform.system() == "Darwin":  # macOS
                sound_file = SOUNDS_DIR / f"{status}.wav"
                # Kopiere Systemton
                subprocess.run(["cp", f"/System/Library/Sounds/{system_sound}", str(sound_file)], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                log(f"Systemton kopiert: {system_sound} -> {sound_file}")
        except Exception as e:
            log(f"Fehler beim Erstellen der Sounddatei: {e}")
    
    def play_sound(self, status):
        """Spielt einen Ton ab, abhängig vom Status."""
        if not self.system_sound_available or not CONFIG["sound_enabled"]:
            return
        
        # Prüfe, ob seit der letzten Benachrichtigung genug Zeit vergangen ist
        current_time = time.time()
        time_since_last_announcement = current_time - self.last_status_announcement
        
        # Nur benachrichtigen, wenn der Status sich geändert hat oder das Intervall überschritten wurde
        if status == self.cursor_status and time_since_last_announcement < CONFIG["notification_interval"]:
            return
        
        # Bei inaktivem Status oder nicht laufendem Cursor immer benachrichtigen
        # Bei aktivem Status nur in regelmäßigen Abständen benachrichtigen
        if status != "active" or time_since_last_announcement >= CONFIG["notification_interval"]:
            self.last_status_announcement = current_time
            
            try:
                if platform.system() == "Darwin":  # macOS
                    # Systemtöne direkt abspielen
                    if status == "active":
                        subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    elif status == "inactive":
                        subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff"], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:  # not_running
                        subprocess.run(["afplay", "/System/Library/Sounds/Submarine.aiff"], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    log(f"Ton abgespielt für: {status}")
                elif platform.system() == "Windows":
                    # Windows-Systemtöne
                    import winsound
                    if status == "active":
                        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
                    elif status == "inactive":
                        winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
                    else:  # not_running
                        winsound.PlaySound("SystemQuestion", winsound.SND_ALIAS)
                    log(f"Ton abgespielt für: {status}")
                elif platform.system() == "Linux":
                    # Linux-Töne (falls verfügbar)
                    sound_file = SOUNDS_DIR / f"{status}.wav"
                    if sound_file.exists():
                        subprocess.run(["aplay", str(sound_file)], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        log(f"Ton abgespielt für: {status}")
            except Exception as e:
                log(f"Fehler beim Abspielen des Tons: {e}")
    
    def find_cursor_process(self):
        """Findet den Cursor-Prozess und gibt seine PID zurück."""
        cursor_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Prüfe den Prozessnamen
                proc_name = proc.info['name'].lower() if proc.info['name'] else ""
                for cursor_name in CONFIG["cursor_process_names"]:
                    if cursor_name.lower() in proc_name and "cursoruiviewservice" not in proc_name.lower():
                        cursor_processes.append(proc)
                        # Speichere die PID des Hauptprozesses
                        if proc_name == "cursor" or proc_name == "cursor.app":
                            self.cursor_pid = proc.pid
                            return proc.pid
                
                # Prüfe auch die Befehlszeile, falls verfügbar
                if 'cmdline' in proc.info and proc.info['cmdline']:
                    cmdline = ' '.join([cmd.lower() for cmd in proc.info['cmdline'] if cmd])
                    if 'cursor' in cmdline and 'cursor.app' in cmdline:
                        if proc not in cursor_processes:
                            cursor_processes.append(proc)
                            self.cursor_pid = proc.pid
                            return proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
                # Ignoriere Fehler bei der Prozessabfrage
                pass
        
        # Wenn kein Hauptprozess gefunden wurde, aber andere Cursor-Prozesse existieren
        if cursor_processes:
            self.cursor_pid = cursor_processes[0].pid
            return cursor_processes[0].pid
        
        # Kein Cursor-Prozess gefunden
        self.cursor_pid = None
        return None
    
    def check_cpu_usage(self):
        """Überprüft die CPU-Auslastung des Cursor-Prozesses."""
        if self.cursor_pid is None:
            return False
            
        try:
            proc = psutil.Process(self.cursor_pid)
            cpu_percent = proc.cpu_percent(interval=0.1)
            
            # Speichere den Wert in der Historie
            self.cpu_history.append(cpu_percent)
            if len(self.cpu_history) > 5:  # Behalte nur die letzten 5 Werte
                self.cpu_history.pop(0)
                
            # Berechne Durchschnitt
            avg_cpu = sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0
            
            # Hohe CPU-Auslastung kann auf Blockierung hindeuten
            if cpu_percent > CONFIG["cpu_threshold"]:
                log(f"Cursor CPU-Nutzung: {cpu_percent:.1f}% (blockiert)")
                return True
            else:
                log(f"Cursor CPU-Nutzung: {cpu_percent:.1f}% (normal)")
                return False
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
            return False
    
    def check_network_activity(self):
        """
        Überprüft die Netzwerkaktivität des Systems, um Chat-Kommunikation zu erkennen.
        Fokussiert auf die Erkennung von Chat-Stillstand.
        
        Returns:
            bool: True, wenn Chat-Aktivität erkannt wurde, sonst False
        """
        try:
            current_net_io = psutil.net_io_counters()
            current_time = time.time()
            
            if self.last_network_io is not None:
                time_diff = current_time - self.last_network_check
                if time_diff > 0:
                    # Berechne Bytes pro Sekunde
                    bytes_sent = (current_net_io.bytes_sent - self.last_network_io.bytes_sent) / time_diff
                    bytes_recv = (current_net_io.bytes_recv - self.last_network_io.bytes_recv) / time_diff
                    
                    # Gesamte Netzwerkaktivität
                    total_bytes = bytes_sent + bytes_recv
                    
                    # Speichere den Wert in der Historie
                    self.network_activity_history.append((bytes_sent, bytes_recv, total_bytes))
                    if len(self.network_activity_history) > 5:  # Behalte nur die letzten 5 Werte
                        self.network_activity_history.pop(0)
                    
                    # Chat-Aktivitätsmuster erkennen:
                    # 1. Kontinuierliche, aber moderate Aktivität
                    # 2. Verhältnis zwischen Senden und Empfangen typisch für Chat
                    
                    # Prüfe auf typisches Chat-Muster
                    is_chat_pattern = False
                    
                    # Typische Chat-Aktivität hat ein bestimmtes Verhältnis von gesendeten zu empfangenen Daten
                    # und liegt in einem bestimmten Bereich
                    if len(self.network_activity_history) >= 3:
                        # Berechne Durchschnitt der letzten Messungen
                        avg_sent = sum(item[0] for item in self.network_activity_history) / len(self.network_activity_history)
                        avg_recv = sum(item[1] for item in self.network_activity_history) / len(self.network_activity_history)
                        
                        # Typisches Chat-Muster:
                        # 1. Moderate Aktivität (nicht zu hoch, nicht zu niedrig)
                        # 2. Relativ konstante Aktivität (keine großen Schwankungen)
                        
                        # Prüfe auf moderate Aktivität
                        moderate_activity = (
                            CONFIG["network_threshold"] * 0.1 < avg_sent < CONFIG["network_threshold"] * 10 and
                            CONFIG["network_threshold"] * 0.1 < avg_recv < CONFIG["network_threshold"] * 10
                        )
                        
                        # Prüfe auf konstante Aktivität (keine großen Schwankungen)
                        if moderate_activity and len(self.network_activity_history) >= 3:
                            # Berechne Standardabweichung
                            sent_values = [item[0] for item in self.network_activity_history]
                            recv_values = [item[1] for item in self.network_activity_history]
                            
                            # Einfache Varianzberechnung
                            sent_variance = sum((x - avg_sent) ** 2 for x in sent_values) / len(sent_values)
                            recv_variance = sum((x - avg_recv) ** 2 for x in recv_values) / len(recv_values)
                            
                            # Niedrige Varianz deutet auf konstante Aktivität hin
                            constant_activity = (
                                sent_variance < (avg_sent * 2) ** 2 and
                                recv_variance < (avg_recv * 2) ** 2
                            )
                            
                            is_chat_pattern = moderate_activity and constant_activity
                    
                    # Wenn ein Chat-Muster erkannt wurde oder die Aktivität über dem Schwellenwert liegt
                    if is_chat_pattern or bytes_sent > CONFIG["network_threshold"] or bytes_recv > CONFIG["network_threshold"]:
                        log(f"Chat-Netzwerkaktivität erkannt: {bytes_sent:.0f} B/s gesendet, {bytes_recv:.0f} B/s empfangen")
                        self.last_significant_network_activity = current_time
                        return True
            
            self.last_network_io = current_net_io
            self.last_network_check = current_time
            
            # Prüfe, ob seit der letzten signifikanten Netzwerkaktivität genug Zeit vergangen ist
            time_since_last_activity = current_time - self.last_significant_network_activity
            if time_since_last_activity < CONFIG["inactivity_threshold"]:
                return True
                
            return False
        except Exception as e:
            log(f"Fehler bei der Netzwerkaktivitätsprüfung: {e}")
            return False
    
    def check_cursor_activity(self):
        """
        Überprüft, ob der Cursor-Chat aktiv ist oder im Stillstand.
        Fokussiert auf Netzwerkaktivität als Hauptindikator für Chat-Aktivität.
        
        Returns:
            bool: True, wenn Chat aktiv ist, sonst False
        """
        pid = self.find_cursor_process()
        if pid is None:
            return False
        
        # Prüfe auf hohe CPU-Auslastung (Blockierung)
        is_blocked = self.check_cpu_usage()
        if is_blocked:
            log("Cursor Status: Cursor: Blockiert!")
            return False
        
        # Hauptsächlich auf Netzwerkaktivität prüfen
        is_active = self.check_network_activity()
        
        # Speichere den aktuellen Aktivitätsstatus in der Historie
        self.activity_status_history.append(is_active)
        if len(self.activity_status_history) > 5:  # Behalte nur die letzten 5 Werte
            self.activity_status_history.pop(0)
        
        # Prüfe, ob die Inaktivitätszeit überschritten wurde
        current_time = time.time()
        inactivity_time = current_time - self.last_activity_time
        
        # Aktualisiere die letzte Aktivitätszeit, wenn aktiv
        if is_active:
            self.last_activity_time = current_time
            self.consecutive_inactive_count = 0
            log(f"Inaktivitätszeit: {inactivity_time:.1f}s (Schwelle: {CONFIG['inactivity_threshold']}s) - Aktiv")
            return True
        else:
            # Erhöhe den Zähler für aufeinanderfolgende Inaktivitätserkennungen
            self.consecutive_inactive_count += 1
            
            # Nur als inaktiv melden, wenn mehrere aufeinanderfolgende Inaktivitätserkennungen vorliegen
            # Dies verhindert falsche Inaktivitätsmeldungen durch kurzzeitige Netzwerkschwankungen
            if self.consecutive_inactive_count >= 3:  # Mindestens 3 aufeinanderfolgende Inaktivitätserkennungen
                log(f"Inaktivitätszeit: {inactivity_time:.1f}s (Schwelle: {CONFIG['inactivity_threshold']}s) - Inaktiv")
                return False
            else:
                # Bei weniger als 3 aufeinanderfolgenden Inaktivitätserkennungen noch als aktiv betrachten
                log(f"Inaktivitätszeit: {inactivity_time:.1f}s (Schwelle: {CONFIG['inactivity_threshold']}s) - Noch aktiv (Inaktivitätszähler: {self.consecutive_inactive_count}/3)")
                return True
    
    def check_cursor_status(self):
        """Überprüft den Status von Cursor und gibt eine Statusmeldung aus."""
        if not is_monitor_enabled():
            return
            
        self.last_check_time = time.time()
        
        # Aktuellen Status ermitteln
        if self.find_cursor_process() is not None:
            if self.check_cursor_activity():
                current_status = "active"
                log("Cursor Status: Cursor: Aktiv")
            else:
                current_status = "inactive"
                log("Cursor Status: Cursor: Inaktiv")
        else:
            current_status = "not_running"
            log("Cursor Status: Cursor: Nicht gestartet")
        
        # Status hat sich geändert oder erste Prüfung
        if current_status != self.cursor_status or self.cursor_status == "unknown":
            log(f"Chat Status geändert: {self.cursor_status} -> {current_status}")
            self.cursor_status = current_status
            
            # Spiele immer einen Ton ab, wenn sich der Status ändert
            self.play_sound(current_status)
            
            # Speichere den letzten Status
            CONFIG["last_status"] = current_status
            save_config()
        else:
            # Status ist gleich geblieben, aber wir spielen trotzdem in regelmäßigen Abständen einen Ton
            self.play_sound(current_status)
    
    def run(self):
        """Startet die Überwachung."""
        log("Cursor Monitor gestartet. Drücke Strg+C zum Beenden.")
        
        # Signal-Handler für SIGUSR1 (Toggle)
        def handle_sigusr1(signum, frame):
            toggle_monitor()
            if is_monitor_enabled():
                log("Monitor aktiviert")
                self.play_sound("active")
            else:
                log("Monitor deaktiviert")
                self.play_sound("inactive")
        
        # Registriere Signal-Handler
        signal.signal(signal.SIGUSR1, handle_sigusr1)
        
        try:
            while self.running:
                self.check_cursor_status()
                time.sleep(CONFIG["check_interval"])
        except KeyboardInterrupt:
            log("Cursor Monitor beendet.")
            sys.exit(0)

def parse_arguments():
    """Parst die Kommandozeilenargumente."""
    parser = argparse.ArgumentParser(description="Cursor Monitor - Überwacht den Status von Cursor-Chats")
    parser.add_argument("--toggle", action="store_true", help="Schaltet den Monitor ein oder aus")
    parser.add_argument("--sound", action="store_true", help="Schaltet die Tonausgabe ein oder aus")
    parser.add_argument("--interval", type=int, help="Setzt das Prüfintervall in Sekunden")
    parser.add_argument("--threshold", type=int, help="Setzt die Inaktivitätsschwelle in Sekunden")
    parser.add_argument("--network", type=int, help="Setzt den Schwellenwert für Netzwerkaktivität in Bytes/s")
    parser.add_argument("--cpu", type=int, help="Setzt den CPU-Schwellenwert in Prozent")
    parser.add_argument("--debug", action="store_true", help="Aktiviert Debug-Ausgaben")
    parser.add_argument("--status", action="store_true", help="Zeigt den aktuellen Status an")
    parser.add_argument("--pid", action="store_true", help="Zeigt die PID des laufenden Monitors an")
    parser.add_argument("--notification-interval", type=int, help="Setzt das Intervall für Benachrichtigungen in Sekunden")
    parser.add_argument("--kill", action="store_true", help="Beendet alle laufenden Monitor-Prozesse")
    return parser.parse_args()

if __name__ == "__main__":
    # Lade die Konfiguration
    load_config()
    
    # Parse Kommandozeilenargumente
    args = parse_arguments()
    
    # Verarbeite Kommandozeilenargumente
    if args.kill:
        # Beende alle laufenden Monitor-Prozesse
        killed = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python3' or proc.info['name'] == 'python':
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'cursor_monitor.py' in cmdline and proc.pid != os.getpid():
                        print(f"Beende Monitor-Prozess: PID {proc.pid}")
                        proc.kill()
                        killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if not killed:
            print("Keine laufenden Monitor-Prozesse gefunden")
        sys.exit(0)
    
    if args.toggle:
        enabled = toggle_monitor()
        print(f"Cursor Monitor {'aktiviert' if enabled else 'deaktiviert'}")
        sys.exit(0)
    
    if args.sound:
        CONFIG["sound_enabled"] = not CONFIG["sound_enabled"]
        status = "aktiviert" if CONFIG["sound_enabled"] else "deaktiviert"
        print(f"Tonausgabe {status}")
        save_config()
        sys.exit(0)
    
    if args.interval:
        CONFIG["check_interval"] = args.interval
        print(f"Prüfintervall auf {args.interval} Sekunden gesetzt")
        save_config()
        sys.exit(0)
    
    if args.threshold:
        CONFIG["inactivity_threshold"] = args.threshold
        print(f"Inaktivitätsschwelle auf {args.threshold} Sekunden gesetzt")
        save_config()
        sys.exit(0)
    
    if args.network:
        CONFIG["network_threshold"] = args.network
        print(f"Netzwerk-Schwellenwert auf {args.network} Bytes/s gesetzt")
        save_config()
        sys.exit(0)
    
    if args.cpu:
        CONFIG["cpu_threshold"] = args.cpu
        print(f"CPU-Schwellenwert auf {args.cpu}% gesetzt")
        save_config()
        sys.exit(0)
    
    if args.notification_interval:
        CONFIG["notification_interval"] = args.notification_interval
        print(f"Benachrichtigungsintervall auf {args.notification_interval} Sekunden gesetzt")
        save_config()
        sys.exit(0)
    
    if args.debug:
        CONFIG["debug"] = not CONFIG["debug"]
        status = "aktiviert" if CONFIG["debug"] else "deaktiviert"
        print(f"Debug-Ausgaben {status}")
        save_config()
        sys.exit(0)
    
    if args.pid:
        # Finde laufende Monitor-Prozesse
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python3' or proc.info['name'] == 'python':
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'cursor_monitor.py' in cmdline and proc.pid != os.getpid():
                        print(f"Laufender Monitor: PID {proc.pid}")
                        sys.exit(0)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        print("Kein laufender Monitor gefunden")
        sys.exit(0)
    
    if args.status:
        status = "aktiviert" if is_monitor_enabled() else "deaktiviert"
        sound = "aktiviert" if CONFIG["sound_enabled"] else "deaktiviert"
        last_status = CONFIG["last_status"]
        print(f"Cursor Monitor Status:")
        print(f"  Aktiviert: {status}")
        print(f"  Tonausgabe: {sound}")
        print(f"  Prüfintervall: {CONFIG['check_interval']} Sekunden")
        print(f"  Benachrichtigungsintervall: {CONFIG['notification_interval']} Sekunden")
        print(f"  Inaktivitätsschwelle: {CONFIG['inactivity_threshold']} Sekunden")
        print(f"  Netzwerk-Schwellenwert: {CONFIG['network_threshold']} Bytes/s")
        print(f"  CPU-Schwellenwert: {CONFIG['cpu_threshold']}%")
        print(f"  Letzter Status: {last_status}")
        print(f"  Debug-Ausgaben: {'aktiviert' if CONFIG['debug'] else 'deaktiviert'}")
        sys.exit(0)
    
    # Starte den Monitor
    monitor = CursorMonitor()
    monitor.run() 