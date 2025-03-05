#!/usr/bin/env python3

"""
Tests for the model_switcher.py module.
"""

import unittest
import sys
from pathlib import Path
import os

# Add parent directory to path to allow imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from scripts.ai.model_switcher import analyze_complexity, assign_model, estimate_tokens, estimate_cost


class TestModelSwitcher(unittest.TestCase):
    """Test cases for the model_switcher module."""

    def test_analyze_complexity_simple_prompt(self):
        """Test complexity analysis for a simple prompt."""
        prompt = "Generate a function to add two numbers."
        metrics = analyze_complexity(prompt)
        
        self.assertLess(metrics["overall_score"], 40, 
                        "Simple prompts should have a low complexity score")
        self.assertEqual(metrics["complexity_level"], "simple",
                        "Simple prompts should be classified as 'simple'")
        
    def test_analyze_complexity_medium_prompt(self):
        """Test complexity analysis for a medium complexity prompt."""
        prompt = """Refactor this code to be more efficient:
        
        def slow_function(n):
            result = 0
            for i in range(n):
                for j in range(n):
                    result += i * j
            return result
        """
        code_context = """
        class Calculator:
            def __init__(self):
                self.value = 0
                
            def calculate(self, n):
                return slow_function(n)
        """
        metrics = analyze_complexity(prompt, code_context)
        
        self.assertGreaterEqual(metrics["overall_score"], 40,
                               "Medium complexity prompts should score higher")
        self.assertLess(metrics["overall_score"], 70,
                       "Medium complexity prompts should not score too high")
        self.assertEqual(metrics["complexity_level"], "medium",
                        "This should be classified as medium complexity")
        
    def test_analyze_complexity_complex_prompt(self):
        """Test complexity analysis for a complex reasoning prompt."""
        prompt = """Analyze the architecture of this distributed system and suggest improvements:
        
        The system consists of a web frontend, 3 microservices, and a database cluster.
        Service A handles authentication and forwards requests to Service B and C.
        Service B processes data and stores results in the database.
        Service C generates reports based on the processed data.
        
        The system is experiencing high latency during peak hours. Analyze potential 
        bottlenecks and suggest architectural improvements for better scalability.
        """
        metrics = analyze_complexity(prompt)
        
        self.assertGreaterEqual(metrics["overall_score"], 70,
                               "Complex reasoning prompts should score high")
        self.assertEqual(metrics["complexity_level"], "complex",
                        "This should be classified as complex")
    
    def test_analyze_complexity_gdpr_prompt(self):
        """Test complexity analysis for GDPR-related prompts."""
        prompt = """Implement a user data handling system that complies with GDPR requirements.
        
        The system should handle personal data, implement data subject access rights,
        and ensure proper encryption of sensitive information. We need to ensure 
        compliance with data protection regulations in the EU.
        """
        metrics = analyze_complexity(prompt)
        
        self.assertGreater(metrics["gdpr_score"], 0,
                          "GDPR-related prompts should have a positive GDPR score")
        self.assertEqual(metrics["complexity_level"], "complex",
                        "GDPR compliance tasks should be classified as complex")
    
    def test_analyze_complexity_with_historical_data(self):
        """Test complexity analysis with historical data adjustment."""
        prompt = "Generate a simple function."
        
        # Test without historical data
        metrics_without_history = analyze_complexity(prompt)
        
        # Test with historical data suggesting higher complexity
        historical_data = {
            "average_complexity": 60,
            "similar_prompts": 5
        }
        metrics_with_history = analyze_complexity(prompt, historical_data=historical_data)
        
        # The score should be higher with historical data
        self.assertGreater(metrics_with_history["overall_score"], 
                          metrics_without_history["overall_score"],
                          "Historical data should influence complexity score")
        self.assertGreater(metrics_with_history["historical_adjustment"], 0,
                          "Historical adjustment should be positive")
    
    def test_analyze_complexity_technical_terms(self):
        """Test complexity analysis for prompts with technical terms."""
        prompt = """Create a thread-safe implementation of a cache with optimized time complexity.
        The system should handle race conditions and prevent deadlocks during concurrent access.
        """
        metrics = analyze_complexity(prompt)
        
        self.assertGreater(metrics["technical_difficulty_score"], 0,
                          "Technical terms should increase the difficulty score")
    
    def test_assign_model(self):
        """Test model assignment based on complexity metrics."""
        # Simple complexity
        simple_metrics = {"overall_score": 30, "complexity_level": "simple"}
        simple_model = assign_model(simple_metrics, gdpr_required=False)
        self.assertEqual(simple_model, "gpt4o_mini",
                        "Simple prompts should use the most cost-effective model")
        
        # Medium complexity
        medium_metrics = {"overall_score": 55, "complexity_level": "medium"}
        medium_model = assign_model(medium_metrics, gdpr_required=False)
        self.assertEqual(medium_model, "claude_sonnet",
                        "Medium complexity prompts should use a balanced model")
        
        # Complex reasoning
        complex_metrics = {"overall_score": 85, "complexity_level": "complex"}
        complex_model = assign_model(complex_metrics, gdpr_required=False)
        self.assertEqual(complex_model, "deepseek_r1",
                        "Complex reasoning prompts should use the most powerful model")
        
        # Test GDPR requirement
        non_gdpr_model = assign_model(simple_metrics, gdpr_required=False)
        gdpr_model = assign_model(simple_metrics, gdpr_required=True)
        self.assertEqual(non_gdpr_model, "gpt4o_mini", "Should return gpt4o_mini when GDPR is not required")
        self.assertEqual(gdpr_model, "claude_sonnet", "Should return claude_sonnet when GDPR is required")
    
    def test_estimate_tokens(self):
        """Test token estimation function."""
        short_text = "This is a short text."
        medium_text = "This is a medium length text with several sentences. " * 10
        long_text = "This is a very long text with many sentences. " * 50
        
        short_tokens = estimate_tokens(short_text)
        medium_tokens = estimate_tokens(medium_text)
        long_tokens = estimate_tokens(long_text)
        
        self.assertLess(short_tokens, medium_tokens, 
                       "Shorter texts should have fewer tokens")
        self.assertLess(medium_tokens, long_tokens,
                       "Medium texts should have fewer tokens than long texts")
    
    def test_estimate_cost(self):
        """Test cost estimation function."""
        # Test with different models and text lengths
        short_text = "This is a short text."
        medium_text = "This is a medium length text with several sentences. " * 10
        long_text = "This is a very long text with many sentences. " * 50
        
        # Costs should be proportional to text length
        short_cost_mini = estimate_cost("gpt4o_mini", short_text)
        long_cost_mini = estimate_cost("gpt4o_mini", long_text)
        self.assertLess(short_cost_mini, long_cost_mini,
                       "Longer texts should cost more with the same model")
        
        # Model cost comparison based on actual pricing
        cost_mini = estimate_cost("gpt4o_mini", medium_text)
        cost_sonnet = estimate_cost("claude_sonnet", medium_text)
        cost_deepseek = estimate_cost("deepseek_r1", medium_text)
        
        self.assertLessEqual(cost_mini, cost_deepseek,
                           "GPT-4o Mini should cost less than DeepSeek R1")
        # Claude Sonnet is actually more expensive per token than DeepSeek R1
        self.assertGreater(cost_sonnet, cost_deepseek,
                           "Claude Sonnet should cost more than DeepSeek R1")
        self.assertGreater(cost_sonnet, cost_mini,
                           "Claude Sonnet should cost more than GPT-4o Mini")


if __name__ == "__main__":
    unittest.main() 