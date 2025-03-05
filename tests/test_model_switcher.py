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
        
    def test_assign_model(self):
        """Test model assignment based on complexity metrics."""
        # Simple complexity
        simple_metrics = {"overall_score": 30, "complexity_level": "simple"}
        simple_model = assign_model(simple_metrics)
        self.assertEqual(simple_model, "gpt4o_mini",
                        "Simple prompts should use the most cost-effective model")
        
        # Medium complexity
        medium_metrics = {"overall_score": 55, "complexity_level": "medium"}
        medium_model = assign_model(medium_metrics)
        self.assertEqual(medium_model, "claude_sonnet",
                        "Medium complexity prompts should use a balanced model")
        
        # Complex reasoning
        complex_metrics = {"overall_score": 85, "complexity_level": "complex"}
        complex_model = assign_model(complex_metrics)
        self.assertEqual(complex_model, "deepseek_r1",
                        "Complex reasoning prompts should use the most powerful model")
        
        # Test GDPR requirement
        non_gdpr_model = assign_model(simple_metrics, gdpr_required=False)
        gdpr_model = assign_model(simple_metrics, gdpr_required=True)
        self.assertIsNotNone(non_gdpr_model, "Should return a model when GDPR is not required")
        self.assertIsNotNone(gdpr_model, "Should return a GDPR-compliant model when required")
    
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
        long_text = "This is a very long text with many sentences. " * 50
        
        # Costs should be proportional to text length
        short_cost_mini = estimate_cost("gpt4o_mini", short_text)
        long_cost_mini = estimate_cost("gpt4o_mini", long_text)
        self.assertLess(short_cost_mini, long_cost_mini,
                       "Longer texts should cost more with the same model")
        
        # More powerful models should cost more for the same text
        cost_mini = estimate_cost("gpt4o_mini", medium_text)
        cost_sonnet = estimate_cost("claude_sonnet", medium_text)
        cost_deepseek = estimate_cost("deepseek_r1", medium_text)
        
        self.assertLessEqual(cost_mini, cost_sonnet,
                           "GPT-4o Mini should cost less than Claude Sonnet")
        self.assertLessEqual(cost_sonnet, cost_deepseek,
                           "Claude Sonnet should cost less than DeepSeek R1")


if __name__ == "__main__":
    unittest.main() 