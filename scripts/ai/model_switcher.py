#!/usr/bin/env python3

"""
model_switcher.py

This script implements dynamic AI model selection based on task complexity.
It analyzes prompts and code context to determine the most appropriate model for the task,
optimizing for cost, performance, and GDPR compliance.
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent.parent / "logs" / "ai_model_usage.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("model_switcher")

# Define model configuration
MODELS = {
    "gpt4o_mini": {
        "name": "GPT-4o Mini",
        "provider": "OpenAI",
        "cost_per_1k_input": 0.15,
        "cost_per_1k_output": 0.60,
        "gdpr_compliant": False,
        "max_tokens": 128000,
        "region": "US",
        "api_endpoint": "https://api.openai.com/v1/chat/completions"
    },
    "claude_sonnet": {
        "name": "Claude Sonnet",
        "provider": "Anthropic",
        "cost_per_1k_input": 3.00,
        "cost_per_1k_output": 15.00,
        "gdpr_compliant": True,
        "max_tokens": 200000,
        "region": "EU via T-Systems",
        "api_endpoint": "https://t-systems-api.anthropic.com/v1/messages"
    },
    "deepseek_r1": {
        "name": "DeepSeek R1",
        "provider": "DeepSeek",
        "cost_per_1k_input": 0.50,
        "cost_per_1k_output": 2.50,
        "gdpr_compliant": False,  # Defaults to false due to China hosting
        "max_tokens": 32000,
        "region": "CN",
        "api_endpoint": "https://api.deepseek.com/v1/chat/completions"
    }
}

# Configuration thresholds for model selection
COMPLEXITY_THRESHOLDS = {
    "simple": 30,  # Simple tasks under this threshold
    "medium": 70,  # Medium complexity tasks under this threshold
    "complex": 100  # Complex tasks (everything else)
}

# Keywords that indicate complex reasoning tasks
REASONING_KEYWORDS = [
    "explain", "analyze", "compare", "contrast", "evaluate", 
    "debug", "architecture", "design pattern", "performance", 
    "security", "best practice", "optimize", "refactor",
    # Erweiterte Schlüsselwörter
    "dsgvo", "gdpr", "data protection", "privacy", "encryption",
    "compliance", "security", "vulnerability", "penetration test",
    "architecture", "scalability", "concurrency", "distributed",
    "asynchronous", "multithreading", "database design", "race condition"
]

# DSGVO-spezifische Schlüsselwörter mit höherer Gewichtung
GDPR_KEYWORDS = {
    "dsgvo": 10, "gdpr": 10, "data protection": 10, "privacy": 8, 
    "encryption": 7, "compliance": 7, "personal data": 8,
    "data subject": 9, "anonymization": 7, "pseudonymization": 7,
    "data security": 8, "sensitive data": 9, "data breach": 10
}

def analyze_complexity(prompt, code_context="", historical_data=None):
    """
    Analyze the complexity of a prompt and code context to determine the appropriate model.
    
    Args:
        prompt (str): The user prompt
        code_context (str, optional): Any associated code context
        historical_data (dict, optional): Historical complexity data from CostTracker
    
    Returns:
        dict: Complexity metrics including score and category
    """
    # Initialize metrics
    metrics = {
        "length_score": 0,
        "code_complexity_score": 0,
        "keyword_score": 0,
        "gdpr_score": 0,
        "technical_difficulty_score": 0,
        "historical_adjustment": 0,
        "total_score": 0,
        "complexity_level": "simple",
        "overall_score": 0
    }
    
    # 1. Length-based complexity (longer prompts are generally more complex)
    prompt_length = len(prompt)
    if prompt_length < 100:
        metrics["length_score"] = 10
    elif prompt_length < 500:
        metrics["length_score"] = 30
    else:
        metrics["length_score"] = 50
    
    # 2. Code complexity (if code context is provided)
    if code_context:
        lines = code_context.count("\n")
        # Count function/class definitions as indicators of complexity
        function_count = len(re.findall(r'(def|function|class)\s+\w+', code_context))
        
        # Check for advanced programming patterns
        has_async = "async " in code_context or "await " in code_context
        has_generators = "yield " in code_context
        has_complex_regex = code_context.count(r'[.*+?(){}|[\]^$]') > 5
        has_complex_imports = code_context.count("import ") > 5
        
        if lines < 50:
            metrics["code_complexity_score"] = 10
        elif lines < 200:
            metrics["code_complexity_score"] = 30
        else:
            metrics["code_complexity_score"] = 50
            
        # Add bonus for many functions/classes
        metrics["code_complexity_score"] += min(function_count * 2, 20)
        
        # Add bonus for advanced programming patterns
        if has_async:
            metrics["code_complexity_score"] += 15
        if has_generators:
            metrics["code_complexity_score"] += 10
        if has_complex_regex:
            metrics["code_complexity_score"] += 8
        if has_complex_imports:
            metrics["code_complexity_score"] += 5
    
    # 3. Keyword-based complexity (specific keywords indicate more complex tasks)
    prompt_lower = prompt.lower()
    keyword_count = sum(1 for keyword in REASONING_KEYWORDS if keyword.lower() in prompt_lower)
    metrics["keyword_score"] = min(keyword_count * 5, 30)
    
    # 4. DSGVO/GDPR complexity
    gdpr_score = 0
    for keyword, weight in GDPR_KEYWORDS.items():
        if keyword in prompt_lower:
            gdpr_score += weight
    metrics["gdpr_score"] = min(gdpr_score, 50)  # Cap at 50
    
    # 5. Technical difficulty assessment based on patterns
    technical_terms = [
        "encryption", "authentication", "tokenization", "secure hash",
        "concurrent", "thread safe", "race condition", "deadlock",
        "optimization algorithm", "time complexity", "space complexity",
        "distributed system", "microservice", "serverless"
    ]
    
    technical_score = sum(10 for term in technical_terms if term in prompt_lower)
    metrics["technical_difficulty_score"] = min(technical_score, 40)
    
    # 6. Historical complexity adjustment if data is available
    if historical_data and 'average_complexity' in historical_data:
        # Adjust current complexity by historical data (30% influence)
        historical_complexity = historical_data['average_complexity']
        adjustment = 0
        
        if 'similar_prompts' in historical_data and historical_data['similar_prompts'] > 0:
            adjustment = historical_complexity * 0.3
            metrics["historical_adjustment"] = adjustment
    
    # Calculate total complexity score
    metrics["total_score"] = (
        metrics["length_score"] + 
        metrics["code_complexity_score"] + 
        metrics["keyword_score"] +
        metrics["gdpr_score"] + 
        metrics["technical_difficulty_score"] +
        metrics["historical_adjustment"]
    )
    
    # Calculate normalized overall score (0-100)
    metrics["overall_score"] = min(metrics["total_score"], 100)
    
    # Determine complexity category
    if metrics["overall_score"] <= COMPLEXITY_THRESHOLDS["simple"]:
        metrics["complexity_level"] = "simple"
    elif metrics["overall_score"] <= COMPLEXITY_THRESHOLDS["medium"]:
        metrics["complexity_level"] = "medium"
    else:
        metrics["complexity_level"] = "complex"
    
    logger.info(f"Prompt complexity analysis: {metrics}")
    return metrics

def assign_model(complexity_metrics, gdpr_required=True):
    """
    Assign the appropriate model based on task complexity and GDPR requirements.
    
    Args:
        complexity_metrics (dict): Complexity metrics from analyze_complexity()
        gdpr_required (bool): Whether GDPR compliance is required
    
    Returns:
        str: Model ID to use
    """
    category = complexity_metrics["complexity_level"]
    
    # Simple decision tree for model selection
    if gdpr_required:
        # In GDPR mode, we prioritize compliant models
        if category == "simple":
            # For simple tasks with GDPR, use Claude Sonnet as DeepSeek is not GDPR compliant by default
            model = "claude_sonnet"
        elif category == "medium":
            # Medium complexity tasks also use Claude Sonnet in GDPR mode
            model = "claude_sonnet"
        else:
            # Complex tasks use Claude Sonnet in GDPR mode
            model = "claude_sonnet"
    else:
        # Non-GDPR mode allows using all models based on complexity
        if category == "simple":
            # Simple tasks use the cheapest option
            model = "gpt4o_mini"
        elif category == "medium":
            # Medium tasks use a middle-ground model
            model = "claude_sonnet"
        else:
            # Complex reasoning tasks use DeepSeek R1
            model = "deepseek_r1"
    
    logger.info(f"Selected model {model} for task with complexity {category}")
    return model

def estimate_tokens(text):
    """
    Estimate the number of tokens in a text string.
    This is a rough approximation - 1 token ≈ 4 chars for English text.
    
    Args:
        text (str): Input text
    
    Returns:
        int: Estimated token count
    """
    return len(text) // 4

def estimate_cost(model_id, input_text, output_length_estimate=200):
    """
    Estimate the cost of a model call.
    
    Args:
        model_id (str): ID of the model
        input_text (str): Input prompt text
        output_length_estimate (int): Estimated length of output in tokens
    
    Returns:
        float: Estimated cost in USD
    """
    model = MODELS[model_id]
    input_tokens = estimate_tokens(input_text)
    
    input_cost = (input_tokens / 1000) * model["cost_per_1k_input"]
    output_cost = (output_length_estimate / 1000) * model["cost_per_1k_output"]
    
    total_cost = input_cost + output_cost
    logger.info(f"Estimated cost for {model_id}: ${total_cost:.4f} USD")
    
    return total_cost

def anonymize_input(text):
    """
    Basic anonymization of potentially sensitive information in input text.
    
    Args:
        text (str): Input text to anonymize
    
    Returns:
        str: Anonymized text
    """
    # Patterns to detect and anonymize
    patterns = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),  # Email
        (r'\b(?:\d[ -]*?){13,16}\b', '[CREDIT_CARD]'),  # Credit card
        (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE_NUMBER]'),  # US Phone
        (r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b', '[SSN]'),  # SSN
        (r'(?i)\b(password|passwd|pwd)(\s*?[:=]\s*?)(\S+)', r'\1\2[REDACTED]'),  # Passwords
        (r'(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token)(\s*?[:=]\s*?)(\S+)', r'\1\2[REDACTED]')  # API keys
    ]
    
    anonymized = text
    for pattern, replacement in patterns:
        anonymized = re.sub(pattern, replacement, anonymized)
    
    return anonymized

def call_model(prompt, code_context="", gdpr_required=True, max_cost=None):
    """
    Main function to call the appropriate AI model based on task complexity.
    
    Args:
        prompt (str): User prompt
        code_context (str, optional): Code context if available
        gdpr_required (bool): Whether GDPR compliance is required
        max_cost (float, optional): Maximum allowed cost for this call
    
    Returns:
        dict: Response with model details and result
    """
    # Record start time for tracking
    start_time = datetime.now()
    
    # Step 1: Anonymize input if required
    if gdpr_required:
        prompt = anonymize_input(prompt)
        code_context = anonymize_input(code_context) if code_context else ""
    
    # Step 2: Analyze complexity
    complexity = analyze_complexity(prompt, code_context)
    
    # Step 3: Select model
    model_id = assign_model(complexity, gdpr_required)
    model_details = MODELS[model_id]
    
    # Step 4: Estimate cost
    combined_input = prompt + "\n" + code_context if code_context else prompt
    estimated_cost = estimate_cost(model_id, combined_input)
    
    # Step 5: Check if cost exceeds maximum allowed
    if max_cost and estimated_cost > max_cost:
        logger.warning(f"Estimated cost ${estimated_cost:.4f} exceeds maximum ${max_cost:.4f}")
        return {
            "error": "Cost limit exceeded",
            "estimated_cost": estimated_cost,
            "max_cost": max_cost,
            "model": model_details["name"]
        }
    
    # Step 6: Mock API call (in real implementation, this would call the actual API)
    # Note: This is a placeholder for the actual API call implementation
    logger.info(f"Calling model {model_id} for prompt with {len(prompt)} chars")
    
    # Mock response (replace with actual API call)
    response = {
        "model": model_details["name"],
        "provider": model_details["provider"],
        "gdpr_compliant": model_details["gdpr_compliant"],
        "estimated_cost": estimated_cost,
        "complexity_score": complexity["total_score"],
        "complexity_category": complexity["complexity_level"],
        "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        "input_length": len(combined_input),
        "result": "This is a mock response. Implement actual API call here."
    }
    
    # Log the call details to the audit trail
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model_details["name"],
        "complexity": complexity,
        "estimated_cost": estimated_cost,
        "prompt_length": len(prompt),
        "context_length": len(code_context) if code_context else 0,
        "processing_time_ms": response["processing_time_ms"]
    }
    
    # Create audit log directory if it doesn't exist
    audit_log_dir = Path(__file__).parent.parent.parent / "logs" / "ai_audit"
    audit_log_dir.mkdir(parents=True, exist_ok=True)
    
    # Write to audit log file
    audit_log_file = audit_log_dir / f"ai_audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(audit_log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    return response

# Example usage (for testing)
if __name__ == "__main__":
    # Test with a simple prompt
    simple_prompt = "Generate a function to add two numbers."
    simple_result = call_model(simple_prompt)
    print(f"Simple task model: {simple_result['model']}")
    
    # Test with a complex prompt
    complex_prompt = "Analyze the architecture of this codebase and suggest refactoring to improve performance and security."
    complex_code = """
    def process_data(input_data):
        # Process the data
        result = input_data * 2
        return result
        
    class DataProcessor:
        def __init__(self):
            self.data = []
            
        def add_data(self, item):
            self.data.append(item)
            
        def process_all(self):
            return [process_data(item) for item in self.data]
    """
    complex_result = call_model(complex_prompt, complex_code)
    print(f"Complex task model: {complex_result['model']}") 