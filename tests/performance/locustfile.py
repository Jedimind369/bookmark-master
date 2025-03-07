#!/usr/bin/env python3

"""
locustfile.py

Performance tests for the AI system using Locust.
Tests the performance of the model switcher, prompt cache, and cost tracker under load.
"""

import os
import sys
import json
import random
from pathlib import Path
from locust import HttpUser, task, between

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.ai.model_switcher import analyze_complexity, select_model
from scripts.ai.prompt_cache import cached_call, get_cache_stats
from scripts.ai.cost_tracker import CostTracker


# Sample prompts with varying complexity
SIMPLE_PROMPTS = [
    "What is the weather today?",
    "How do I make pasta?",
    "What time is it in Tokyo?",
    "Who won the last World Cup?",
    "What is the capital of France?",
]

MEDIUM_PROMPTS = [
    "Explain the difference between REST and GraphQL APIs.",
    "What are the key principles of object-oriented programming?",
    "How does blockchain technology work?",
    "Compare and contrast SQL and NoSQL databases.",
    "What are the main features of Python 3.10?",
]

COMPLEX_PROMPTS = [
    "Implement a distributed system for GDPR-compliant data processing with encryption.",
    "Design a scalable microservice architecture for an e-commerce platform.",
    "Explain quantum computing and its implications for cryptography.",
    "Develop a strategy for implementing machine learning in a production environment.",
    "Create a comprehensive security plan for a cloud-based application.",
]


class AISystemUser(HttpUser):
    """
    Simulated user for performance testing of the AI system.
    
    Note: This doesn't actually make HTTP requests, but uses Locust's
    framework to simulate load on the AI system components.
    """
    
    wait_time = between(1, 3)  # Wait between 1-3 seconds between tasks
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cost_tracker = CostTracker()
        
        # Mock API call function
        self.api_call = lambda prompt: {
            "response": f"Response to: {prompt[:50]}...",
            "model_id": "test_model",
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": 20,
            "cost": 0.01 * (0.5 + random.random())  # Random cost between 0.005 and 0.015
        }
    
    @task(10)  # Higher weight for simple prompts
    def query_simple_prompt(self):
        """Test with a simple prompt."""
        prompt = random.choice(SIMPLE_PROMPTS)
        
        start_time = self.environment.runner.time()
        
        # Analyze complexity
        complexity = analyze_complexity(prompt)
        
        # Select model
        model = select_model(prompt)
        
        # Make cached API call
        result = cached_call(prompt, self.api_call, model_id=model.get('model_id', 'default_model'))
        
        # Record response time
        response_time = self.environment.runner.time() - start_time
        self.environment.events.request_success.fire(
            request_type="AI Query",
            name="Simple Prompt",
            response_time=response_time,
            response_length=len(json.dumps(result))
        )
    
    @task(5)  # Medium weight for medium prompts
    def query_medium_prompt(self):
        """Test with a medium complexity prompt."""
        prompt = random.choice(MEDIUM_PROMPTS)
        
        start_time = self.environment.runner.time()
        
        # Analyze complexity
        complexity = analyze_complexity(prompt)
        
        # Select model
        model = select_model(prompt)
        
        # Make cached API call
        result = cached_call(prompt, self.api_call, model_id=model.get('model_id', 'default_model'))
        
        # Record response time
        response_time = self.environment.runner.time() - start_time
        self.environment.events.request_success.fire(
            request_type="AI Query",
            name="Medium Prompt",
            response_time=response_time,
            response_length=len(json.dumps(result))
        )
    
    @task(2)  # Lower weight for complex prompts
    def query_complex_prompt(self):
        """Test with a complex prompt."""
        prompt = random.choice(COMPLEX_PROMPTS)
        
        start_time = self.environment.runner.time()
        
        # Analyze complexity
        complexity = analyze_complexity(prompt)
        
        # Select model
        model = select_model(prompt)
        
        # Make cached API call
        result = cached_call(prompt, self.api_call, model_id=model.get('model_id', 'default_model'))
        
        # Record response time
        response_time = self.environment.runner.time() - start_time
        self.environment.events.request_success.fire(
            request_type="AI Query",
            name="Complex Prompt",
            response_time=response_time,
            response_length=len(json.dumps(result))
        )
    
    @task(1)  # Lowest weight for cache stats
    def get_system_stats(self):
        """Get system statistics."""
        start_time = self.environment.runner.time()
        
        # Get cache statistics
        cache_stats = get_cache_stats()
        
        # Get cost summary
        cost_summary = self.cost_tracker.get_cost_summary()
        
        # Record response time
        response_time = self.environment.runner.time() - start_time
        self.environment.events.request_success.fire(
            request_type="System Stats",
            name="Cache and Cost Stats",
            response_time=response_time,
            response_length=len(json.dumps(cache_stats)) + len(json.dumps(cost_summary))
        )


# To run this test:
# locust -f locustfile.py --headless -u 10 -r 1 -t 1m
# This will run a headless test with 10 users, spawning at a rate of 1 user per second, for 1 minute. 