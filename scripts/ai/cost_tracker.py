#!/usr/bin/env python3

"""
cost_tracker.py

Tracks and monitors AI API usage costs, providing real-time statistics,
budget alerts, and cost optimization recommendations.
"""

import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent.parent / "logs" / "cost_tracker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cost_tracker")

# Database setup
DB_PATH = Path(__file__).parent.parent.parent / "data" / "ai_costs.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Default budget settings
DEFAULT_BUDGET = {
    "daily_limit": 10.0,      # $10 per day
    "monthly_limit": 100.0,   # $100 per month
    "alert_threshold": 0.8,   # Alert at 80% of budget
}

# Define notification channels
NOTIFICATIONS = {
    "enabled": True,
    "slack_webhook": os.environ.get("SLACK_WEBHOOK_URL", ""),
    "email": os.environ.get("ALERT_EMAIL", ""),
    "log_alerts": True
}

class CostTracker:
    """
    Tracks and analyzes AI API usage costs.
    """
    
    def __init__(self, budget: Optional[Dict[str, float]] = None):
        """
        Initialize the cost tracker.
        
        Args:
            budget (dict, optional): Budget settings to override defaults
        """
        self.budget = DEFAULT_BUDGET.copy()
        if budget:
            self.budget.update(budget)
        
        self._setup_database()
    
    def _setup_database(self) -> None:
        """
        Create the database tables if they don't exist.
        """
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Create tables if they don't exist
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
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON api_calls(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_model ON api_calls(model_id)')
        
        conn.commit()
        conn.close()
        
        logger.info("Database setup complete")
    
    def record_api_call(self, model_id: str, prompt_tokens: int, completion_tokens: int,
                      cost: float, cached: bool = False, complexity_score: float = 0.0,
                      request_type: str = "completion", request_id: Optional[str] = None) -> None:
        """
        Record an API call in the database.
        
        Args:
            model_id (str): ID of the model used
            prompt_tokens (int): Number of input tokens
            completion_tokens (int): Number of output tokens
            cost (float): Cost of the API call in USD
            cached (bool): Whether the result was cached
            complexity_score (float): Complexity score of the request
            request_type (str): Type of request (completion, embedding, etc.)
            request_id (str, optional): Unique ID for the request
        """
        timestamp = datetime.now().isoformat()
        
        # Generate a unique request ID if not provided
        if not request_id:
            request_id = f"{model_id}_{int(datetime.now().timestamp())}_{prompt_tokens}"
        
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            # Insert the API call record
            cursor.execute('''
            INSERT INTO api_calls (timestamp, model_id, prompt_tokens, completion_tokens, 
                                 cost, cached, complexity_score, request_type, request_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, model_id, prompt_tokens, completion_tokens, 
                cost, cached, complexity_score, request_type, request_id))
            
            # Update daily budget
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
            INSERT INTO daily_budgets (date, budget_limit, budget_used)
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
            budget_used = budget_used + ?
            ''', (today, self.budget['daily_limit'], cost, cost))
            
            # Update monthly budget
            current_month = datetime.now().strftime('%Y-%m')
            cursor.execute('''
            INSERT INTO monthly_budgets (month, budget_limit, budget_used)
            VALUES (?, ?, ?)
            ON CONFLICT(month) DO UPDATE SET
            budget_used = budget_used + ?
            ''', (current_month, self.budget['monthly_limit'], cost, cost))
            
            conn.commit()
            
            # Check budget alerts
            self._check_budget_alerts(cursor)
            
            conn.close()
            
            logger.info(f"Recorded API call: {model_id}, cost: ${cost:.4f}, tokens: {prompt_tokens}+{completion_tokens}")
        except Exception as e:
            logger.error(f"Error recording API call: {str(e)}")
    
    def _check_budget_alerts(self, cursor) -> None:
        """
        Check if budget thresholds have been exceeded and send alerts.
        
        Args:
            cursor: SQLite cursor
        """
        # Check daily budget
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT budget_limit, budget_used, alert_sent FROM daily_budgets WHERE date = ?', (today,))
        daily_row = cursor.fetchone()
        
        if daily_row:
            daily_limit, daily_used, alert_sent = daily_row
            daily_percentage = daily_used / daily_limit if daily_limit > 0 else 0
            
            if daily_percentage >= self.budget['alert_threshold'] and not alert_sent:
                self._send_alert(f"Daily budget alert: ${daily_used:.2f}/${daily_limit:.2f} ({daily_percentage:.1%})")
                cursor.execute('UPDATE daily_budgets SET alert_sent = 1 WHERE date = ?', (today,))
        
        # Check monthly budget
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute('SELECT budget_limit, budget_used, alert_sent FROM monthly_budgets WHERE month = ?', (current_month,))
        monthly_row = cursor.fetchone()
        
        if monthly_row:
            monthly_limit, monthly_used, alert_sent = monthly_row
            monthly_percentage = monthly_used / monthly_limit if monthly_limit > 0 else 0
            
            if monthly_percentage >= self.budget['alert_threshold'] and not alert_sent:
                self._send_alert(f"Monthly budget alert: ${monthly_used:.2f}/${monthly_limit:.2f} ({monthly_percentage:.1%})")
                cursor.execute('UPDATE monthly_budgets SET alert_sent = 1 WHERE month = ?', (current_month,))
    
    def _send_alert(self, message: str) -> None:
        """
        Send an alert through configured channels.
        
        Args:
            message (str): Alert message
        """
        if not NOTIFICATIONS["enabled"]:
            return
        
        # Always log alerts
        logger.warning(f"BUDGET ALERT: {message}")
        
        # TODO: Implement actual notification methods (Slack, email, etc.)
        # This would involve calling external APIs or services
    
    def get_daily_costs(self, days: int = 7) -> pd.DataFrame:
        """
        Get daily cost data for the specified number of days.
        
        Args:
            days (int): Number of days to retrieve
            
        Returns:
            DataFrame: Daily cost data
        """
        try:
            conn = sqlite3.connect(str(DB_PATH))
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Query for daily aggregated costs
            query = f'''
            SELECT 
                date(timestamp) as date,
                sum(cost) as total_cost,
                count(*) as call_count,
                avg(cost) as avg_cost,
                sum(CASE WHEN cached = 1 THEN 1 ELSE 0 END) as cached_count
            FROM api_calls
            WHERE timestamp >= ?
            GROUP BY date(timestamp)
            ORDER BY date(timestamp)
            '''
            
            df = pd.read_sql_query(query, conn, params=(start_date.isoformat(),))
            conn.close()
            
            # Calculate cache hit rate
            if 'call_count' in df.columns and 'cached_count' in df.columns and not df.empty:
                df['cache_hit_rate'] = df['cached_count'] / df['call_count']
            
            return df
        except Exception as e:
            logger.error(f"Error getting daily costs: {str(e)}")
            return pd.DataFrame()
    
    def get_model_costs(self, days: int = 30) -> pd.DataFrame:
        """
        Get cost data aggregated by model for the specified number of days.
        
        Args:
            days (int): Number of days to retrieve
            
        Returns:
            DataFrame: Model cost data
        """
        try:
            conn = sqlite3.connect(str(DB_PATH))
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Query for model aggregated costs
            query = f'''
            SELECT 
                model_id,
                sum(cost) as total_cost,
                count(*) as call_count,
                avg(cost) as avg_cost_per_call,
                sum(prompt_tokens) as total_prompt_tokens,
                sum(completion_tokens) as total_completion_tokens
            FROM api_calls
            WHERE timestamp >= ?
            GROUP BY model_id
            ORDER BY total_cost DESC
            '''
            
            df = pd.read_sql_query(query, conn, params=(start_date.isoformat(),))
            conn.close()
            
            # Calculate cost per 1K tokens
            if not df.empty:
                df['total_tokens'] = df['total_prompt_tokens'] + df['total_completion_tokens']
                df['cost_per_1k_tokens'] = df['total_cost'] * 1000 / df['total_tokens'].replace(0, np.nan)
            
            return df
        except Exception as e:
            logger.error(f"Error getting model costs: {str(e)}")
            return pd.DataFrame()
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current cost metrics.
        
        Returns:
            dict: Cost summary data
        """
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            # Get today's costs
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
            SELECT SUM(cost) FROM api_calls 
            WHERE date(timestamp) = ?
            ''', (today,))
            today_cost = cursor.fetchone()[0] or 0
            
            # Get current month costs
            current_month = datetime.now().strftime('%Y-%m')
            month_start = f"{current_month}-01"
            cursor.execute('''
            SELECT SUM(cost) FROM api_calls 
            WHERE date(timestamp) >= ?
            ''', (month_start,))
            month_cost = cursor.fetchone()[0] or 0
            
            # Get total all-time cost
            cursor.execute('SELECT SUM(cost) FROM api_calls')
            total_cost = cursor.fetchone()[0] or 0
            
            # Get call count statistics
            cursor.execute('SELECT COUNT(*) FROM api_calls')
            total_calls = cursor.fetchone()[0] or 0
            
            cursor.execute('''
            SELECT COUNT(*) FROM api_calls 
            WHERE cached = 1
            ''')
            cached_calls = cursor.fetchone()[0] or 0
            
            cache_hit_rate = cached_calls / total_calls if total_calls > 0 else 0
            
            # Get budget information
            cursor.execute('''
            SELECT budget_limit, budget_used FROM daily_budgets
            WHERE date = ?
            ''', (today,))
            daily_budget_row = cursor.fetchone()
            daily_budget = {"limit": self.budget["daily_limit"], "used": 0, "remaining": self.budget["daily_limit"]}
            
            if daily_budget_row:
                daily_budget["limit"] = daily_budget_row[0]
                daily_budget["used"] = daily_budget_row[1]
                daily_budget["remaining"] = daily_budget["limit"] - daily_budget["used"]
            
            cursor.execute('''
            SELECT budget_limit, budget_used FROM monthly_budgets
            WHERE month = ?
            ''', (current_month,))
            monthly_budget_row = cursor.fetchone()
            monthly_budget = {"limit": self.budget["monthly_limit"], "used": 0, "remaining": self.budget["monthly_limit"]}
            
            if monthly_budget_row:
                monthly_budget["limit"] = monthly_budget_row[0]
                monthly_budget["used"] = monthly_budget_row[1]
                monthly_budget["remaining"] = monthly_budget["limit"] - monthly_budget["used"]
            
            conn.close()
            
            return {
                "today_cost": today_cost,
                "month_cost": month_cost,
                "total_cost": total_cost,
                "total_calls": total_calls,
                "cache_hit_rate": cache_hit_rate,
                "daily_budget": daily_budget,
                "monthly_budget": monthly_budget,
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting cost summary: {str(e)}")
            return {
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }
    
    def get_optimization_recommendations(self) -> List[Dict[str, str]]:
        """
        Analyze usage patterns and provide cost optimization recommendations.
        
        Returns:
            list: Optimization recommendations
        """
        recommendations = []
        
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            # Check cache hit rate
            cursor.execute('''
            SELECT COUNT(*) as total,
                  SUM(CASE WHEN cached = 1 THEN 1 ELSE 0 END) as cached
            FROM api_calls
            WHERE timestamp >= datetime('now', '-30 day')
            ''')
            row = cursor.fetchone()
            if row and row[0] > 0:
                cache_hit_rate = row[1] / row[0]
                if cache_hit_rate < 0.2:  # Less than 20% cache hit rate
                    recommendations.append({
                        "type": "cache",
                        "severity": "high" if cache_hit_rate < 0.1 else "medium",
                        "message": f"Low cache hit rate ({cache_hit_rate:.1%}). Consider improving prompt consistency and semantic caching threshold."
                    })
            
            # Check for expensive models usage on simple tasks
            cursor.execute('''
            SELECT COUNT(*) FROM api_calls
            WHERE model_id IN ('claude_sonnet', 'deepseek_r1')
              AND complexity_score < 30
              AND timestamp >= datetime('now', '-30 day')
            ''')
            simple_on_complex = cursor.fetchone()[0] or 0
            
            if simple_on_complex > 10:
                recommendations.append({
                    "type": "model_selection",
                    "severity": "high",
                    "message": f"Found {simple_on_complex} simple tasks using expensive models. Adjust the complexity thresholds or model routing logic."
                })
            
            # Check for potential token wastage
            cursor.execute('''
            SELECT AVG(prompt_tokens) as avg_prompt_tokens
            FROM api_calls
            WHERE timestamp >= datetime('now', '-30 day')
            ''')
            avg_prompt_tokens = cursor.fetchone()[0] or 0
            
            if avg_prompt_tokens > 1000:  # More than 1K tokens on average
                recommendations.append({
                    "type": "tokens",
                    "severity": "medium",
                    "message": f"High average prompt size ({avg_prompt_tokens:.0f} tokens). Consider prompt compression or better context filtering."
                })
            
            conn.close()
            
            # Add general recommendations if list is empty
            if not recommendations:
                recommendations.append({
                    "type": "general",
                    "severity": "low",
                    "message": "No specific optimization opportunities identified. Continue monitoring usage patterns."
                })
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            recommendations.append({
                "type": "error",
                "severity": "low",
                "message": f"Error analyzing optimization opportunities: {str(e)}"
            })
        
        return recommendations

    def export_data(self, format: str = "csv", days: int = 30) -> Optional[str]:
        """
        Export cost data to a file.
        
        Args:
            format (str): Export format ("csv" or "json")
            days (int): Number of days of data to export
            
        Returns:
            str: Path to the exported file
        """
        try:
            # Get the data
            conn = sqlite3.connect(str(DB_PATH))
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Query for detailed data
            query = f'''
            SELECT 
                timestamp, model_id, prompt_tokens, completion_tokens,
                cost, cached, complexity_score, request_type
            FROM api_calls
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            '''
            
            df = pd.read_sql_query(query, conn, params=(start_date.isoformat(),))
            conn.close()
            
            # Create export directory
            export_dir = Path(__file__).parent.parent.parent / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.lower() == "csv":
                export_path = export_dir / f"ai_costs_{timestamp}.csv"
                df.to_csv(export_path, index=False)
            elif format.lower() == "json":
                export_path = export_dir / f"ai_costs_{timestamp}.json"
                df.to_json(export_path, orient="records", indent=2)
            else:
                logger.error(f"Unsupported export format: {format}")
                return None
            
            logger.info(f"Exported data to {export_path}")
            return str(export_path)
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return None

# Example usage
if __name__ == "__main__":
    # Create a cost tracker instance
    tracker = CostTracker({
        "daily_limit": 20.0,      # $20 per day
        "monthly_limit": 200.0,   # $200 per month
        "alert_threshold": 0.7    # Alert at 70% of budget
    })
    
    # Record some example API calls
    for i in range(5):
        # Simulate different models and costs
        model = "gpt4o_mini" if i % 3 == 0 else ("claude_sonnet" if i % 3 == 1 else "deepseek_r1")
        prompt_tokens = 100 + (i * 20)
        completion_tokens = 50 + (i * 10)
        cost = 0.01 * (i + 1)
        complexity = 20 + (i * 10)
        
        tracker.record_api_call(
            model_id=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
            complexity_score=complexity,
            cached=(i == 3)  # One of them is cached
        )
    
    # Get and print cost summary
    summary = tracker.get_cost_summary()
    print("\nCost Summary:")
    print(f"Today's cost: ${summary['today_cost']:.2f}")
    print(f"Month's cost: ${summary['month_cost']:.2f}")
    print(f"Total cost: ${summary['total_cost']:.2f}")
    print(f"Cache hit rate: {summary['cache_hit_rate']:.1%}")
    
    # Get optimization recommendations
    recommendations = tracker.get_optimization_recommendations()
    print("\nOptimization Recommendations:")
    for rec in recommendations:
        print(f"[{rec['severity'].upper()}] {rec['message']}") 