#!/usr/bin/env python3

"""
dashboard.py

A Streamlit dashboard for real-time monitoring of AI API usage costs.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to allow imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
sys.path.append(str(parent_dir))

import pandas as pd
import streamlit as st
import plotly.express as px
from scripts.ai.cost_tracker import CostTracker

# Set page config
st.set_page_config(
    page_title="AI API Cost Dashboard",
    page_icon="💰",
    layout="wide"
)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = datetime.now()

# Main content
st.title("AI API Cost Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Create mock data for demonstration
def generate_mock_data():
    # Mock summary data
    summary = {
        "today_cost": 15.75,
        "month_cost": 150.50,
        "total_cost": 420.25,
        "total_calls": 250,
        "cache_hit_rate": 0.35,
        "daily_budget": {"limit": 50.0, "used": 15.75, "remaining": 34.25},
        "monthly_budget": {"limit": 500.0, "used": 150.50, "remaining": 349.50},
    }
    
    # Mock daily costs
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(14)]
    costs = [10.50, 12.75, 15.25, 8.50, 9.75, 14.50, 16.25, 15.75, 12.50, 11.75, 13.25, 10.25, 9.50, 8.75]
    calls = [25, 30, 35, 20, 22, 32, 38, 36, 28, 26, 30, 24, 22, 20]
    cache_rate = [0.30, 0.32, 0.35, 0.28, 0.30, 0.34, 0.36, 0.35, 0.32, 0.31, 0.33, 0.29, 0.28, 0.27]
    
    daily_costs = pd.DataFrame({
        "date": dates,
        "total_cost": costs,
        "call_count": calls,
        "cache_hit_rate": cache_rate
    })
    
    # Mock model costs
    models = ["gpt4o_mini", "claude_sonnet", "deepseek_r1"]
    total_costs = [45.25, 75.50, 29.75]
    call_counts = [120, 80, 50]
    prompt_tokens = [12000, 8000, 5000]
    completion_tokens = [6000, 4000, 2500]
    
    model_costs = pd.DataFrame({
        "model_id": models,
        "total_cost": total_costs,
        "call_count": call_counts,
        "total_prompt_tokens": prompt_tokens,
        "total_completion_tokens": completion_tokens,
        "avg_cost_per_call": [total_costs[i]/call_counts[i] for i in range(len(models))]
    })
    
    # Mock recommendations
    recommendations = [
        {
            "type": "cache",
            "severity": "medium",
            "message": "Low cache hit rate (35.0%). Consider improving prompt consistency and semantic caching threshold."
        },
        {
            "type": "model_selection",
            "severity": "high",
            "message": "Found 18 simple tasks using expensive models. Adjust the complexity thresholds or model routing logic."
        }
    ]
    
    return {
        "summary": summary,
        "daily_costs": daily_costs,
        "model_costs": model_costs,
        "recommendations": recommendations
    }

# Get data - either from mock for demo or real data
try:
    # Try to initialize the cost tracker
    tracker = CostTracker()
    # If this is just a demo, use mock data instead
    use_mock_data = True  # Set to False to use real data when available
    
    if use_mock_data:
        data = generate_mock_data()
    else:
        # Get real data
        summary = tracker.get_cost_summary()
        daily_costs = tracker.get_daily_costs(days=30)
        model_costs = tracker.get_model_costs()
        recommendations = tracker.get_optimization_recommendations()
        
        data = {
            "summary": summary,
            "daily_costs": daily_costs,
            "model_costs": model_costs,
            "recommendations": recommendations
        }
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Today's Cost", f"${data['summary']['today_cost']:.2f}")
    
    with col2:
        st.metric("Monthly Cost", f"${data['summary']['month_cost']:.2f}")
    
    with col3:
        st.metric("Budget Remaining", f"${data['summary']['monthly_budget']['remaining']:.2f}")
        monthly_budget = data['summary']['monthly_budget']
        percentage = (monthly_budget['used'] / monthly_budget['limit']) * 100 if monthly_budget['limit'] > 0 else 0
        st.progress(percentage / 100, text=f"{percentage:.1f}% of monthly budget used")
    
    with col4:
        cache_rate = data['summary'].get('cache_hit_rate', 0) * 100
        st.metric("Cache Hit Rate", f"{cache_rate:.1f}%")
    
    # Section: Daily Cost Trends
    st.header("Daily Cost Trends")
    
    if not data["daily_costs"].empty:
        # Daily cost chart
        fig_daily = px.bar(
            data["daily_costs"],
            x="date",
            y="total_cost",
            title="Daily API Costs",
            labels={"date": "Date", "total_cost": "Cost (USD)"}
        )
        st.plotly_chart(fig_daily, use_container_width=True)
    
    # Section: Model Usage Breakdown
    st.header("Model Usage Breakdown")
    
    if not data["model_costs"].empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Model cost pie chart
            fig_pie = px.pie(
                data["model_costs"],
                values="total_cost",
                names="model_id",
                title="Cost Distribution by Model"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Tokens by model
            fig_tokens = px.bar(
                data["model_costs"],
                x="model_id",
                y=["total_prompt_tokens", "total_completion_tokens"],
                title="Token Usage by Model",
                labels={"model_id": "Model", "value": "Tokens", "variable": "Token Type"},
                barmode="stack"
            )
            st.plotly_chart(fig_tokens, use_container_width=True)
    
    # Section: Optimization Recommendations
    st.header("Optimization Recommendations")
    
    if data["recommendations"]:
        for rec in data["recommendations"]:
            if rec['severity'] == 'high':
                st.error(f"**{rec['type'].upper()}**: {rec['message']}")
            elif rec['severity'] == 'medium':
                st.warning(f"**{rec['type'].upper()}**: {rec['message']}")
            else:
                st.info(f"**{rec['type'].upper()}**: {rec['message']}")
    else:
        st.info("No optimization recommendations available.")

except Exception as e:
    st.error(f"Error loading dashboard data: {str(e)}")
    st.info("Using mock data for demonstration. In production, this would use the CostTracker.")
    data = generate_mock_data()

# Sidebar controls
with st.sidebar:
    st.title("Dashboard Controls")
    
    if st.button("Refresh Data"):
        st.success("Data refreshed!")
    
    st.divider()
    
    st.subheader("Export Data")
    export_format = st.selectbox("Format", options=["CSV", "JSON"])
    export_days = st.slider("Days to export", min_value=7, max_value=90, value=30)
    
    if st.button("Export Data"):
        st.success(f"Data would be exported in {export_format} format")
    
    st.divider()
    
    # Future Enhancements Section
    st.subheader("Future Enhancements")
    st.info(
        "Consider integrating the RAG approach for semantic search and automated content enrichment. "
        "See details in docs/RAG_Idea.md"
    )

# Footer
# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0;
    }
    .metric-label {
        font-size: 1rem;
        color: #6c757d;
        margin-top: 0;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #f1f1f1;
        padding-bottom: 0.5rem;
    }
    .recommendation-high {
        background-color: #ffe9e9;
        border-left: 5px solid #ff4d4d;
        padding: 0.8rem;
        margin-bottom: 0.8rem;
    }
    .recommendation-medium {
        background-color: #fff8e1;
        border-left: 5px solid #ffcc00;
        padding: 0.8rem;
        margin-bottom: 0.8rem;
    }
    .recommendation-low {
        background-color: #e6f3ff;
        border-left: 5px solid #4d94ff;
        padding: 0.8rem;
        margin-bottom: 0.8rem;
    }
    .cache-stats {
        display: flex;
        justify-content: space-between;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = datetime.now()
if 'auto_refresh' not in st.session_state:
    st.session_state['auto_refresh'] = False
if 'refresh_interval' not in st.session_state:
    st.session_state['refresh_interval'] = 5  # minutes

# Function to load data
@st.cache_data(ttl=timedelta(minutes=5))
def load_data():
    # Initialize the cost tracker
    tracker = CostTracker()
    
    # Get summary data
    summary = tracker.get_cost_summary()
    
    # Get daily costs for the past 30 days
    daily_costs = tracker.get_daily_costs(days=30)
    
    # Get model costs 
    model_costs = tracker.get_model_costs()
    
    # Get optimization recommendations
    recommendations = tracker.get_optimization_recommendations()
    
    return {
        "summary": summary,
        "daily_costs": daily_costs,
        "model_costs": model_costs,
        "recommendations": recommendations,
        "last_updated": datetime.now()
    }

# Sidebar
with st.sidebar:
    st.title("Dashboard Controls")
    
    # Refresh button
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.session_state['last_refresh'] = datetime.now()
        st.success("Data refreshed successfully!")
    
    # Auto-refresh toggle
    auto_refresh = st.toggle("Auto Refresh", value=st.session_state['auto_refresh'])
    st.session_state['auto_refresh'] = auto_refresh
    
    if auto_refresh:
        refresh_interval = st.slider(
            "Refresh Interval (minutes)", 
            min_value=1, 
            max_value=60, 
            value=st.session_state['refresh_interval']
        )
        st.session_state['refresh_interval'] = refresh_interval
        
        # Auto-refresh logic
        if (datetime.now() - st.session_state['last_refresh']).total_seconds() >= (refresh_interval * 60):
            st.cache_data.clear()
            st.session_state['last_refresh'] = datetime.now()
    
    st.divider()
    
    # Date range filter for charts
    st.subheader("Time Range")
    date_range = st.selectbox(
        "Select period for charts",
        options=["Last 7 days", "Last 14 days", "Last 30 days", "Last 90 days"],
        index=2
    )
    
    # Additional filters
    st.subheader("Filters")
    # These would be populated with actual data from the database
    model_filter = st.multiselect(
        "Filter by Model",
        options=["All", "GPT-4o Mini", "Claude Sonnet", "DeepSeek R1"],
        default="All"
    )
    
    # Export data
    st.subheader("Export Data")
    export_format = st.selectbox("Format", options=["CSV", "JSON"])
    export_days = st.slider("Days to export", min_value=7, max_value=90, value=30)
    
    if st.button("Export Data"):
        tracker = CostTracker()
        export_path = tracker.export_data(format=export_format.lower(), days=export_days)
        if export_path:
            st.success(f"Data exported to: {export_path}")
        else:
            st.error("Failed to export data")

# Main content
st.markdown('<h1 class="main-header">AI API Cost Dashboard</h1>', unsafe_allow_html=True)

# Load data
try:
    data = load_data()
    
    # Last updated info
    st.caption(f"Last updated: {data['last_updated'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Key metrics in a row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <p class="metric-value">$%.2f</p>
            <p class="metric-label">Today's Cost</p>
        </div>
        """ % data["summary"]["today_cost"], unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <p class="metric-value">$%.2f</p>
            <p class="metric-label">Monthly Cost</p>
        </div>
        """ % data["summary"]["month_cost"], unsafe_allow_html=True)
    
    with col3:
        monthly_budget = data["summary"]["monthly_budget"]
        percentage = (monthly_budget["used"] / monthly_budget["limit"]) * 100 if monthly_budget["limit"] > 0 else 0
        
        st.markdown("""
        <div class="metric-card">
            <p class="metric-value">$%.2f</p>
            <p class="metric-label">Budget Remaining</p>
        </div>
        """ % monthly_budget["remaining"], unsafe_allow_html=True)
        
        # Progress bar for budget
        st.progress(percentage / 100, text=f"{percentage:.1f}% of monthly budget used")
    
    with col4:
        cache_rate = data["summary"].get("cache_hit_rate", 0) * 100
        
        st.markdown("""
        <div class="metric-card">
            <p class="metric-value">%.1f%%</p>
            <p class="metric-label">Cache Hit Rate</p>
        </div>
        """ % cache_rate, unsafe_allow_html=True)
    
    # Section: Daily Cost Trends
    st.markdown('<h2 class="section-header">Daily Cost Trends</h2>', unsafe_allow_html=True)
    
    if not data["daily_costs"].empty:
        # Daily cost chart
        fig_daily = px.bar(
            data["daily_costs"],
            x="date",
            y="total_cost",
            title="Daily API Costs",
            labels={"date": "Date", "total_cost": "Cost (USD)"},
            color_discrete_sequence=["#4e79a7"]
        )
        fig_daily.update_layout(height=400)
        st.plotly_chart(fig_daily, use_container_width=True)
        
        # API calls and cache hit rate
        col1, col2 = st.columns(2)
        
        with col1:
            fig_calls = px.line(
                data["daily_costs"],
                x="date",
                y="call_count",
                title="Number of API Calls per Day",
                labels={"date": "Date", "call_count": "Number of Calls"},
                color_discrete_sequence=["#59a14f"]
            )
            fig_calls.update_layout(height=300)
            st.plotly_chart(fig_calls, use_container_width=True)
        
        with col2:
            if 'cache_hit_rate' in data["daily_costs"].columns:
                fig_cache = px.line(
                    data["daily_costs"],
                    x="date",
                    y="cache_hit_rate",
                    title="Daily Cache Hit Rate",
                    labels={"date": "Date", "cache_hit_rate": "Cache Hit Rate"},
                    color_discrete_sequence=["#edc949"]
                )
                fig_cache.update_layout(
                    height=300,
                    yaxis=dict(tickformat=".0%", range=[0, 1])
                )
                st.plotly_chart(fig_cache, use_container_width=True)
    else:
        st.info("No daily cost data available yet. Start making API calls to see trends.")
    
    # Section: Model Usage Breakdown
    st.markdown('<h2 class="section-header">Model Usage Breakdown</h2>', unsafe_allow_html=True)
    
    if not data["model_costs"].empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Model cost pie chart
            fig_pie = px.pie(
                data["model_costs"],
                values="total_cost",
                names="model_id",
                title="Cost Distribution by Model",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Tokens by model
            fig_tokens = px.bar(
                data["model_costs"],
                x="model_id",
                y=["total_prompt_tokens", "total_completion_tokens"],
                title="Token Usage by Model",
                labels={
                    "model_id": "Model",
                    "value": "Tokens",
                    "variable": "Token Type"
                },
                barmode="stack",
                color_discrete_map={
                    "total_prompt_tokens": "#5470c6",
                    "total_completion_tokens": "#91cc75"
                }
            )
            fig_tokens.update_layout(height=350)
            st.plotly_chart(fig_tokens, use_container_width=True)
        
        # Model cost efficiency table
        st.subheader("Model Cost Efficiency")
        
        # Add calculated metrics for display
        display_df = data["model_costs"].copy()
        display_df["total_tokens"] = display_df["total_prompt_tokens"] + display_df["total_completion_tokens"]
        display_df["cost_per_1k_tokens"] = (display_df["total_cost"] * 1000 / display_df["total_tokens"]).round(4)
        display_df["avg_cost_per_call"] = display_df["avg_cost_per_call"].round(4)
        
        # Reorder and rename columns for display
        display_cols = [
            "model_id", "call_count", "total_cost", "avg_cost_per_call", 
            "total_tokens", "cost_per_1k_tokens"
        ]
        display_df = display_df[display_cols].rename(columns={
            "model_id": "Model",
            "call_count": "API Calls",
            "total_cost": "Total Cost ($)",
            "avg_cost_per_call": "Avg Cost per Call ($)",
            "total_tokens": "Total Tokens",
            "cost_per_1k_tokens": "$ per 1K Tokens"
        })
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No model usage data available yet. Start making API calls to see model breakdown.")
    
    # Section: Optimization Recommendations
    st.markdown('<h2 class="section-header">Optimization Recommendations</h2>', unsafe_allow_html=True)
    
    if data["recommendations"]:
        for rec in data["recommendations"]:
            severity_class = f"recommendation-{rec['severity']}"
            st.markdown(f"""
            <div class="{severity_class}">
                <strong>{rec['type'].upper()}</strong>: {rec['message']}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No optimization recommendations available.")

except Exception as e:
    st.error(f"Error loading dashboard data: {str(e)}")
    st.info("Please make sure the database is set up and has data. Try running the cost tracker script first.")

# Footer
st.markdown("---")
st.caption("AI API Cost Dashboard • GDPR Compliant • Built with Streamlit")