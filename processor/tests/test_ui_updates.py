#!/usr/bin/env python3
"""
Tests für das UI-Updates-Modul
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch
from processor.ui_updates import UIUpdateManager, UpdateType


class TestUIUpdateManager(unittest.TestCase):
    """Tests für die UIUpdateManager-Klasse"""

    def setUp(self):
        """Test-Setup vor jedem Test"""
        self.manager = UIUpdateManager(update_interval=0.01)
        self.manager.start()

    def tearDown(self):
        """Bereinigung nach jedem Test"""
        self.manager.stop()

    def test_register_handler(self):
        """Test, ob Handler korrekt registriert werden"""
        mock_handler = Mock()
        self.manager.register_handler(UpdateType.PROGRESS, mock_handler)
        self.assertIn(mock_handler, self.manager.update_handlers[UpdateType.PROGRESS])

    def test_throttling(self):
        """Test, ob Throttling funktioniert"""
        # Setze Throttle-Interval auf 0.5 Sekunden
        self.manager.set_throttle(UpdateType.PROGRESS, 0.5)

        # Erstelle Mock-Handler
        mock_handler = Mock()
        self.manager.register_handler(UpdateType.PROGRESS, mock_handler)

        # Sende Updates in schneller Folge
        for _ in range(10):
            self.manager.queue_progress("test_task", 1, 10)
            time.sleep(0.01)

        # Warte, bis Updates verarbeitet wurden
        time.sleep(0.1)

        # Handler sollte nur einmal aufgerufen worden sein wegen Throttling
        self.assertLessEqual(mock_handler.call_count, 2)

    def test_multiple_handlers(self):
        """Test, ob mehrere Handler für denselben Update-Typ funktionieren"""
        mock_handler1 = Mock()
        mock_handler2 = Mock()

        self.manager.register_handler(UpdateType.STATUS, mock_handler1)
        self.manager.register_handler(UpdateType.STATUS, mock_handler2)

        self.manager.queue_status("test_task", "In Bearbeitung")

        # Warte, bis Updates verarbeitet wurden
        time.sleep(0.1)

        # Beide Handler sollten aufgerufen worden sein
        mock_handler1.assert_called_once()
        mock_handler2.assert_called_once()

    def test_error_handling(self):
        """Test, ob Fehler in Handlern korrekt behandelt werden"""
        # Erstelle einen Handler, der eine Exception wirft
        def error_handler(key, data):
            raise ValueError("Test-Fehler")

        # Erstelle einen normalen Handler
        mock_handler = Mock()

        # Registriere beide Handler
        self.manager.register_handler(UpdateType.ERROR, error_handler)
        self.manager.register_handler(UpdateType.ERROR, mock_handler)

        # Sende Update
        with patch("processor.ui_updates.logger") as mock_logger:
            self.manager.queue_error("test_task", "Ein Fehler ist aufgetreten")

            # Warte, bis Updates verarbeitet wurden
            time.sleep(0.1)

            # Der Fehler sollte geloggt worden sein
            mock_logger.error.assert_called()

            # Der normale Handler sollte trotzdem aufgerufen worden sein
            mock_handler.assert_called_once()

    def test_queue_progress(self):
        """Test für die queue_progress-Methode"""
        mock_handler = Mock()
        self.manager.register_handler(UpdateType.PROGRESS, mock_handler)

        self.manager.queue_progress("test_task", 5, 10)

        # Warte, bis Updates verarbeitet wurden
        time.sleep(0.1)

        # Prüfe, ob Handler mit korrekten Daten aufgerufen wurde
        mock_handler.assert_called_once()
        args, _ = mock_handler.call_args
        self.assertEqual(args[0], "test_task")
        self.assertEqual(args[1]["progress"], 5)
        self.assertEqual(args[1]["total"], 10)
        self.assertEqual(args[1]["percentage"], 50.0)

    def test_queue_status(self):
        """Test für die queue_status-Methode"""
        mock_handler = Mock()
        self.manager.register_handler(UpdateType.STATUS, mock_handler)

        self.manager.queue_status("test_task", "In Bearbeitung")

        # Warte, bis Updates verarbeitet wurden
        time.sleep(0.1)

        # Prüfe, ob Handler mit korrekten Daten aufgerufen wurde
        mock_handler.assert_called_once()
        args, _ = mock_handler.call_args
        self.assertEqual(args[0], "test_task")
        self.assertEqual(args[1]["status"], "In Bearbeitung")

    def test_queue_complete(self):
        """Test für die queue_complete-Methode"""
        mock_handler = Mock()
        self.manager.register_handler(UpdateType.COMPLETE, mock_handler)

        result = {"success": True, "items_processed": 100}
        self.manager.queue_complete("test_task", result)

        # Warte, bis Updates verarbeitet wurden
        time.sleep(0.1)

        # Prüfe, ob Handler mit korrekten Daten aufgerufen wurde
        mock_handler.assert_called_once()
        args, _ = mock_handler.call_args
        self.assertEqual(args[0], "test_task")
        self.assertEqual(args[1]["result"], result)

    def test_thread_safety(self):
        """Test der Thread-Sicherheit bei gleichzeitigen Updates"""
        # Erstelle Mock-Handler
        mock_handler = Mock()
        self.manager.register_handler(UpdateType.CUSTOM, mock_handler)

        # Deaktiviere Throttling für diesen Test
        self.manager.set_throttle(UpdateType.CUSTOM, 0.0)

        # Anzahl der Threads und Updates pro Thread
        num_threads = 5
        updates_per_thread = 20

        # Funktion für Thread, der Updates sendet
        def send_updates(thread_id):
            for i in range(updates_per_thread):
                self.manager.queue_custom(
                    f"task_{thread_id}", "test_event", {"counter": i}
                )
                time.sleep(0.001)  # Kleine Verzögerung für Realismus

        # Starte mehrere Threads, die Updates senden
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=send_updates, args=(i,))
            thread.start()
            threads.append(thread)

        # Warte auf Abschluss aller Threads
        for thread in threads:
            thread.join()

        # Warte zusätzlich, bis alle Updates verarbeitet wurden
        time.sleep(0.5)

        # Überprüfe, dass die erwartete Anzahl an Updates verarbeitet wurde
        self.assertEqual(mock_handler.call_count, num_threads * updates_per_thread)


if __name__ == "__main__":
    unittest.main() 