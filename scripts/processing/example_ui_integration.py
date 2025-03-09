#!/usr/bin/env python3
"""
example_ui_integration.py

Beispiel für die Integration des Chunk-Prozessors mit einer UI-Komponente.
Demonstriert die Verwendung von Callbacks für Fortschrittsanzeige und Statusupdates.
"""

import os
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import json

# Füge das übergeordnete Verzeichnis zum Pfad hinzu, um den Chunk-Prozessor zu importieren
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processing.chunk_processor import ChunkProcessor

class ChunkProcessorApp:
    """Einfache Tkinter-Anwendung zur Demonstration des Chunk-Prozessors."""
    
    def __init__(self, root):
        """Initialisiert die Anwendung."""
        self.root = root
        self.root.title("Chunk-Prozessor Demo")
        self.root.geometry("600x400")
        self.root.minsize(500, 300)
        
        # Erstelle Chunk-Prozessor
        self.processor = ChunkProcessor(
            callback_progress=self.update_progress,
            callback_status=self.update_status,
            callback_error=self.handle_error,
            callback_complete=self.handle_complete,
            max_workers=2
        )
        
        # Erstelle UI-Komponenten
        self.create_widgets()
        
        # Flag für laufende Verarbeitung
        self.processing = False
    
    def create_widgets(self):
        """Erstellt die UI-Komponenten."""
        # Hauptframe
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Dateiauswahl
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="Datei:").pack(side=tk.LEFT, padx=5)
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(file_frame, text="Durchsuchen", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        
        # Optionen
        options_frame = ttk.LabelFrame(main_frame, text="Optionen", padding="5")
        options_frame.pack(fill=tk.X, pady=5)
        
        # Worker-Anzahl
        worker_frame = ttk.Frame(options_frame)
        worker_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(worker_frame, text="Worker-Threads:").pack(side=tk.LEFT, padx=5)
        
        self.worker_var = tk.IntVar(value=2)
        worker_spinbox = ttk.Spinbox(worker_frame, from_=1, to=8, textvariable=self.worker_var, width=5)
        worker_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Chunk-Größe
        chunk_frame = ttk.Frame(options_frame)
        chunk_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(chunk_frame, text="Min. Chunk-Größe (KB):").pack(side=tk.LEFT, padx=5)
        
        self.min_chunk_var = tk.IntVar(value=50)
        min_chunk_spinbox = ttk.Spinbox(chunk_frame, from_=10, to=1000, textvariable=self.min_chunk_var, width=5)
        min_chunk_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(chunk_frame, text="Max. Chunk-Größe (KB):").pack(side=tk.LEFT, padx=5)
        
        self.max_chunk_var = tk.IntVar(value=10000)
        max_chunk_spinbox = ttk.Spinbox(chunk_frame, from_=1000, to=100000, textvariable=self.max_chunk_var, width=7)
        max_chunk_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Speichernutzung
        memory_frame = ttk.Frame(options_frame)
        memory_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(memory_frame, text="Speichernutzung (%):").pack(side=tk.LEFT, padx=5)
        
        self.memory_var = tk.DoubleVar(value=70)
        memory_spinbox = ttk.Spinbox(memory_frame, from_=10, to=90, textvariable=self.memory_var, width=5)
        memory_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Fortschrittsanzeige
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5)
        
        # Statusanzeige
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar(value="Bereit")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)
        
        # Speichernutzungsanzeige
        memory_usage_frame = ttk.Frame(main_frame)
        memory_usage_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(memory_usage_frame, text="Speichernutzung:").pack(side=tk.LEFT, padx=5)
        
        self.memory_usage_var = tk.StringVar(value="0 MB")
        ttk.Label(memory_usage_frame, textvariable=self.memory_usage_var).pack(side=tk.LEFT, padx=5)
        
        # Aktionsbuttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Starten", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(button_frame, text="Abbrechen", command=self.cancel_processing, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Ergebnisanzeige
        result_frame = ttk.LabelFrame(main_frame, text="Ergebnisse", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.result_text = tk.Text(result_frame, height=5, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar für Ergebnisanzeige
        scrollbar = ttk.Scrollbar(self.result_text, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
    
    def browse_file(self):
        """Öffnet einen Dateiauswahldialog."""
        file_path = filedialog.askopenfilename(
            title="Datei auswählen",
            filetypes=[("Alle Dateien", "*.*"), ("Textdateien", "*.txt"), ("JSON-Dateien", "*.json")]
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def update_progress(self, progress, stats):
        """Aktualisiert die Fortschrittsanzeige."""
        # Aktualisiere UI im Hauptthread
        self.root.after(0, lambda: self._update_progress_ui(progress, stats))
    
    def _update_progress_ui(self, progress, stats):
        """Aktualisiert die UI-Komponenten für den Fortschritt."""
        self.progress_var.set(progress * 100)
        
        # Aktualisiere Speichernutzungsanzeige
        memory_usage = stats.get("current_memory_usage", 0)
        self.memory_usage_var.set(f"{memory_usage:.2f} MB")
    
    def update_status(self, status, stats):
        """Aktualisiert die Statusanzeige."""
        # Aktualisiere UI im Hauptthread
        self.root.after(0, lambda: self.status_var.set(status))
    
    def handle_error(self, message, exception):
        """Behandelt Fehler während der Verarbeitung."""
        # Zeige Fehlermeldung im Hauptthread
        self.root.after(0, lambda: messagebox.showerror("Fehler", f"{message}\n\n{str(exception)}"))
    
    def handle_complete(self, stats):
        """Behandelt den Abschluss der Verarbeitung."""
        # Aktualisiere UI im Hauptthread
        self.root.after(0, lambda: self._handle_complete_ui(stats))
    
    def _handle_complete_ui(self, stats):
        """Aktualisiert die UI nach Abschluss der Verarbeitung."""
        self.processing = False
        self.start_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        
        # Zeige Zusammenfassung
        duration = stats["end_time"] - stats["start_time"]
        summary = (
            f"Verarbeitung abgeschlossen in {duration:.2f} Sekunden\n"
            f"Verarbeitete Chunks: {stats['processed_chunks']}/{stats['total_chunks']}\n"
            f"Durchschnittliche Chunk-Verarbeitungszeit: {stats['avg_chunk_processing_time']:.4f} Sekunden\n"
            f"Maximaler Speicherverbrauch: {stats['peak_memory_usage']:.2f} MB\n"
        )
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, summary)
        
        # Füge Ergebnisse hinzu, wenn vorhanden
        if "results" in stats and stats["results"]:
            self.result_text.insert(tk.END, "\nErgebnisse:\n")
            
            # Begrenze die Anzahl der angezeigten Ergebnisse
            max_results = 5
            results = stats["results"][:max_results]
            
            for i, result in enumerate(results):
                self.result_text.insert(tk.END, f"Chunk {i}: {str(result)[:100]}...\n")
            
            if len(stats["results"]) > max_results:
                self.result_text.insert(tk.END, f"... und {len(stats['results']) - max_results} weitere Ergebnisse\n")
    
    def start_processing(self):
        """Startet die Verarbeitung."""
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showwarning("Warnung", "Bitte wählen Sie eine Datei aus.")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("Fehler", f"Die Datei '{file_path}' existiert nicht.")
            return
        
        # Aktualisiere Prozessor-Konfiguration
        self.processor.max_workers = self.worker_var.get()
        self.processor.min_chunk_size = self.min_chunk_var.get()
        self.processor.max_chunk_size = self.max_chunk_var.get()
        self.processor.memory_target_percentage = self.memory_var.get() / 100
        
        # Setze UI-Status
        self.processing = True
        self.progress_var.set(0)
        self.status_var.set("Starte Verarbeitung...")
        self.start_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        
        # Starte Verarbeitung in separatem Thread
        threading.Thread(target=self._process_file, args=(file_path,), daemon=True).start()
    
    def _process_file(self, file_path):
        """Verarbeitet die Datei im Hintergrund."""
        try:
            # Bestimme Verarbeitungsfunktion basierend auf Dateityp
            _, ext = os.path.splitext(file_path)
            
            if ext.lower() in ['.txt', '.md', '.csv', '.html', '.xml', '.json']:
                # Textdatei: Zähle Wörter pro Chunk
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                def process_text_chunk(chunk):
                    # Zähle Wörter im Chunk
                    words = chunk.split()
                    return len(words)
                
                self.processor.process_text(text, process_text_chunk)
            else:
                # Binärdatei: Verarbeite als Bytes
                def process_binary_chunk(chunk):
                    # Einfache Verarbeitung: Zähle Bytes und berechne Durchschnitt
                    if not chunk:
                        return 0
                    return sum(chunk) / len(chunk)
                
                self.processor.process_file(file_path, process_binary_chunk)
                
        except Exception as e:
            # Zeige Fehlermeldung
            self.root.after(0, lambda: messagebox.showerror("Fehler", f"Fehler bei der Verarbeitung: {str(e)}"))
            
            # Setze UI-Status zurück
            self.root.after(0, lambda: self._reset_ui())
    
    def _reset_ui(self):
        """Setzt die UI zurück."""
        self.processing = False
        self.start_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        self.status_var.set("Bereit")
    
    def cancel_processing(self):
        """Bricht die Verarbeitung ab."""
        if self.processing:
            self.processor.cancel()
            self.status_var.set("Abbruch angefordert...")
    
    def on_closing(self):
        """Wird beim Schließen der Anwendung aufgerufen."""
        if self.processing:
            if messagebox.askyesno("Abbrechen", "Die Verarbeitung läuft noch. Wirklich beenden?"):
                self.processor.shutdown()
                self.root.destroy()
        else:
            self.processor.shutdown()
            self.root.destroy()


if __name__ == "__main__":
    # Erstelle Tkinter-Root
    root = tk.Tk()
    
    # Erstelle Anwendung
    app = ChunkProcessorApp(root)
    
    # Setze Callback für Schließen-Event
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Starte Hauptloop
    root.mainloop() 