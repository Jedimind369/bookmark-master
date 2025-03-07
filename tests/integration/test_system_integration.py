#!/usr/bin/env python3

"""
test_system_integration.py

Integration tests for the AI system components, testing the interaction between
model_switcher, prompt_cache, and cost_tracker.
"""

import os
import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.ai.model_switcher import analyze_complexity, select_model
from scripts.ai.prompt_cache import cached_call, get_cache_stats, clean_cache
from scripts.ai.cost_tracker import CostTracker


class TestSystemIntegration(unittest.TestCase):
    """Integration tests for the AI system components."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.temp_dir.name) / "cache"
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.logs_dir = Path(self.temp_dir.name) / "logs"
        
        # Create directories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up environment variables for testing
        self.original_cache_dir = os.environ.get("CACHE_DIR")
        self.original_data_dir = os.environ.get("DATA_DIR")
        self.original_logs_dir = os.environ.get("LOGS_DIR")
        
        os.environ["CACHE_DIR"] = str(self.cache_dir)
        os.environ["DATA_DIR"] = str(self.data_dir)
        os.environ["LOGS_DIR"] = str(self.logs_dir)
        
        # Initialize a test database
        self.db_path = self.data_dir / "ai_costs.db"
        self._setup_test_db()
        
        # Initialize cost tracker with test budget
        self.cost_tracker = CostTracker(budget={
            "daily_limit": 5.0,
            "monthly_limit": 50.0,
            "alert_threshold": 0.8
        })

    def tearDown(self):
        """Clean up after tests."""
        # Restore original environment variables
        if self.original_cache_dir:
            os.environ["CACHE_DIR"] = self.original_cache_dir
        else:
            os.environ.pop("CACHE_DIR", None)
            
        if self.original_data_dir:
            os.environ["DATA_DIR"] = self.original_data_dir
        else:
            os.environ.pop("DATA_DIR", None)
            
        if self.original_logs_dir:
            os.environ["LOGS_DIR"] = self.original_logs_dir
        else:
            os.environ.pop("LOGS_DIR", None)
        
        # Clean up temporary directory
        self.temp_dir.cleanup()

    def _setup_test_db(self):
        """Set up a test database for cost tracking."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            model_id TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            cost REAL,
            request_type TEXT,
            cached BOOLEAN,
            complexity_score REAL,
            request_id TEXT UNIQUE
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_budgets (
            date TEXT PRIMARY KEY,
            budget_limit REAL,
            budget_used REAL,
            alert_sent BOOLEAN DEFAULT 0
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS monthly_budgets (
            month TEXT PRIMARY KEY,
            budget_limit REAL,
            budget_used REAL,
            alert_sent BOOLEAN DEFAULT 0
        )
        ''')
        
        conn.commit()
        conn.close()

    @patch('scripts.ai.prompt_cache.CACHE_DIR')
    @patch('scripts.ai.cost_tracker.DB_PATH')
    def test_end_to_end_workflow(self, mock_db_path, mock_cache_dir):
        """Test the end-to-end workflow of the AI system."""
        # Set up mocks
        mock_db_path.return_value = self.db_path
        mock_cache_dir.return_value = self.cache_dir
        
        # Test prompts with different complexity levels
        simple_prompt = "What is the weather today?"
        medium_prompt = "Explain the difference between REST and GraphQL APIs."
        complex_prompt = "Implement a distributed system for GDPR-compliant data processing with encryption and secure authentication."
        
        # 1. Test complexity analysis
        simple_score = analyze_complexity(simple_prompt)
        medium_score = analyze_complexity(medium_prompt)
        complex_score = analyze_complexity(complex_prompt)
        
        # Verify complexity scores are in ascending order
        self.assertLess(simple_score['overall_score'], medium_score['overall_score'])
        self.assertLess(medium_score['overall_score'], complex_score['overall_score'])
        
        # 2. Test model selection based on complexity
        simple_model = select_model(simple_prompt)
        medium_model = select_model(medium_prompt)
        complex_model = select_model(complex_prompt)
        
        # Verify different models are selected based on complexity
        self.assertIn('model_id', simple_model)
        self.assertIn('model_id', medium_model)
        self.assertIn('model_id', complex_model)
        
        # 3. Test cached API calls with mock API function
        def mock_api_call(prompt):
            """Mock API call function that returns a response based on the prompt."""
            return {
                "response": f"Response to: {prompt}",
                "model_id": "test_model",
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 20,
                "cost": 0.01
            }
        
        # First call should be a cache miss
        with patch('scripts.ai.cost_tracker.CostTracker.record_api_call') as mock_record:
            result1 = cached_call(simple_prompt, mock_api_call)
            # Verify API call was recorded
            mock_record.assert_called_once()
        
        # Second call with same prompt should be a cache hit
        with patch('scripts.ai.cost_tracker.CostTracker.record_api_call') as mock_record:
            result2 = cached_call(simple_prompt, mock_api_call)
            # Verify no new API call was recorded
            mock_record.assert_not_called()
        
        # Verify results are the same
        self.assertEqual(result1['response'], result2['response'])
        
        # 4. Test cache statistics
        cache_stats = get_cache_stats()
        self.assertGreater(cache_stats['total_entries'], 0)
        self.assertIn('metrics', cache_stats)
        
        # 5. Test cost tracking
        # Record some API calls
        self.cost_tracker.record_api_call(
            model_id="gpt4o_mini",
            prompt_tokens=10,
            completion_tokens=20,
            cost=0.05,
            complexity_score=simple_score['overall_score']
        )
        
        self.cost_tracker.record_api_call(
            model_id="claude_sonnet",
            prompt_tokens=30,
            completion_tokens=50,
            cost=0.15,
            complexity_score=complex_score['overall_score']
        )
        
        # Get cost summary
        cost_summary = self.cost_tracker.get_cost_summary()
        
        # Verify cost tracking
        self.assertGreaterEqual(cost_summary['today_cost'], 0.20)  # 0.05 + 0.15
        self.assertIn('daily_budget', cost_summary)
        self.assertIn('monthly_budget', cost_summary)
        
        # Get model costs
        model_costs = self.cost_tracker.get_model_costs(days=1)
        self.assertGreaterEqual(len(model_costs), 2)  # At least two models used
        
        # 6. Test optimization recommendations
        recommendations = self.cost_tracker.get_optimization_recommendations()
        self.assertIsInstance(recommendations, list)


if __name__ == '__main__':
    unittest.main() 