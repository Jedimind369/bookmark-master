# AI Optimization Components

This directory contains components for optimizing AI API usage, including dynamic model selection, caching, and cost tracking.

## Components

### 1. Dynamic Model Selection (`model_switcher.py`)

Automatically selects the most appropriate AI model based on:
- Task complexity
- GDPR requirements
- Cost constraints

The system analyzes prompts and code context to determine complexity, then routes to the appropriate model:
- Simple tasks → GPT-4o Mini (cost-effective)
- Medium complexity → Claude Sonnet (balanced)
- Complex reasoning → DeepSeek R1 (powerful reasoning)

### 2. Hybrid Caching System (`prompt_cache.py`)

Reduces API costs and improves response times through:
- Exact match caching - For identical prompts
- Semantic caching - For similar prompts using embeddings

Features:
- Configurable similarity threshold
- Time-based cache expiration
- Cache size management

### 3. Cost Tracking and Monitoring (`cost_tracker.py`)

Tracks and analyzes AI API usage costs:
- Records all API calls with detailed metrics
- Provides cost summaries and trends
- Monitors budget usage
- Generates optimization recommendations

### 4. Real-time Dashboard (`dashboard.py`)

Streamlit-based dashboard for visualizing:
- Current costs and budget status
- Usage trends over time
- Model efficiency comparisons
- Optimization recommendations

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Dynamic Model Selection

```python
from scripts.ai.model_switcher import call_model

# Simple usage
response = call_model(
    prompt="Generate a function to add two numbers",
    gdpr_required=True
)

# With code context
response = call_model(
    prompt="Optimize this function for performance",
    code_context="def slow_function(x, y):\n    result = 0\n    for i in range(x):\n        result += y\n    return result",
    gdpr_required=True
)
```

### Caching System

```python
from scripts.ai.prompt_cache import cached_call

def my_api_call(prompt):
    # Your actual API call implementation
    return "API response"

# Use caching
response = cached_call(
    prompt="What is the capital of France?",
    api_call_function=my_api_call,
    model_id="gpt4o_mini"
)
```

### Cost Tracking

```python
from scripts.ai.cost_tracker import CostTracker

# Initialize tracker
tracker = CostTracker()

# Record an API call
tracker.record_api_call(
    model_id="claude_sonnet",
    prompt_tokens=500,
    completion_tokens=200,
    cost=0.15,
    complexity_score=45.0
)

# Get cost summary
summary = tracker.get_cost_summary()
print(f"Today's cost: ${summary['today_cost']:.2f}")
```

### Dashboard

Run the dashboard:

```bash
streamlit run scripts/ai/dashboard.py
```

## GDPR Compliance

These components support GDPR compliance through:
- Input anonymization
- Detailed audit trails
- Model selection based on GDPR requirements
- Data minimization practices 