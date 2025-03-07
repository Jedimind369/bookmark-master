#!/usr/bin/env python3

"""
dashboard.py

A Streamlit dashboard for real-time monitoring of AI API usage costs,
cache performance metrics, and system health.
"""

import os
import sys
import datetime
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
import requests
import psutil  # Für Systemmetriken
import time
from model_switcher import get_cache_statistics, optimize_cache_settings

# Add the parent directory to the path to import our modules
sys.path.append(str(Path(__file__).parent))

# Import our modules
from cost_tracker import CostTracker
from prompt_cache import get_cache_stats, CACHE_METRICS

# Slack-Webhook-URL für Benachrichtigungen (aus Umgebungsvariable oder Konfigurationsdatei)
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# Set up page config
st.set_page_config(
    page_title="AI API Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS for styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
    }
    .metric-label {
        font-size: 14px;
        color: #555;
    }
    .good {
        color: #0f8c79;
    }
    .warning {
        color: #ff9800;
    }
    .critical {
        color: #e53935;
    }
    .recommendation {
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 10px;
        margin: 5px 0;
    }
    .recommendation.high {
        border-left: 4px solid #e53935;
    }
    .recommendation.medium {
        border-left: 4px solid #ff9800;
    }
    .recommendation.low {
        border-left: 4px solid #0f8c79;
    }
    .cache-metric {
        background-color: #e8f4f8;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .cache-metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #1e88e5;
    }
    .cache-metric-label {
        font-size: 14px;
        color: #555;
    }
    .system-metric {
        background-color: #f1f8e9;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .system-metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #43a047;
    }
    .system-metric-label {
        font-size: 14px;
        color: #555;
    }
    .notification {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
        background-color: #e8f4f8;
        border-left: 4px solid #1e88e5;
    }
    .optimization-tip {
        background-color: #fff8e1;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        border-left: 4px solid #ffb300;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.datetime.now()
if 'notifications_sent' not in st.session_state:
    st.session_state.notifications_sent = set()

def send_slack_alert(message, emoji="🚨", webhook_url=SLACK_WEBHOOK_URL):
    """
    Sendet eine Benachrichtigung an Slack.
    
    Args:
        message (str): Die zu sendende Nachricht
        emoji (str): Das zu verwendende Emoji
        webhook_url (str): Die Webhook-URL für Slack
    
    Returns:
        bool: True, wenn die Nachricht erfolgreich gesendet wurde, sonst False
    """
    if not webhook_url:
        st.warning("Slack-Webhook-URL nicht konfiguriert. Benachrichtigungen werden nicht gesendet.")
        return False
    
    try:
        payload = {
            "text": f"{emoji} {message}"
        }
        response = requests.post(webhook_url, json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Fehler beim Senden der Slack-Benachrichtigung: {str(e)}")
        return False

def check_and_send_alerts(summary):
    """
    Überprüft, ob Warnungen gesendet werden müssen, und sendet sie bei Bedarf.
    
    Args:
        summary (dict): Zusammenfassung der Kosten und Budget-Informationen
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Tägliches Budget-Alert
    daily_pct = (summary['today_cost'] / summary['budget_daily']) * 100
    if daily_pct >= 80 and f"daily_budget_{today}" not in st.session_state.notifications_sent:
        message = f"Tägliches Budget zu {daily_pct:.1f}% aufgebraucht! (${summary['today_cost']:.2f} von ${summary['budget_daily']:.2f})"
        if send_slack_alert(message, "💰"):
            st.session_state.notifications_sent.add(f"daily_budget_{today}")
    
    # Monatliches Budget-Alert
    monthly_pct = (summary['monthly_cost'] / summary['budget_monthly']) * 100
    current_month = datetime.datetime.now().strftime("%Y-%m")
    if monthly_pct >= 80 and f"monthly_budget_{current_month}" not in st.session_state.notifications_sent:
        message = f"Monatliches Budget zu {monthly_pct:.1f}% aufgebraucht! (${summary['monthly_cost']:.2f} von ${summary['budget_monthly']:.2f})"
        if send_slack_alert(message, "📅"):
            st.session_state.notifications_sent.add(f"monthly_budget_{current_month}")
    
    # Niedrige Cache-Trefferquote
    if summary['cache_hit_rate'] < 0.3 and f"low_cache_hit_{today}" not in st.session_state.notifications_sent:
        message = f"Niedrige Cache-Trefferquote: {summary['cache_hit_rate']*100:.1f}%. Überprüfen Sie die Cache-Einstellungen."
        if send_slack_alert(message, "🔍"):
            st.session_state.notifications_sent.add(f"low_cache_hit_{today}")

def get_system_metrics():
    """
    Erfasst Systemmetriken wie CPU-Auslastung, Speicherverbrauch und Festplattennutzung.
    
    Returns:
        dict: Systemmetriken
    """
    try:
        # CPU-Auslastung
        cpu_percent = psutil.cpu_percent(interval=0.5)
        
        # Speichernutzung
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024 ** 3)  # In GB
        memory_total_gb = memory.total / (1024 ** 3)  # In GB
        
        # Festplattennutzung
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024 ** 3)  # In GB
        disk_total_gb = disk.total / (1024 ** 3)  # In GB
        
        # Netzwerkstatistiken
        net_io = psutil.net_io_counters()
        net_sent_mb = net_io.bytes_sent / (1024 ** 2)  # In MB
        net_recv_mb = net_io.bytes_recv / (1024 ** 2)  # In MB
        
        # Prozessinformationen
        process = psutil.Process(os.getpid())
        process_memory_mb = process.memory_info().rss / (1024 ** 2)  # In MB
        process_cpu_percent = process.cpu_percent(interval=0.5)
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_used_gb": memory_used_gb,
            "memory_total_gb": memory_total_gb,
            "disk_percent": disk_percent,
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "net_sent_mb": net_sent_mb,
            "net_recv_mb": net_recv_mb,
            "process_memory_mb": process_memory_mb,
            "process_cpu_percent": process_cpu_percent
        }
    except Exception as e:
        st.error(f"Fehler beim Erfassen der Systemmetriken: {str(e)}")
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used_gb": 0,
            "memory_total_gb": 1,
            "disk_percent": 0,
            "disk_used_gb": 0,
            "disk_total_gb": 1,
            "net_sent_mb": 0,
            "net_recv_mb": 0,
            "process_memory_mb": 0,
            "process_cpu_percent": 0
        }

def generate_mock_data():
    """Generate mock data for demonstration purposes"""
    # Summary costs
    summary = {
        "today_cost": 2.45,
        "monthly_cost": 28.75,
        "total_cost": 145.32,
        "total_calls": 1250,
        "cache_hit_rate": 0.68,
        "budget_daily": 5.00,
        "budget_monthly": 100.00,
        "budget_daily_remaining": 2.55,
        "budget_monthly_remaining": 71.25
    }
    
    # Daily costs
    daily_costs = pd.DataFrame({
        "date": pd.date_range(end=datetime.datetime.now(), periods=14, freq='D'),
        "cost": [1.2, 0.8, 1.5, 2.1, 0.9, 1.8, 2.5, 1.7, 2.2, 1.9, 2.3, 2.0, 2.4, 2.45],
        "calls": [50, 35, 65, 90, 40, 75, 110, 70, 95, 80, 100, 85, 105, 110],
        "cache_hits": [30, 20, 40, 55, 25, 45, 70, 45, 60, 50, 65, 55, 70, 75]
    })
    
    # Model costs
    model_costs = pd.DataFrame({
        "model": ["gpt-4", "gpt-3.5-turbo", "claude-2", "llama-2"],
        "cost": [15.50, 5.25, 7.00, 1.00],
        "calls": [150, 500, 350, 250],
        "tokens": [75000, 250000, 175000, 125000]
    })
    
    # Optimization recommendations
    recommendations = [
        {"message": "Consider using gpt-3.5-turbo for simple tasks to reduce costs", "severity": "high"},
        {"message": "Increase cache TTL for frequently accessed prompts", "severity": "medium"},
        {"message": "Batch similar requests to reduce API calls", "severity": "low"}
    ]
    
    # Cache metrics
    cache_metrics = {
        "exact_hits": 850,
        "semantic_hits": 250,
        "misses": 500,
        "hit_rate": 0.68,
        "semantic_hit_rate": 0.23,
        "time_saved": 1250.5,  # seconds
        "total_entries": 750,
        "total_size_kb": 1250.5
    }
    
    # Cache optimization recommendations
    cache_optimization = {
        "current_settings": {
            "semantic_threshold": 0.85,
            "ttl_days": 30
        },
        "current_hit_rate": 0.68,
        "target_hit_rate": 0.75,
        "recommendations": [
            {
                "setting": "semantic_threshold",
                "current": 0.85,
                "recommended": 0.80,
                "reason": "Lowering threshold will increase semantic matches."
            },
            {
                "setting": "ttl_days",
                "current": 30,
                "recommended": 45,
                "reason": "Increasing TTL will retain useful cache entries longer."
            }
        ]
    }
    
    # System metrics
    system_metrics = {
        "cpu_percent": 35.2,
        "memory_percent": 42.7,
        "memory_used_gb": 3.2,
        "memory_total_gb": 8.0,
        "disk_percent": 65.3,
        "disk_used_gb": 156.8,
        "disk_total_gb": 240.0,
        "net_sent_mb": 128.5,
        "net_recv_mb": 256.3,
        "process_memory_mb": 125.4,
        "process_cpu_percent": 12.3
    }
    
    return summary, daily_costs, model_costs, recommendations, cache_metrics, cache_optimization, system_metrics

def load_data():
    """Load real data from CostTracker and cache stats"""
    try:
        # Initialize CostTracker
        tracker = CostTracker()
        
        # Get cost summary
        summary = tracker.get_cost_summary()
        
        # Get daily costs
        daily_costs = tracker.get_daily_costs(days=14)
        
        # Get model costs
        model_costs = tracker.get_model_costs()
        
        # Get optimization recommendations
        recommendations = tracker.get_optimization_recommendations()
        
        # Get cache metrics from model_switcher (erweiterte Statistiken)
        cache_stats = get_cache_statistics()
        
        # Extrahiere die Metriken aus den Cache-Statistiken
        cache_metrics = cache_stats.get("metrics", {})
        cache_metrics.update({
            "total_entries": cache_stats.get("total_entries", 0),
            "total_size_kb": cache_stats.get("total_size_kb", 0)
        })
        
        # Wenn cost_data in den Cache-Statistiken vorhanden ist, füge sie hinzu
        if "cost_data" in cache_stats:
            cache_metrics.update({
                "estimated_savings": cache_stats["cost_data"].get("estimated_savings", 0),
                "savings_percentage": cache_stats["cost_data"].get("savings_percentage", 0)
            })
        
        # Get cache optimization recommendations
        cache_optimization = optimize_cache_settings(target_hit_rate=0.75)
        
        # Get system metrics
        system_metrics = get_system_metrics()
        
        return summary, daily_costs, model_costs, recommendations, cache_metrics, cache_optimization, system_metrics
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        # Fall back to mock data
        return generate_mock_data()

# Sidebar
st.sidebar.title("Dashboard Controls")

# Refresh button
if st.sidebar.button("Refresh Data"):
    st.session_state.last_refresh = datetime.datetime.now()

# Auto-refresh toggle
auto_refresh = st.sidebar.checkbox("Auto-refresh (1 min)", value=True)
if auto_refresh:
    if (datetime.datetime.now() - st.session_state.last_refresh).seconds > 60:
        st.session_state.last_refresh = datetime.datetime.now()
        st.experimental_rerun()

# Date range for charts
st.sidebar.subheader("Chart Settings")
days_to_show = st.sidebar.slider("Days to show", min_value=7, max_value=30, value=14)

# Model filter
st.sidebar.subheader("Filters")
# This would be populated with actual models from the data
models_to_show = st.sidebar.multiselect(
    "Models to display",
    ["gpt-4", "gpt-3.5-turbo", "claude-2", "llama-2"],
    default=["gpt-4", "gpt-3.5-turbo", "claude-2", "llama-2"]
)

# Benachrichtigungseinstellungen
st.sidebar.subheader("Notifications")
enable_notifications = st.sidebar.checkbox("Enable Slack Notifications", value=SLACK_WEBHOOK_URL != "")
if enable_notifications and SLACK_WEBHOOK_URL == "":
    st.sidebar.warning("Slack webhook URL not configured. Set the SLACK_WEBHOOK_URL environment variable.")

# Notification thresholds
if enable_notifications:
    budget_threshold = st.sidebar.slider("Budget Alert Threshold (%)", min_value=50, max_value=95, value=80)
    cache_hit_threshold = st.sidebar.slider("Low Cache Hit Rate Alert (%)", min_value=10, max_value=50, value=30)

# Export data
st.sidebar.subheader("Export Data")
export_format = st.sidebar.selectbox("Export format", ["CSV", "JSON"])
if st.sidebar.button("Export Data"):
    # This would call the export function from CostTracker
    st.sidebar.success(f"Data exported in {export_format} format")

# RAG-Hinweis
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Future Enhancement:** Consider integrating Retrieval-Augmented Generation (RAG) for semantic search and automated content enrichment."
)

# Last refresh time
st.sidebar.markdown("---")
st.sidebar.markdown(f"Last refreshed: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")

# Load data
summary, daily_costs, model_costs, recommendations, cache_metrics, cache_optimization, system_metrics = load_data()

# Main content
st.title("AI API Usage Dashboard")

# Top metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Today's Cost</div>
            <div class="metric-value">${summary['today_cost']:.2f}</div>
            <div class="metric-label">Budget: ${summary['budget_daily']:.2f}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Monthly Cost</div>
            <div class="metric-value">${summary['monthly_cost']:.2f}</div>
            <div class="metric-label">Budget: ${summary['budget_monthly']:.2f}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

with col3:
    # Calculate percentage of budget used
    daily_pct = (summary['today_cost'] / summary['budget_daily']) * 100
    monthly_pct = (summary['monthly_cost'] / summary['budget_monthly']) * 100
    
    # Determine color based on percentage
    daily_color = "good" if daily_pct < 70 else "warning" if daily_pct < 90 else "critical"
    monthly_color = "good" if monthly_pct < 70 else "warning" if monthly_pct < 90 else "critical"
    
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Budget Remaining</div>
            <div class="metric-value ${daily_color}">Daily: ${summary['budget_daily_remaining']:.2f}</div>
            <div class="metric-value ${monthly_color}">Monthly: ${summary['budget_monthly_remaining']:.2f}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

with col4:
    # Cache hit rate color
    hit_rate_pct = summary['cache_hit_rate'] * 100
    hit_rate_color = "good" if hit_rate_pct > 60 else "warning" if hit_rate_pct > 40 else "critical"
    
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Cache Performance</div>
            <div class="metric-value ${hit_rate_color}">{hit_rate_pct:.1f}% Hit Rate</div>
            <div class="metric-label">Total Calls: {summary['total_calls']}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

# Cache metrics section
st.header("Cache Performance Metrics")

cache_col1, cache_col2, cache_col3, cache_col4 = st.columns(4)

with cache_col1:
    st.markdown(
        f"""
        <div class="cache-metric">
            <div class="cache-metric-label">Cache Hit Types</div>
            <div class="cache-metric-value">{cache_metrics['exact_hits']} Exact</div>
            <div class="cache-metric-value">{cache_metrics['semantic_hits']} Semantic</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

with cache_col2:
    st.markdown(
        f"""
        <div class="cache-metric">
            <div class="cache-metric-label">Hit Rates</div>
            <div class="cache-metric-value">{cache_metrics['hit_rate']*100:.1f}% Overall</div>
            <div class="cache-metric-value">{cache_metrics['semantic_hit_rate']*100:.1f}% Semantic</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

with cache_col3:
    # Convert time saved to minutes and hours if large enough
    time_saved = cache_metrics['time_saved']
    time_saved_str = f"{time_saved:.1f} sec"
    if time_saved > 60:
        minutes = time_saved / 60
        if minutes > 60:
            hours = minutes / 60
            time_saved_str = f"{hours:.1f} hours"
        else:
            time_saved_str = f"{minutes:.1f} min"
    
    st.markdown(
        f"""
        <div class="cache-metric">
            <div class="cache-metric-label">Efficiency</div>
            <div class="cache-metric-value">{time_saved_str}</div>
            <div class="cache-metric-label">Time Saved</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

with cache_col4:
    # Format size in KB, MB, or GB as appropriate
    size_kb = cache_metrics['total_size_kb']
    size_str = f"{size_kb:.1f} KB"
    if size_kb > 1024:
        size_mb = size_kb / 1024
        if size_mb > 1024:
            size_gb = size_mb / 1024
            size_str = f"{size_gb:.2f} GB"
        else:
            size_str = f"{size_mb:.2f} MB"
    
    st.markdown(
        f"""
        <div class="cache-metric">
            <div class="cache-metric-label">Cache Storage</div>
            <div class="cache-metric-value">{cache_metrics['total_entries']}</div>
            <div class="cache-metric-label">Entries ({size_str})</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

# Cache hit distribution pie chart
cache_fig = go.Figure(data=[
    go.Pie(
        labels=['Exact Hits', 'Semantic Hits', 'Misses'],
        values=[cache_metrics['exact_hits'], cache_metrics['semantic_hits'], cache_metrics['misses']],
        hole=.4,
        marker_colors=['#1e88e5', '#43a047', '#e53935']
    )
])
cache_fig.update_layout(
    title="Cache Hit Distribution",
    height=350
)
st.plotly_chart(cache_fig, use_container_width=True)

# Daily cost trends
st.header("Daily Cost Trends")

# Create a figure with secondary y-axis
fig = go.Figure()

# Add cost bars
fig.add_trace(
    go.Bar(
        x=daily_costs['date'],
        y=daily_costs['cost'],
        name="Cost ($)",
        marker_color='#1e88e5'
    )
)

# Add cache hit rate line on secondary y-axis
fig.add_trace(
    go.Scatter(
        x=daily_costs['date'],
        y=daily_costs['cache_hits'] / daily_costs['calls'],
        name="Cache Hit Rate",
        yaxis="y2",
        line=dict(color='#43a047', width=3)
    )
)

# Update layout with secondary y-axis
fig.update_layout(
    title="Daily Costs and Cache Hit Rate",
    xaxis_title="Date",
    yaxis_title="Cost ($)",
    yaxis2=dict(
        title="Cache Hit Rate",
        titlefont=dict(color='#43a047'),
        tickfont=dict(color='#43a047'),
        anchor="x",
        overlaying="y",
        side="right",
        range=[0, 1]
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    height=400
)

st.plotly_chart(fig, use_container_width=True)

# Model usage breakdown
st.header("Model Usage Breakdown")

# Filter models based on selection
filtered_models = model_costs[model_costs['model'].isin(models_to_show)]

col1, col2 = st.columns(2)

with col1:
    # Pie chart for model cost distribution
    fig = px.pie(
        filtered_models,
        values='cost',
        names='model',
        title="Cost Distribution by Model",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # Bar chart for token usage by model
    fig = px.bar(
        filtered_models,
        x='model',
        y='tokens',
        title="Token Usage by Model",
        color='model',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# Model cost efficiency table
st.subheader("Model Cost Efficiency")

# Calculate cost per 1000 tokens
filtered_models['cost_per_1k_tokens'] = (filtered_models['cost'] / filtered_models['tokens']) * 1000

# Format the table
table_data = filtered_models[['model', 'calls', 'tokens', 'cost', 'cost_per_1k_tokens']]
table_data = table_data.rename(columns={
    'model': 'Model',
    'calls': 'Total Calls',
    'tokens': 'Total Tokens',
    'cost': 'Total Cost ($)',
    'cost_per_1k_tokens': 'Cost per 1K Tokens ($)'
})

# Format numeric columns
table_data['Total Cost ($)'] = table_data['Total Cost ($)'].map('${:.2f}'.format)
table_data['Cost per 1K Tokens ($)'] = table_data['Cost per 1K Tokens ($)'].map('${:.4f}'.format)

st.table(table_data)

# Optimization recommendations
st.header("Optimization Recommendations")

for rec in recommendations:
    st.markdown(
        f"""
        <div class="recommendation {rec['severity']}">
            <strong>{rec['severity'].upper()}:</strong> {rec['message']}
        </div>
        """,
        unsafe_allow_html=True
    )

# System health metrics
st.header("System Health")

# Check if alerts should be sent
if enable_notifications:
    check_and_send_alerts(summary)

# System metrics display
sys_col1, sys_col2, sys_col3, sys_col4 = st.columns(4)

with sys_col1:
    # CPU usage
    cpu_color = "good" if system_metrics["cpu_percent"] < 70 else "warning" if system_metrics["cpu_percent"] < 90 else "critical"
    st.markdown(
        f"""
        <div class="system-metric">
            <div class="system-metric-label">CPU Usage</div>
            <div class="system-metric-value {cpu_color}">{system_metrics["cpu_percent"]:.1f}%</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

with sys_col2:
    # Memory usage
    memory_color = "good" if system_metrics["memory_percent"] < 70 else "warning" if system_metrics["memory_percent"] < 90 else "critical"
    st.markdown(
        f"""
        <div class="system-metric">
            <div class="system-metric-label">Memory Usage</div>
            <div class="system-metric-value {memory_color}">{system_metrics["memory_percent"]:.1f}%</div>
            <div class="system-metric-label">{system_metrics["memory_used_gb"]:.1f} GB / {system_metrics["memory_total_gb"]:.1f} GB</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

with sys_col3:
    # Disk usage
    disk_color = "good" if system_metrics["disk_percent"] < 70 else "warning" if system_metrics["disk_percent"] < 90 else "critical"
    st.markdown(
        f"""
        <div class="system-metric">
            <div class="system-metric-label">Disk Usage</div>
            <div class="system-metric-value {disk_color}">{system_metrics["disk_percent"]:.1f}%</div>
            <div class="system-metric-label">{system_metrics["disk_used_gb"]:.1f} GB / {system_metrics["disk_total_gb"]:.1f} GB</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

with sys_col4:
    # Process memory
    st.markdown(
        f"""
        <div class="system-metric">
            <div class="system-metric-label">Process Resources</div>
            <div class="system-metric-value">{system_metrics["process_memory_mb"]:.1f} MB</div>
            <div class="system-metric-label">Memory Usage</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

# System metrics charts
sys_chart_col1, sys_chart_col2 = st.columns(2)

with sys_chart_col1:
    # CPU and Memory usage gauge chart
    fig = go.Figure()
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=system_metrics["cpu_percent"],
        title={"text": "CPU Usage (%)"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#1e88e5"},
            "steps": [
                {"range": [0, 50], "color": "#e8f5e9"},
                {"range": [50, 80], "color": "#fff9c4"},
                {"range": [80, 100], "color": "#ffebee"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 90
            }
        }
    ))
    
    st.plotly_chart(fig, use_container_width=True)

with sys_chart_col2:
    # Memory usage gauge chart
    fig = go.Figure()
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=system_metrics["memory_percent"],
        title={"text": "Memory Usage (%)"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#43a047"},
            "steps": [
                {"range": [0, 50], "color": "#e8f5e9"},
                {"range": [50, 80], "color": "#fff9c4"},
                {"range": [80, 100], "color": "#ffebee"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 90
            }
        }
    ))
    
    st.plotly_chart(fig, use_container_width=True)

# Cache optimization recommendations
st.header("Cache Optimization Recommendations")

# Current cache settings
st.subheader("Current Cache Settings")
settings_col1, settings_col2, settings_col3 = st.columns(3)

with settings_col1:
    st.metric("Semantic Threshold", f"{cache_optimization['current_settings']['semantic_threshold']:.2f}")

with settings_col2:
    st.metric("TTL (Days)", cache_optimization['current_settings']['ttl_days'])

with settings_col3:
    st.metric("Current Hit Rate", f"{cache_optimization['current_hit_rate']*100:.1f}%")

# Recommendations
st.subheader("Recommended Optimizations")

for rec in cache_optimization['recommendations']:
    st.markdown(
        f"""
        <div class="optimization-tip">
            <strong>Setting: {rec['setting']}</strong><br>
            Current: {rec['current']} → Recommended: {rec['recommended']}<br>
            Reason: {rec['reason']}
        </div>
        """,
        unsafe_allow_html=True
    )

# Footer
st.markdown("---")
st.markdown("Dashboard last updated: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# RAG hint (subtle)
st.markdown(
    """
    <div style="text-align: right; color: #888; font-size: 0.8em;">
    Future enhancement: Retrieval-Augmented Generation (RAG) capabilities
    </div>
    """,
    unsafe_allow_html=True
)

if __name__ == "__main__":
    # This will run when the script is executed directly
    pass