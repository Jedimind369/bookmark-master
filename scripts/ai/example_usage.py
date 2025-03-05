#!/usr/bin/env python3

"""
example_usage.py

Demonstrates how to use the AI optimization components together.
This script shows a complete workflow with dynamic model selection,
caching, and cost tracking.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
sys.path.append(str(parent_dir))

from scripts.ai.model_switcher import call_model, analyze_complexity, estimate_tokens, estimate_cost
from scripts.ai.prompt_cache import cached_call
from scripts.ai.cost_tracker import CostTracker

# Initialize the cost tracker
tracker = CostTracker({
    "daily_limit": 20.0,      # $20 per day
    "monthly_limit": 200.0,   # $200 per month
    "alert_threshold": 0.7    # Alert at 70% of budget
})

def api_call_with_tracking(prompt, code_context="", gdpr_required=True):
    """
    Integrated function that combines model selection, caching, and cost tracking.
    
    Args:
        prompt (str): The user prompt
        code_context (str, optional): Any associated code context
        gdpr_required (bool): Whether GDPR compliance is required
        
    Returns:
        dict: Response with model details and result
    """
    print(f"\n{'='*80}\nProcessing prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}\n{'='*80}")
    
    # Step 1: Analyze complexity to estimate costs before making the call
    complexity = analyze_complexity(prompt, code_context)
    print(f"Complexity analysis: {complexity['category']} (score: {complexity['total_score']})")
    
    # Step 2: Define the actual API call function that will be cached
    def actual_api_call(p):
        # This calls our model_switcher which handles model selection
        return call_model(p, code_context, gdpr_required)
    
    # Step 3: Use cached_call to check cache before making the actual API call
    response = cached_call(
        prompt=prompt,
        api_call_function=actual_api_call,
        use_semantic=True
    )
    
    # Step 4: Record the API call in the cost tracker (only if not from cache)
    if not response.get("cached", False):
        # Extract information from the response
        model_id = response.get("model_id", "unknown")
        estimated_cost = response.get("estimated_cost", 0.0)
        
        # Estimate token counts
        combined_input = prompt + "\n" + code_context if code_context else prompt
        prompt_tokens = estimate_tokens(combined_input)
        completion_tokens = 200  # Estimate for demonstration
        
        # Record in the cost tracker
        tracker.record_api_call(
            model_id=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=estimated_cost,
            cached=False,
            complexity_score=complexity["total_score"]
        )
        
        print(f"API call recorded: {model_id}, cost: ${estimated_cost:.4f}")
    else:
        print(f"Using cached response (type: {response.get('source', 'unknown')})")
        
        # Even for cached responses, we record them (with zero cost) for analytics
        tracker.record_api_call(
            model_id=response.get("model_id", "cached"),
            prompt_tokens=estimate_tokens(prompt),
            completion_tokens=0,
            cost=0.0,
            cached=True,
            complexity_score=complexity["total_score"]
        )
    
    return response

def main():
    """
    Main function demonstrating the complete workflow.
    """
    print("AI Optimization Components - Example Usage\n")
    
    # Example 1: Simple prompt (should use cheaper model)
    simple_prompt = "Generate a function to add two numbers in Python."
    simple_response = api_call_with_tracking(simple_prompt)
    
    # Example 2: Medium complexity prompt with code context
    medium_prompt = "Refactor this code to be more efficient and follow best practices."
    medium_code = """
def process_data(items):
    result = []
    for i in range(len(items)):
        if items[i] % 2 == 0:
            result.append(items[i] * 2)
        else:
            result.append(items[i] + 1)
    return result
    """
    medium_response = api_call_with_tracking(medium_prompt, medium_code)
    
    # Example 3: Complex reasoning prompt (should use more powerful model)
    complex_prompt = """
    Analyze the architecture of this code and suggest improvements for scalability, 
    performance, and security. Consider potential race conditions, memory leaks, 
    and security vulnerabilities.
    """
    complex_code = """
class DataProcessor:
    def __init__(self):
        self.data = {}
        self.processed = False
        
    def add_data(self, key, value):
        self.data[key] = value
        self.processed = False
        
    def process_all(self):
        result = {}
        for key, value in self.data.items():
            # Process the data
            result[key] = value * 2
        self.processed = True
        return result
        
    def get_processed_data(self):
        if not self.processed:
            return self.process_all()
        return self.data
    """
    complex_response = api_call_with_tracking(complex_prompt, complex_code)
    
    # Example 4: Repeat the simple prompt to demonstrate caching
    print("\nRepeating the simple prompt to demonstrate caching:")
    cached_response = api_call_with_tracking(simple_prompt)
    
    # Example 5: Similar prompt to demonstrate semantic caching
    similar_prompt = "Write a Python function that adds two numbers together."
    print("\nUsing a similar prompt to demonstrate semantic caching:")
    semantic_response = api_call_with_tracking(similar_prompt)
    
    # Get and display cost summary
    summary = tracker.get_cost_summary()
    print("\nCost Summary:")
    print(f"Today's cost: ${summary['today_cost']:.2f}")
    print(f"Month's cost: ${summary['month_cost']:.2f}")
    print(f"Total calls: {summary['total_calls']}")
    print(f"Cache hit rate: {summary['cache_hit_rate']:.1%}")
    
    # Get optimization recommendations
    recommendations = tracker.get_optimization_recommendations()
    print("\nOptimization Recommendations:")
    for rec in recommendations:
        print(f"[{rec['severity'].upper()}] {rec['message']}")

if __name__ == "__main__":
    main() 