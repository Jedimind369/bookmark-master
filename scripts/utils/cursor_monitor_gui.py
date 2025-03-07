#!/usr/bin/env python3

"""
cursor_monitor_gui.py - Grafische Benutzeroberfläche für den Cursor Monitor
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
from pathlib import Path
import platform

# Pfade
SCRIPT_DIR = Path(__file__).parent
MONITOR_SCRIPT = SCRIPT_DIR / "cursor_monitor.py"
CONFIG_FILE = Path.home() / ".cursor_monitor_config.json"
PID_FILE = Path.home() / ".cursor_monitor.pid"
STATUS_FILE = Path.home() / ".cursor_monitor_status"

# Standard-Konfiguration
DEFAULT_CONFIG = {
    "enabled": True,
    "check_interval": 30,
    "cursor_process_names": ["cursor", "Cursor", "cursor.app", "Cursor.app"],
    "inactivity_threshold": 5,
    "debug": True,
    "sound_enabled": True,
    "network_threshold": 50,
    "last_status": "unknown",
    "notification_interval": 120,
    "cpu_threshold": 90,
}

# Lade Konfiguration
def load_config():
    """Lädt die Konfiguration aus der Datei."""
    config = DEFAULT_CONFIG.copy()
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
    except Exception as e:
        print(f"Fehler beim Laden der Konfiguration: {e}")
    return config

# Speichere Konfiguration
def save_config(config):
    """Speichert die Konfiguration in der Datei."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Fehler beim Speichern der Konfiguration: {e}")

# Prüfe, ob der Monitor läuft
def is_running():
    """Prüft, ob der Monitor läuft."""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Prüfe, ob der Prozess existiert
            import psutil
            return psutil.pid_exists(pid)
        except:
            return False
    return False

# Starte den Monitor
def start_monitor():
    """Startet den Monitor im Hintergrund."""
    if is_running():
        return "Cursor Monitor läuft bereits"
    
    try:
        if platform.system() == "Windows":
            proc = subprocess.Popen(["pythonw", str(MONITOR_SCRIPT)], 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            proc = subprocess.Popen(["python3", str(MONITOR_SCRIPT)], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
        
        # Speichere PID
        with open(PID_FILE, 'w') as f:
            f.write(str(proc.pid))
        
        return f"Cursor Monitor gestartet (PID: {proc.pid})"
    except Exception as e:
        return f"Fehler beim Starten des Monitors: {e}"

# Stoppe den Monitor
def stop_monitor():
    """Stoppt den Monitor."""
    if not is_running():
        return "Cursor Monitor läuft nicht"
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        import psutil
        try:
            process = psutil.Process(pid)
            process.terminate()
            PID_FILE.unlink(missing_ok=True)
            return f"Cursor Monitor gestoppt (PID: {pid})"
        except psutil.NoSuchProcess:
            PID_FILE.unlink(missing_ok=True)
            return "Cursor Monitor-Prozess existiert nicht mehr"
    except Exception as e:
        return f"Fehler beim Stoppen des Monitors: {e}"

# Toggle Monitor
def toggle_monitor_status():
    """Schaltet den Monitor ein oder aus (ohne ihn zu beenden)."""
    if STATUS_FILE.exists():
        STATUS_FILE.unlink()
        return "Monitor deaktiviert (läuft weiter im Hintergrund)"
    else:
        STATUS_FILE.touch()
        return "Monitor aktiviert"

# Teste Töne
def test_sound(status):
    """Testet einen Ton."""
    try:
        if platform.system() == "Darwin":  # macOS
            sounds = {
                "active": "Tink.aiff",
                "inactive": "Basso.aiff",
                "not_running": "Submarine.aiff"
            }
            if status in sounds:
                subprocess.run(["afplay", f"/System/Library/Sounds/{sounds[status]}"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Ton für '{status}' abgespielt"
        elif platform.system() == "Windows":
            import winsound
            sounds = {
                "active": winsound.MB_ICONASTERISK,
                "inactive": winsound.MB_ICONEXCLAMATION,
                "not_running": winsound.MB_ICONQUESTION
            }
            if status in sounds:
                winsound.MessageBeep(sounds[status])
                return f"Ton für '{status}' abgespielt"
        elif platform.system() == "Linux":
            # Linux-Töne (falls verfügbar)
            sound_file = SCRIPT_DIR / "sounds" / f"{status}.wav"
            if sound_file.exists():
                subprocess.run(["aplay", str(sound_file)], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Ton für '{status}' abgespielt"
        
        return "Tonausgabe nicht verfügbar für dieses System"
    except Exception as e:
        return f"Fehler beim Abspielen des Tons: {e}"

# Hauptklasse für die GUI
class CursorMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cursor Monitor Steuerung")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Lade Konfiguration
        self.config = load_config()
        
        # Erstelle GUI
        self.create_widgets()
        
        # Aktualisiere Status
        self.update_status()
        
        # Aktualisiere Status alle 5 Sekunden
        self.root.after(5000, self.update_status)
    
    def create_widgets(self):
        # Hauptframe
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status-Frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Wird geladen...")
        self.status_label.pack(fill=tk.X)
        
        # Steuerungs-Frame
        control_frame = ttk.LabelFrame(main_frame, text="Steuerung", padding="10")
        control_frame.pack(fill=tk.X, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.start_button = ttk.Button(button_frame, text="Starten", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stoppen", command=self.stop)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.toggle_button = ttk.Button(button_frame, text="Ein/Aus", command=self.toggle)
        self.toggle_button.pack(side=tk.LEFT, padx=5)
        
        # Konfiguration-Frame
        config_frame = ttk.LabelFrame(main_frame, text="Konfiguration", padding="10")
        config_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Erstelle ein Notebook (Tabs)
        notebook = ttk.Notebook(config_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Allgemeine Einstellungen
        general_tab = ttk.Frame(notebook, padding="10")
        notebook.add(general_tab, text="Allgemein")
        
        # Sound aktivieren
        sound_frame = ttk.Frame(general_tab)
        sound_frame.pack(fill=tk.X, pady=5)
        
        self.sound_var = tk.BooleanVar(value=self.config["sound_enabled"])
        sound_check = ttk.Checkbutton(sound_frame, text="Tonausgabe aktivieren", 
                                     variable=self.sound_var, command=self.save_settings)
        sound_check.pack(side=tk.LEFT)
        
        # Test-Töne
        sound_test_frame = ttk.LabelFrame(general_tab, text="Test-Töne", padding="10")
        sound_test_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(sound_test_frame, text="Aktiv", 
                  command=lambda: self.test_sound("active")).pack(side=tk.LEFT, padx=5)
        ttk.Button(sound_test_frame, text="Inaktiv", 
                  command=lambda: self.test_sound("inactive")).pack(side=tk.LEFT, padx=5)
        ttk.Button(sound_test_frame, text="Nicht gestartet", 
                  command=lambda: self.test_sound("not_running")).pack(side=tk.LEFT, padx=5)
        
        # Debug aktivieren
        debug_frame = ttk.Frame(general_tab)
        debug_frame.pack(fill=tk.X, pady=5)
        
        self.debug_var = tk.BooleanVar(value=self.config["debug"])
        debug_check = ttk.Checkbutton(debug_frame, text="Debug-Ausgaben aktivieren", 
                                     variable=self.debug_var, command=self.save_settings)
        debug_check.pack(side=tk.LEFT)
        
        # Tab 2: Zeiteinstellungen
        time_tab = ttk.Frame(notebook, padding="10")
        notebook.add(time_tab, text="Zeiteinstellungen")
        
        # Prüfintervall
        interval_frame = ttk.Frame(time_tab)
        interval_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(interval_frame, text="Prüfintervall (Sekunden):").pack(side=tk.LEFT)
        
        self.interval_var = tk.StringVar(value=str(self.config["check_interval"]))
        interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=10)
        interval_entry.pack(side=tk.LEFT, padx=5)
        interval_entry.bind("<FocusOut>", lambda e: self.save_settings())
        interval_entry.bind("<Return>", lambda e: self.save_settings())
        
        # Inaktivitätsschwelle
        threshold_frame = ttk.Frame(time_tab)
        threshold_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(threshold_frame, text="Inaktivitätsschwelle (Sekunden):").pack(side=tk.LEFT)
        
        self.threshold_var = tk.StringVar(value=str(self.config["inactivity_threshold"]))
        threshold_entry = ttk.Entry(threshold_frame, textvariable=self.threshold_var, width=10)
        threshold_entry.pack(side=tk.LEFT, padx=5)
        threshold_entry.bind("<FocusOut>", lambda e: self.save_settings())
        threshold_entry.bind("<Return>", lambda e: self.save_settings())
        
        # Benachrichtigungsintervall
        notify_frame = ttk.Frame(time_tab)
        notify_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(notify_frame, text="Benachrichtigungsintervall (Sekunden):").pack(side=tk.LEFT)
        
        self.notify_var = tk.StringVar(value=str(self.config["notification_interval"]))
        notify_entry = ttk.Entry(notify_frame, textvariable=self.notify_var, width=10)
        notify_entry.pack(side=tk.LEFT, padx=5)
        notify_entry.bind("<FocusOut>", lambda e: self.save_settings())
        notify_entry.bind("<Return>", lambda e: self.save_settings())
        
        # Tab 3: Schwellenwerte
        threshold_tab = ttk.Frame(notebook, padding="10")
        notebook.add(threshold_tab, text="Schwellenwerte")
        
        # Netzwerk-Schwellenwert
        network_frame = ttk.Frame(threshold_tab)
        network_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(network_frame, text="Netzwerk-Schwellenwert (Bytes/s):").pack(side=tk.LEFT)
        
        self.network_var = tk.StringVar(value=str(self.config["network_threshold"]))
        network_entry = ttk.Entry(network_frame, textvariable=self.network_var, width=10)
        network_entry.pack(side=tk.LEFT, padx=5)
        network_entry.bind("<FocusOut>", lambda e: self.save_settings())
        network_entry.bind("<Return>", lambda e: self.save_settings())
        
        # CPU-Schwellenwert
        cpu_frame = ttk.Frame(threshold_tab)
        cpu_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(cpu_frame, text="CPU-Schwellenwert (%):").pack(side=tk.LEFT)
        
        self.cpu_var = tk.StringVar(value=str(self.config["cpu_threshold"]))
        cpu_entry = ttk.Entry(cpu_frame, textvariable=self.cpu_var, width=10)
        cpu_entry.pack(side=tk.LEFT, padx=5)
        cpu_entry.bind("<FocusOut>", lambda e: self.save_settings())
        cpu_entry.bind("<Return>", lambda e: self.save_settings())
        
        # Status-Anzeige
        self.log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        self.log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = tk.Text(self.log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar für Log
        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Mache Log schreibgeschützt
        self.log_text.config(state=tk.DISABLED)
        
        # Füge Hilfetext hinzu
        self.add_log("Cursor Monitor GUI gestartet.")
        self.add_log("Verwende die Steuerungsbuttons, um den Monitor zu starten, zu stoppen oder ein-/auszuschalten.")
        self.add_log("Ändere die Einstellungen in den Tabs und klicke auf 'Speichern'.")
    
    def update_status(self):
        """Aktualisiert den Status des Monitors."""
        running = is_running()
        enabled = STATUS_FILE.exists()
        
        if running:
            with open(PID_FILE, 'r') as f:
                pid = f.read().strip()
            status_text = f"Cursor Monitor läuft (PID: {pid})"
            if enabled:
                status_text += " - Aktiviert"
            else:
                status_text += " - Deaktiviert"
        else:
            status_text = "Cursor Monitor läuft nicht"
        
        self.status_label.config(text=status_text)
        
        # Aktualisiere Buttons
        if running:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.toggle_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.toggle_button.config(state=tk.DISABLED)
        
        # Plane nächste Aktualisierung
        self.root.after(5000, self.update_status)
    
    def start(self):
        """Startet den Monitor."""
        result = start_monitor()
        self.add_log(result)
        self.update_status()
    
    def stop(self):
        """Stoppt den Monitor."""
        result = stop_monitor()
        self.add_log(result)
        self.update_status()
    
    def toggle(self):
        """Schaltet den Monitor ein/aus."""
        result = toggle_monitor_status()
        self.add_log(result)
        self.update_status()
    
    def save_settings(self):
        """Speichert die Einstellungen."""
        try:
            # Aktualisiere Konfiguration
            self.config["sound_enabled"] = self.sound_var.get()
            self.config["debug"] = self.debug_var.get()
            
            # Prüfe numerische Werte
            try:
                self.config["check_interval"] = int(self.interval_var.get())
                self.config["inactivity_threshold"] = int(self.threshold_var.get())
                self.config["notification_interval"] = int(self.notify_var.get())
                self.config["network_threshold"] = int(self.network_var.get())
                self.config["cpu_threshold"] = int(self.cpu_var.get())
            except ValueError:
                messagebox.showerror("Fehler", "Bitte geben Sie gültige Zahlen ein.")
                return
            
            # Speichere Konfiguration
            save_config(self.config)
            self.add_log("Einstellungen gespeichert.")
            
            # Wenn der Monitor läuft, starte ihn neu, damit die Änderungen wirksam werden
            if is_running():
                self.add_log("Starte Monitor neu, um Änderungen zu übernehmen...")
                stop_monitor()
                start_monitor()
                self.update_status()
        except Exception as e:
            self.add_log(f"Fehler beim Speichern der Einstellungen: {e}")
    
    def test_sound(self, status):
        """Testet einen Ton."""
        result = test_sound(status)
        self.add_log(result)
    
    def add_log(self, message):
        """Fügt eine Nachricht zum Log hinzu."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

# Hauptfunktion
def main():
    root = tk.Tk()
    app = CursorMonitorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 