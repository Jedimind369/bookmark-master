#!/usr/bin/env python3
"""
Tests für die API-Endpunkte des Processors
"""

import unittest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
import psutil

# Mock-Importieren des app-Moduls
with patch.dict('sys.modules', {
    'prometheus_client': MagicMock(),
    'flask': MagicMock(),
}):
    from processor.app import app


class TestProcessorAPI(unittest.TestCase):
    """Tests für die API-Endpunkte des Processors"""

    def setUp(self):
        """Test-Setup vor jedem Test"""
        self.app = app.test_client()
        self.app.testing = True
        
        # Erstelle temporäre Testdateien
        self.temp_dir = tempfile.TemporaryDirectory()
        self.json_file_path = os.path.join(self.temp_dir.name, "test_bookmarks.json")
        
        # Schreibe Testdaten in die JSON-Datei
        with open(self.json_file_path, 'w') as f:
            json.dump([
                {"url": "https://example.com", "title": "Example Website"},
                {"url": "https://test.com", "title": "Test Website"}
            ], f)

    def tearDown(self):
        """Bereinigung nach jedem Test"""
        self.temp_dir.cleanup()

    @patch('processor.app.PipelineIntegration')
    def test_health_check(self, mock_pipeline):
        """Test des Health-Check-Endpunkts"""
        response = self.app.get('/health')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'ok')
        self.assertIn('memory_usage', data)
        self.assertIn('uptime', data)

    @patch('processor.app.get_memory_usage')
    def test_get_memory_usage(self, mock_get_memory):
        """Test der get_memory_usage-Funktion"""
        mock_get_memory.return_value = 1024 * 1024  # 1 MB
        
        response = self.app.get('/health')
        data = json.loads(response.data)
        
        self.assertEqual(data['memory_usage'], 1024 * 1024)
        mock_get_memory.assert_called_once()

    @patch('processor.app.PipelineIntegration')
    def test_process_json(self, mock_pipeline):
        """Test des JSON-Verarbeitungs-Endpunkts"""
        # Mock der process_json-Methode
        mock_instance = mock_pipeline.return_value
        mock_instance.process_json.return_value = {
            'items_processed': 2,
            'output_path': '/output/enriched.json'
        }
        
        response = self.app.post('/process/json', json={
            'file_path': self.json_file_path,
            'max_workers': 2,
            'min_chunk_size': 100,
            'max_chunk_size': 1000,
            'memory_target': 70
        })
        
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['items_processed'], 2)
        self.assertEqual(data['output_path'], '/output/enriched.json')
        
        # Überprüfe, ob process_json mit den richtigen Parametern aufgerufen wurde
        mock_instance.process_json.assert_called_once()
        args, kwargs = mock_instance.process_json.call_args
        self.assertEqual(args[0], self.json_file_path)

    @patch('processor.app.PipelineIntegration')
    def test_process_urls(self, mock_pipeline):
        """Test des URL-Verarbeitungs-Endpunkts"""
        urls = ["https://example.com", "https://test.com"]
        
        # Mock der process_urls-Methode
        mock_instance = mock_pipeline.return_value
        mock_instance.process_urls.return_value = {
            'items_processed': len(urls),
            'output_path': '/output/enriched_urls.json'
        }
        
        response = self.app.post('/process/urls', json={
            'urls': urls,
            'max_workers': 2
        })
        
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['items_processed'], len(urls))
        self.assertEqual(data['output_path'], '/output/enriched_urls.json')
        
        # Überprüfe, ob process_urls mit den richtigen Parametern aufgerufen wurde
        mock_instance.process_urls.assert_called_once()
        args, kwargs = mock_instance.process_urls.call_args
        self.assertEqual(args[0], urls)

    @patch('processor.app.PipelineIntegration')
    def test_generate_report(self, mock_pipeline):
        """Test des Report-Generierungs-Endpunkts"""
        # Mock der generate_report-Methode
        mock_instance = mock_pipeline.return_value
        mock_instance.generate_report.return_value = {
            'output_path': '/output/report.html'
        }
        
        response = self.app.post('/report', json={
            'input_path': self.json_file_path,
            'template': 'default',
            'max_workers': 2
        })
        
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['output_path'], '/output/report.html')
        
        # Überprüfe, ob generate_report mit den richtigen Parametern aufgerufen wurde
        mock_instance.generate_report.assert_called_once()
        args, kwargs = mock_instance.generate_report.call_args
        self.assertEqual(args[0], self.json_file_path)
        self.assertEqual(kwargs.get('template'), 'default')

    @patch('processor.app.processing_requests_total')
    @patch('processor.app.processing_errors_total')
    @patch('processor.app.PipelineIntegration')
    def test_stats_endpoint(self, mock_pipeline, mock_errors, mock_requests):
        """Test des Statistik-Endpunkts"""
        # Mock-Counter-Werte
        mock_requests.value = 100
        mock_errors.value = 5
        
        # Mock der PipelineIntegration-Statistiken
        mock_instance = mock_pipeline.return_value
        mock_instance.get_stats.return_value = {
            'active_workers': 2,
            'processed_items': 95,
            'avg_processing_time': 0.75
        }
        
        response = self.app.get('/stats')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['requests_processed'], 100)
        self.assertEqual(data['errors_total'], 5)
        self.assertEqual(data['active_workers'], 2)
        self.assertEqual(data['processed_items'], 95)
        self.assertEqual(data['avg_processing_time'], 0.75)
        self.assertIn('memory_usage_bytes', data)
        self.assertIn('uptime', data)

    @patch('processor.app.PipelineIntegration')
    def test_error_handling(self, mock_pipeline):
        """Test der Fehlerbehandlung"""
        # Mock einer Exception in der process_json-Methode
        mock_instance = mock_pipeline.return_value
        mock_instance.process_json.side_effect = ValueError("Ungültiges JSON-Format")
        
        response = self.app.post('/process/json', json={
            'file_path': self.json_file_path
        })
        
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['error'], "Ungültiges JSON-Format")
        self.assertFalse(data['success'])


if __name__ == "__main__":
    unittest.main() 