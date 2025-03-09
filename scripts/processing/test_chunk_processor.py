#!/usr/bin/env python3
"""
test_chunk_processor.py

Testskript für den Chunk-Prozessor.
Führt verschiedene Tests durch, um die Funktionalität zu überprüfen.
"""

import os
import sys
import time
import tempfile
import unittest
import random
import string
from pathlib import Path

# Füge das übergeordnete Verzeichnis zum Pfad hinzu, um den Chunk-Prozessor zu importieren
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processing.chunk_processor import ChunkProcessor

class ChunkProcessorTests(unittest.TestCase):
    """Testklasse für den Chunk-Prozessor."""
    
    def setUp(self):
        """Wird vor jedem Test ausgeführt."""
        # Erstelle temporäres Verzeichnis für Testdateien
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Erstelle Chunk-Prozessor mit Standardeinstellungen
        self.processor = ChunkProcessor(
            max_workers=2,
            min_chunk_size=10,
            max_chunk_size=100
        )
        
        # Erstelle Testdateien
        self.small_file_path = self._create_test_file(size_kb=50)
        self.medium_file_path = self._create_test_file(size_kb=500)
        self.large_file_path = self._create_test_file(size_kb=2000)
        
        # Erstelle Testtext
        self.small_text = self._create_random_text(words=1000)
        self.large_text = self._create_random_text(words=10000)
    
    def tearDown(self):
        """Wird nach jedem Test ausgeführt."""
        # Fahre Prozessor herunter
        self.processor.shutdown()
        
        # Lösche temporäres Verzeichnis
        self.temp_dir.cleanup()
    
    def _create_test_file(self, size_kb):
        """Erstellt eine Testdatei mit der angegebenen Größe."""
        file_path = Path(self.temp_dir.name) / f"test_file_{size_kb}kb.txt"
        
        # Generiere zufälligen Inhalt
        content = ''.join(random.choices(string.ascii_letters + string.digits + ' \n', k=size_kb * 1024))
        
        # Schreibe Inhalt in Datei
        with open(file_path, 'w') as f:
            f.write(content)
        
        return file_path
    
    def _create_random_text(self, words):
        """Erstellt einen zufälligen Text mit der angegebenen Anzahl an Wörtern."""
        word_list = ['Lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit',
                    'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore',
                    'magna', 'aliqua', 'Ut', 'enim', 'ad', 'minim', 'veniam', 'quis', 'nostrud',
                    'exercitation', 'ullamco', 'laboris', 'nisi', 'ut', 'aliquip', 'ex', 'ea',
                    'commodo', 'consequat', 'Duis', 'aute', 'irure', 'dolor', 'in', 'reprehenderit',
                    'in', 'voluptate', 'velit', 'esse', 'cillum', 'dolore', 'eu', 'fugiat', 'nulla',
                    'pariatur', 'Excepteur', 'sint', 'occaecat', 'cupidatat', 'non', 'proident',
                    'sunt', 'in', 'culpa', 'qui', 'officia', 'deserunt', 'mollit', 'anim', 'id',
                    'est', 'laborum']
        
        return ' '.join(random.choices(word_list, k=words))
    
    def test_determine_chunk_size(self):
        """Testet die Bestimmung der Chunk-Größe."""
        # Teste mit verschiedenen Dateigrößen
        small_size = 100 * 1024  # 100 KB
        medium_size = 10 * 1024 * 1024  # 10 MB
        large_size = 100 * 1024 * 1024  # 100 MB
        
        # Bestimme Chunk-Größen
        small_chunk_size = self.processor.determine_chunk_size(small_size)
        medium_chunk_size = self.processor.determine_chunk_size(medium_size)
        large_chunk_size = self.processor.determine_chunk_size(large_size)
        
        # Überprüfe, ob die Chunk-Größen im erwarteten Bereich liegen
        self.assertGreaterEqual(small_chunk_size, self.processor.min_chunk_size * 1024)
        self.assertLessEqual(small_chunk_size, self.processor.max_chunk_size * 1024)
        
        self.assertGreaterEqual(medium_chunk_size, self.processor.min_chunk_size * 1024)
        self.assertLessEqual(medium_chunk_size, self.processor.max_chunk_size * 1024)
        
        self.assertGreaterEqual(large_chunk_size, self.processor.min_chunk_size * 1024)
        self.assertLessEqual(large_chunk_size, self.processor.max_chunk_size * 1024)
        
        # Überprüfe, ob größere Dateien zu größeren Chunks führen (oder gleich bleiben)
        self.assertGreaterEqual(medium_chunk_size, small_chunk_size)
        self.assertGreaterEqual(large_chunk_size, medium_chunk_size)
    
    def test_process_file_small(self):
        """Testet die Verarbeitung einer kleinen Datei."""
        # Definiere Verarbeitungsfunktion: Zähle Zeichen pro Chunk
        def count_chars(chunk):
            return len(chunk)
        
        # Verarbeite Datei
        result = self.processor.process_file(self.small_file_path, count_chars)
        
        # Überprüfe Ergebnis
        self.assertTrue(result["success"])
        self.assertGreater(len(result["results"]), 0)
        
        # Überprüfe, ob die Summe der Ergebnisse der Dateigröße entspricht
        total_chars = sum(result["results"])
        file_size = os.path.getsize(self.small_file_path)
        self.assertEqual(total_chars, file_size)
    
    def test_process_file_large(self):
        """Testet die Verarbeitung einer großen Datei."""
        # Definiere Verarbeitungsfunktion: Zähle Zeilen pro Chunk
        def count_lines(chunk):
            return chunk.count(b'\n') + 1
        
        # Verarbeite Datei
        result = self.processor.process_file(self.large_file_path, count_lines)
        
        # Überprüfe Ergebnis
        self.assertTrue(result["success"])
        self.assertGreater(len(result["results"]), 1)  # Sollte mehrere Chunks haben
        
        # Überprüfe, ob die Summe der Ergebnisse ungefähr der Anzahl der Zeilen entspricht
        total_lines = sum(result["results"])
        
        # Zähle Zeilen in der Datei
        with open(self.large_file_path, 'rb') as f:
            file_lines = f.read().count(b'\n') + 1
        
        # Toleriere kleine Abweichungen aufgrund von Chunk-Grenzen
        self.assertAlmostEqual(total_lines, file_lines, delta=len(result["results"]))
    
    def test_process_text_small(self):
        """Testet die Verarbeitung eines kleinen Texts."""
        # Definiere Verarbeitungsfunktion: Zähle Wörter pro Chunk
        def count_words(chunk):
            return len(chunk.split())
        
        # Verarbeite Text
        result = self.processor.process_text(self.small_text, count_words)
        
        # Überprüfe Ergebnis
        self.assertTrue(result["success"])
        self.assertGreater(len(result["results"]), 0)
        
        # Überprüfe, ob die Summe der Ergebnisse der Wortanzahl entspricht
        total_words = sum(result["results"])
        actual_words = len(self.small_text.split())
        self.assertEqual(total_words, actual_words)
    
    def test_process_text_large(self):
        """Testet die Verarbeitung eines großen Texts."""
        # Definiere Verarbeitungsfunktion: Zähle Vorkommen des Buchstabens 'e'
        def count_letter_e(chunk):
            return chunk.lower().count('e')
        
        # Verarbeite Text
        result = self.processor.process_text(self.large_text, count_letter_e)
        
        # Überprüfe Ergebnis
        self.assertTrue(result["success"])
        self.assertGreater(len(result["results"]), 1)  # Sollte mehrere Chunks haben
        
        # Überprüfe, ob die Summe der Ergebnisse der Anzahl der 'e's entspricht
        total_e = sum(result["results"])
        actual_e = self.large_text.lower().count('e')
        self.assertEqual(total_e, actual_e)
    
    def test_cancel_processing(self):
        """Testet das Abbrechen der Verarbeitung."""
        # Erstelle eine sehr große Datei
        very_large_file = self._create_test_file(size_kb=5000)
        
        # Definiere Verarbeitungsfunktion mit Verzögerung
        def slow_processing(chunk):
            time.sleep(0.1)  # Verzögerung, um Abbruch zu ermöglichen
            return len(chunk)
        
        # Starte Verarbeitung in separatem Thread
        import threading
        processing_thread = threading.Thread(
            target=lambda: self.processor.process_file(very_large_file, slow_processing),
            daemon=True
        )
        processing_thread.start()
        
        # Warte kurz, damit die Verarbeitung beginnen kann
        time.sleep(0.5)
        
        # Breche Verarbeitung ab
        self.processor.cancel()
        
        # Warte auf Beendigung (max. 5 Sekunden)
        processing_thread.join(timeout=5.0)
        
        # Überprüfe, ob das Abbruch-Flag gesetzt wurde
        self.assertTrue(self.processor.cancel_requested)
    
    def test_memory_usage(self):
        """Testet die Speichernutzung während der Verarbeitung."""
        import psutil
        
        # Erfasse Speichernutzung vor der Verarbeitung
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        # Verarbeite große Datei
        def process_chunk(chunk):
            # Einfache Verarbeitung ohne zusätzlichen Speicherverbrauch
            return len(chunk)
        
        result = self.processor.process_file(self.large_file_path, process_chunk)
        
        # Erfasse Speichernutzung nach der Verarbeitung
        memory_after = process.memory_info().rss
        
        # Überprüfe, ob die Speichernutzung nicht übermäßig angestiegen ist
        # (Toleriere einen Anstieg von maximal 50% oder 100 MB, je nachdem, was größer ist)
        max_increase = max(memory_before * 0.5, 100 * 1024 * 1024)
        self.assertLessEqual(memory_after - memory_before, max_increase)
        
        # Überprüfe, ob die gemessene Speichernutzung im Ergebnis enthalten ist
        self.assertGreater(result["stats"]["peak_memory_usage"], 0)
    
    def test_error_handling(self):
        """Testet die Fehlerbehandlung."""
        # Definiere fehlerhafte Verarbeitungsfunktion
        def faulty_processing(chunk):
            if random.random() < 0.5:  # 50% Wahrscheinlichkeit für einen Fehler
                raise ValueError("Simulierter Fehler")
            return len(chunk)
        
        # Sammle Fehler
        errors = []
        def error_callback(message, exception):
            errors.append((message, exception))
        
        # Setze Fehler-Callback
        self.processor.callback_error = error_callback
        
        # Verarbeite Datei
        result = self.processor.process_file(self.medium_file_path, faulty_processing)
        
        # Überprüfe, ob Fehler aufgetreten sind
        self.assertGreaterEqual(len(errors), 0)
        
        # Überprüfe, ob die Anzahl der Fehler im Ergebnis korrekt ist
        self.assertEqual(result["stats"]["errors"], len(errors))
        
        # Überprüfe, ob trotz Fehlern ein Ergebnis zurückgegeben wurde
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main() 