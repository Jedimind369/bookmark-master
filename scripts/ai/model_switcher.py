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
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import caching and cost tracking modules
from prompt_cache import (
    cached_call, cache_response, get_cached_response, 
    CACHE_METRICS, CACHE_CONFIG
)
from cost_tracker import CostTracker

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

# Initialize cost tracker
cost_tracker = CostTracker()

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

# Keywords that indicate complex reasoning tasks with weights
REASONING_KEYWORDS = {
    # Analytische Aufgaben
    "explain": 1.5, "analyze": 1.8, "compare": 1.2, "contrast": 1.2, 
    "evaluate": 1.5, "critique": 1.7, "review": 1.3, "assess": 1.5,
    
    # Debugging und Optimierung
    "debug": 1.8, "optimize": 2.0, "refactor": 1.9, "performance": 1.7,
    "bottleneck": 1.8, "memory leak": 2.0, "race condition": 2.2,
    
    # Architektur und Design
    "architecture": 2.0, "design pattern": 1.9, "best practice": 1.5,
    "scalability": 1.8, "maintainability": 1.6, "extensibility": 1.7,
    
    # Komplexe Konzepte
    "concurrency": 2.2, "distributed": 2.1, "asynchronous": 1.9,
    "multithreading": 2.0, "parallelism": 2.0, "event-driven": 1.8,
    
    # Datenbank und Speicher
    "database design": 1.8, "query optimization": 1.9, "indexing": 1.7,
    "normalization": 1.8, "transaction": 1.7, "acid": 1.9,
    
    # Algorithmen
    "algorithm": 1.7, "complexity analysis": 2.0, "big o": 1.9,
    "dynamic programming": 2.1, "recursion": 1.8, "graph theory": 2.0
}

# DSGVO/GDPR-spezifische Schlüsselwörter mit höherer Gewichtung
GDPR_KEYWORDS = {
    # Grundlegende DSGVO-Begriffe
    "dsgvo": 3.0, "gdpr": 3.0, "datenschutz": 2.8, "privacy": 2.5,
    "data protection": 2.8, "datenschutzgrundverordnung": 3.0,
    
    # Personenbezogene Daten
    "personal data": 2.7, "personenbezogene daten": 2.7, 
    "sensitive data": 2.9, "special category data": 2.9,
    "personally identifiable": 2.8, "pii": 2.8,
    
    # Betroffenenrechte
    "data subject": 2.6, "betroffenenrechte": 2.6, 
    "right to access": 2.5, "auskunftsrecht": 2.5,
    "right to erasure": 2.7, "recht auf löschung": 2.7,
    "right to be forgotten": 2.7, "recht auf vergessenwerden": 2.7,
    "data portability": 2.5, "datenübertragbarkeit": 2.5,
    
    # Datensicherheit
    "data security": 2.6, "datensicherheit": 2.6,
    "encryption": 2.4, "verschlüsselung": 2.4,
    "pseudonymization": 2.5, "pseudonymisierung": 2.5,
    "anonymization": 2.5, "anonymisierung": 2.5,
    
    # Datenschutzverletzungen
    "data breach": 3.0, "datenpanne": 3.0, 
    "breach notification": 2.8, "meldepflicht": 2.8,
    
    # Verantwortlichkeiten
    "data controller": 2.4, "verantwortlicher": 2.4,
    "data processor": 2.4, "auftragsverarbeiter": 2.4,
    "dpa": 2.5, "data processing agreement": 2.5,
    "auftragsverarbeitungsvertrag": 2.5,
    
    # Compliance
    "compliance": 2.3, "accountability": 2.4, "rechenschaftspflicht": 2.4,
    "lawful basis": 2.5, "rechtsgrundlage": 2.5,
    "legitimate interest": 2.4, "berechtigtes interesse": 2.4,
    "consent": 2.6, "einwilligung": 2.6
}

# Sicherheits-spezifische Schlüsselwörter
SECURITY_KEYWORDS = {
    # Allgemeine Sicherheitsbegriffe
    "security": 2.5, "sicherheit": 2.5, "vulnerability": 2.8, 
    "schwachstelle": 2.8, "exploit": 2.9, "threat": 2.6, "bedrohung": 2.6,
    
    # Authentifizierung und Autorisierung
    "authentication": 2.4, "authentifizierung": 2.4, 
    "authorization": 2.4, "autorisierung": 2.4,
    "oauth": 2.3, "openid": 2.3, "jwt": 2.2, "mfa": 2.5, 
    "two-factor": 2.5, "zwei-faktor": 2.5,
    
    # Kryptographie
    "cryptography": 2.7, "kryptographie": 2.7, 
    "encryption": 2.6, "verschlüsselung": 2.6,
    "hash": 2.3, "salt": 2.3, "cipher": 2.5, "tls": 2.4, "ssl": 2.4,
    
    # Angriffe und Schwachstellen
    "injection": 2.8, "sql injection": 2.9, "xss": 2.8, 
    "cross-site scripting": 2.8, "csrf": 2.7, "cross-site request forgery": 2.7,
    "ddos": 2.7, "denial of service": 2.7, "mitm": 2.8, "man in the middle": 2.8,
    
    # Penetration Testing
    "penetration testing": 2.7, "pentest": 2.7, "pentesting": 2.7,
    "security audit": 2.6, "sicherheitsaudit": 2.6, "vulnerability scan": 2.6,
    
    # Sicherheitsmaßnahmen
    "firewall": 2.3, "waf": 2.4, "ids": 2.5, "ips": 2.5,
    "security policy": 2.4, "sicherheitsrichtlinie": 2.4,
    "patch management": 2.5, "security update": 2.4,
    
    # Datensicherheit
    "data leakage": 2.8, "data loss": 2.7, "dlp": 2.6,
    "sensitive information": 2.7, "confidential data": 2.7,
    
    # Compliance und Standards
    "iso 27001": 2.5, "nist": 2.5, "pci dss": 2.6, "hipaa": 2.6,
    "security compliance": 2.5, "security standard": 2.4
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
        "security_score": 0,
        "technical_difficulty_score": 0,
        "historical_adjustment": 0,
        "cache_adjustment": 0,
        "total_score": 0,
        "complexity_level": "simple",
        "overall_score": 0,
        "security_matches": [],
        "gdpr_matches": []
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
            metrics["code_complexity_score"] += 10
        if has_generators:
            metrics["code_complexity_score"] += 10
        if has_complex_regex:
            metrics["code_complexity_score"] += 5
        if has_complex_imports:
            metrics["code_complexity_score"] += 5
            
        # Check for complex language features
        if "metaclass" in code_context or "decorator" in code_context:
            metrics["code_complexity_score"] += 15
        if "threading" in code_context or "multiprocessing" in code_context:
            metrics["code_complexity_score"] += 15
        if "recursion" in code_context or "recursive" in code_context:
            metrics["code_complexity_score"] += 10
            
        # Cap the code complexity score
        metrics["code_complexity_score"] = min(metrics["code_complexity_score"], 100)
    
    # 3. Keyword-based complexity
    combined_text = prompt + " " + code_context
    
    # Check for reasoning keywords
    for keyword, weight in REASONING_KEYWORDS.items():
        if keyword.lower() in combined_text.lower():
            metrics["keyword_score"] += weight
            
    # 4. GDPR/Security analysis
    # Check for GDPR keywords
    for keyword, weight in GDPR_KEYWORDS.items():
        if keyword.lower() in combined_text.lower():
            metrics["gdpr_score"] += weight
            metrics["gdpr_matches"].append(keyword)
            
    # Check for security keywords
    for keyword, weight in SECURITY_KEYWORDS.items():
        if keyword.lower() in combined_text.lower():
            metrics["security_score"] += weight
            metrics["security_matches"].append(keyword)
    
    # 5. Technical difficulty assessment
    # Count technical terms as indicators of difficulty
    technical_terms = [
        "algorithm", "optimization", "complexity", "architecture", 
        "design pattern", "framework", "infrastructure", "deployment",
        "scalability", "performance", "security", "authentication",
        "authorization", "encryption", "database", "query", "index",
        "transaction", "concurrency", "parallelism", "distributed",
        "microservice", "container", "kubernetes", "docker", "ci/cd",
        "testing", "monitoring", "logging", "debugging", "profiling"
    ]
    
    term_count = sum(1 for term in technical_terms if term in combined_text.lower())
    metrics["technical_difficulty_score"] = min(term_count * 3, 50)
    
    # 6. Historical data adjustment (if provided)
    if historical_data:
        # Adjust based on similar prompts' complexity
        similar_prompts = historical_data.get("similar_prompts", [])
        if similar_prompts:
            avg_complexity = sum(p.get("complexity", 0) for p in similar_prompts) / len(similar_prompts)
            metrics["historical_adjustment"] = avg_complexity * 10  # Scale to match other scores
            
        # Adjust based on model performance
        model_performance = historical_data.get("model_performance", {})
        if model_performance:
            # If simpler models have performed poorly on similar tasks, increase complexity
            if model_performance.get("simple_model_failure_rate", 0) > 0.5:
                metrics["historical_adjustment"] += 15
            # If complex models have been overkill for similar tasks, decrease complexity
            if model_performance.get("complex_model_efficiency", 0) < 0.3:
                metrics["historical_adjustment"] -= 10
    
    # 7. Cache adjustment
    # If we have cache statistics, adjust based on hit rates
    cache_stats = CACHE_METRICS.get_summary() if hasattr(CACHE_METRICS, 'get_summary') else {}
    if cache_stats:
        hit_rate = cache_stats.get("hit_rate", 0)
        semantic_hit_rate = cache_stats.get("semantic_hit_rate", 0)
        
        # If we have high cache hit rates, we might be able to use simpler models
        if hit_rate > 0.7:
            metrics["cache_adjustment"] -= 10
        # If we have low semantic hit rates, we might need more complex models
        if semantic_hit_rate < 0.3 and hit_rate < 0.5:
            metrics["cache_adjustment"] += 10
    
    # Calculate total score
    metrics["total_score"] = (
        metrics["length_score"] + 
        metrics["code_complexity_score"] + 
        metrics["keyword_score"] + 
        metrics["gdpr_score"] + 
        metrics["security_score"] + 
        metrics["technical_difficulty_score"] + 
        metrics["historical_adjustment"] +
        metrics["cache_adjustment"]
    )
    
    # Normalize to 0-100 scale
    metrics["overall_score"] = min(max(metrics["total_score"] / 3, 0), 100)
    
    # Determine complexity level
    if metrics["overall_score"] < COMPLEXITY_THRESHOLDS["simple"]:
        metrics["complexity_level"] = "simple"
    elif metrics["overall_score"] < COMPLEXITY_THRESHOLDS["medium"]:
        metrics["complexity_level"] = "medium"
    else:
        metrics["complexity_level"] = "complex"
    
    # Log the complexity analysis
    logger.debug(f"Complexity analysis: {metrics}")
    
    return metrics

def select_model(prompt, code_context="", historical_data=None, budget_constraints=None):
    """
    Select the most appropriate model based on prompt complexity and other factors.
    
    Args:
        prompt (str): The user prompt
        code_context (str, optional): Any associated code context
        historical_data (dict, optional): Historical data from CostTracker
        budget_constraints (dict, optional): Budget constraints to consider
        
    Returns:
        dict: Selected model information
    """
    # Analyze complexity
    complexity = analyze_complexity(prompt, code_context, historical_data)
    complexity_level = complexity["complexity_level"]
    
    # Get available models
    available_models = list(MODELS.keys())
    
    # Filter models based on GDPR requirements if needed
    gdpr_required = len(complexity["gdpr_matches"]) > 0
    if gdpr_required:
        available_models = [m for m in available_models if MODELS[m]["gdpr_compliant"]]
        logger.info(f"GDPR keywords detected: {complexity['gdpr_matches']}. Filtering for GDPR-compliant models.")
    
    # Apply budget constraints if provided
    if budget_constraints:
        daily_budget_percent = budget_constraints.get("daily_budget_percent", 0)
        
        # If we're close to the daily budget, prefer cheaper models
        if daily_budget_percent > 80:
            # Sort models by cost
            available_models.sort(key=lambda m: MODELS[m]["cost_per_1k_input"] + MODELS[m]["cost_per_1k_output"])
            logger.info(f"Budget constraints active ({daily_budget_percent}% of daily budget used). Preferring cheaper models.")
    
    # Select model based on complexity
    if complexity_level == "simple":
        # For simple tasks, prefer the cheapest model
        available_models.sort(key=lambda m: MODELS[m]["cost_per_1k_input"] + MODELS[m]["cost_per_1k_output"])
        selected_model = available_models[0] if available_models else "gpt4o_mini"
    elif complexity_level == "medium":
        # For medium tasks, balance cost and capability
        # Use a middle-tier model if available
        medium_models = [m for m in available_models if MODELS[m]["cost_per_1k_input"] < 2.0]
        selected_model = medium_models[0] if medium_models else available_models[0]
    else:  # complex
        # For complex tasks, prefer the most capable model
        # Use the model with the highest token limit
        available_models.sort(key=lambda m: MODELS[m]["max_tokens"], reverse=True)
        selected_model = available_models[0] if available_models else "claude_sonnet"
    
    # Get the selected model details
    model_details = MODELS[selected_model].copy()
    model_details["model_id"] = selected_model
    model_details["complexity_analysis"] = complexity
    
    # Log the model selection
    logger.info(f"Selected model {selected_model} for complexity level {complexity_level} (score: {complexity['overall_score']:.1f})")
    
    return model_details

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

def call_model(prompt, code_context="", gdpr_required=True, max_cost=None, 
             use_cache=True, force_refresh=False, max_cache_age_hours=None):
    """
    Main function to call the appropriate AI model based on task complexity.
    
    Args:
        prompt (str): User prompt
        code_context (str, optional): Code context if available
        gdpr_required (bool): Whether GDPR compliance is required
        max_cost (float, optional): Maximum allowed cost for this call
        use_cache (bool): Whether to use caching
        force_refresh (bool): Whether to force a fresh API call
        max_cache_age_hours (int, optional): Maximum age of cache entries in hours
    
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
    model_details = select_model(prompt, code_context)
    
    # Step 4: Estimate cost
    combined_input = prompt + "\n" + code_context if code_context else prompt
    estimated_cost = estimate_cost(model_details["model_id"], combined_input)
    
    # Step 5: Check if cost exceeds maximum allowed
    if max_cost and estimated_cost > max_cost:
        logger.warning(f"Estimated cost ${estimated_cost:.4f} exceeds maximum ${max_cost:.4f}")
        return {
            "error": "Cost limit exceeded",
            "estimated_cost": estimated_cost,
            "max_cost": max_cost,
            "model": model_details["name"]
        }
    
    # Step 6: Check cache or call API
    request_id = f"{model_details['model_id']}_{int(datetime.now().timestamp())}"
    
    # Define the actual API call function
    def api_call_function(input_prompt):
        # This is where you would implement the actual API call to the model
        # For now, we'll use a mock response
        logger.info(f"Calling model {model_details['model_id']} for prompt with {len(input_prompt)} chars")
        
        # Mock response (replace with actual API call)
        response_text = f"This is a mock response from {model_details['name']}. Implement actual API call here."
        
        # Record the API call in the cost tracker
        input_tokens = estimate_tokens(input_prompt)
        output_tokens = len(response_text) // 4  # Rough estimate
        actual_cost = estimate_cost(model_details['model_id'], input_prompt, output_tokens)
        
        cost_tracker.record_api_call(
            model_id=model_details['model_id'],
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            cost=actual_cost,
            cached=False,
            complexity_score=complexity["overall_score"],
            request_type="completion",
            request_id=request_id
        )
        
        return response_text
    
    # Use cached_call to handle caching logic
    if use_cache and not force_refresh:
        cache_result = cached_call(
            prompt=combined_input,
            api_call_function=api_call_function,
            model_id=model_details['model_id'],
            use_semantic=True,
            force_refresh=force_refresh,
            max_age_hours=max_cache_age_hours
        )
        
        # If the result was cached, record it in the cost tracker with zero cost
        if cache_result.get("cached", False):
            cache_type = cache_result.get("source", "unknown")
            logger.info(f"Cache hit ({cache_type}) for prompt with model {model_details['model_id']}")
            
            # Record cached call with zero cost
            cost_tracker.record_api_call(
                model_id=model_details['model_id'],
                prompt_tokens=estimate_tokens(combined_input),
                completion_tokens=estimate_tokens(cache_result["response"]),
                cost=0.0,  # Zero cost for cached responses
                cached=True,
                complexity_score=complexity["overall_score"],
                request_type="completion",
                request_id=request_id
            )
            
            api_result = cache_result["response"]
        else:
            api_result = cache_result["response"]
    else:
        # Direct API call without caching
        api_result = api_call_function(combined_input)
    
    # Calculate processing time
    processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
    
    # Prepare the final response
    response = {
        "model": model_details["name"],
        "provider": model_details["provider"],
        "gdpr_compliant": model_details["gdpr_compliant"],
        "estimated_cost": estimated_cost,
        "complexity_score": complexity["total_score"],
        "complexity_category": complexity["complexity_level"],
        "processing_time_ms": processing_time_ms,
        "input_length": len(combined_input),
        "result": api_result,
        "cached": use_cache and not force_refresh and cache_result.get("cached", False) if 'cache_result' in locals() else False,
        "cache_type": cache_result.get("source", None) if 'cache_result' in locals() and cache_result.get("cached", False) else None
    }
    
    # Log the call details to the audit trail
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model_details["name"],
        "complexity": complexity,
        "estimated_cost": estimated_cost,
        "prompt_length": len(prompt),
        "context_length": len(code_context) if code_context else 0,
        "processing_time_ms": processing_time_ms,
        "cached": response.get("cached", False),
        "cache_type": response.get("cache_type", None)
    }
    
    # Create audit log directory if it doesn't exist
    audit_log_dir = Path(__file__).parent.parent.parent / "logs" / "ai_audit"
    audit_log_dir.mkdir(parents=True, exist_ok=True)
    
    # Write to audit log file
    audit_log_file = audit_log_dir / f"ai_audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(audit_log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    return response

def get_cache_statistics():
    """
    Get statistics about the cache usage.
    
    Returns:
        dict: Cache statistics
    """
    from prompt_cache import get_cache_stats
    
    # Get basic cache stats
    cache_stats = get_cache_stats()
    
    # Get cost tracker data for cached vs non-cached calls
    try:
        import sqlite3
        from pathlib import Path
        
        # Database path from cost_tracker
        DB_PATH = Path(__file__).parent.parent.parent / "data" / "ai_costs.db"
        
        if DB_PATH.exists():
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            # Get total costs with and without cache
            cursor.execute('''
            SELECT 
                SUM(CASE WHEN cached = 0 THEN cost ELSE 0 END) as direct_cost,
                SUM(CASE WHEN cached = 1 THEN cost ELSE 0 END) as cached_cost,
                COUNT(CASE WHEN cached = 0 THEN 1 ELSE NULL END) as direct_calls,
                COUNT(CASE WHEN cached = 1 THEN 1 ELSE NULL END) as cached_calls
            FROM api_calls
            WHERE timestamp >= datetime('now', '-30 day')
            ''')
            
            row = cursor.fetchone()
            if row:
                direct_cost, cached_cost, direct_calls, cached_calls = row
                
                # Calculate savings
                total_calls = (direct_calls or 0) + (cached_calls or 0)
                total_potential_cost = (direct_cost or 0) + ((direct_cost / direct_calls) * cached_calls if direct_calls and direct_calls > 0 else 0)
                savings = total_potential_cost - (direct_cost or 0) if total_potential_cost > 0 else 0
                
                cache_stats.update({
                    "cost_data": {
                        "direct_cost": direct_cost or 0,
                        "cached_cost": cached_cost or 0,
                        "direct_calls": direct_calls or 0,
                        "cached_calls": cached_calls or 0,
                        "total_calls": total_calls,
                        "estimated_savings": savings,
                        "savings_percentage": (savings / total_potential_cost) * 100 if total_potential_cost > 0 else 0
                    }
                })
            
            conn.close()
    except Exception as e:
        logger.error(f"Error getting cost data for cache statistics: {str(e)}")
        cache_stats["cost_data_error"] = str(e)
    
    return cache_stats

def optimize_cache_settings(target_hit_rate=0.5):
    """
    Optimize cache settings based on usage patterns.
    
    Args:
        target_hit_rate (float): Target cache hit rate (0-1)
        
    Returns:
        dict: Recommended cache settings
    """
    from prompt_cache import CACHE_CONFIG
    
    current_settings = CACHE_CONFIG.copy()
    current_hit_rate = CACHE_METRICS.hit_rate()
    
    recommendations = {
        "current_settings": current_settings,
        "current_hit_rate": current_hit_rate,
        "target_hit_rate": target_hit_rate,
        "recommendations": []
    }
    
    # If hit rate is too low, recommend decreasing similarity threshold
    if current_hit_rate < target_hit_rate:
        new_threshold = max(current_settings["semantic_threshold"] - 0.05, 0.7)
        recommendations["recommendations"].append({
            "setting": "semantic_threshold",
            "current": current_settings["semantic_threshold"],
            "recommended": new_threshold,
            "reason": f"Current hit rate ({current_hit_rate:.1%}) is below target ({target_hit_rate:.1%}). Lowering threshold will increase semantic matches."
        })
    
    # If hit rate is too high, might want to increase threshold for better precision
    elif current_hit_rate > target_hit_rate + 0.2:
        new_threshold = min(current_settings["semantic_threshold"] + 0.05, 0.95)
        recommendations["recommendations"].append({
            "setting": "semantic_threshold",
            "current": current_settings["semantic_threshold"],
            "recommended": new_threshold,
            "reason": f"Current hit rate ({current_hit_rate:.1%}) is well above target ({target_hit_rate:.1%}). Increasing threshold will improve precision."
        })
    
    # Check TTL settings
    if current_settings["ttl_days"] < 7:
        recommendations["recommendations"].append({
            "setting": "ttl_days",
            "current": current_settings["ttl_days"],
            "recommended": 14,
            "reason": "Short TTL may be causing unnecessary cache misses. Consider increasing if data doesn't change frequently."
        })
    
    return recommendations

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
    
    # Test caching
    print("\nTesting caching...")
    cached_result = call_model(simple_prompt, use_cache=True)
    print(f"Cached result: {cached_result['cached']}, Cache type: {cached_result.get('cache_type')}")
    
    # Test cache statistics
    print("\nCache Statistics:")
    stats = get_cache_statistics()
    print(f"Total entries: {stats.get('total_entries', 0)}")
    print(f"Hit rate: {stats.get('metrics', {}).get('hit_rate', 0):.1%}")
    
    if 'cost_data' in stats:
        cost_data = stats['cost_data']
        print(f"Estimated savings: ${cost_data.get('estimated_savings', 0):.2f}")
        print(f"Savings percentage: {cost_data.get('savings_percentage', 0):.1f}%")
    
    # Test cache optimization
    print("\nCache Optimization Recommendations:")
    recommendations = optimize_cache_settings(target_hit_rate=0.6)
    for rec in recommendations.get('recommendations', []):
        print(f"- {rec['setting']}: {rec['current']} → {rec['recommended']}")
        print(f"  Reason: {rec['reason']}") 