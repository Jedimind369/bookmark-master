"""
config.py

Konfiguration für das API-Monitoring-System.
Diese Datei enthält alle konfigurierbaren Parameter für die API-Kostenüberwachung.
"""

import os
from pathlib import Path

# Basis-Verzeichnisse
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Projektwurzel
DATA_DIR = Path(BASE_DIR, "data")
MONITORING_DATA_DIR = Path(DATA_DIR, "monitoring")
LOG_DIR = Path(BASE_DIR, "logs")

# Stellen Sie sicher, dass die Verzeichnisse existieren
DATA_DIR.mkdir(exist_ok=True)
MONITORING_DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Dateinamen
USAGE_FILE = Path(MONITORING_DATA_DIR, "api_usage.json")
LOG_FILE = Path(LOG_DIR, "api_monitoring.log")

# Budget-Einstellungen (in USD)
DEFAULT_BUDGET = float(os.environ.get("API_BUDGET_LIMIT", "20.0"))
WARNING_THRESHOLDS = [0.5, 0.75, 0.9]  # Bei 50%, 75% und 90% des Budgets

# Slack-Integration (optional)
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#api-budget-alerts")
SLACK_ENABLED = bool(SLACK_WEBHOOK_URL)

# Helicone-Integration (für detaillierte API-Nutzungsstatistik)
HELICONE_API_KEY = os.environ.get("HELICONE_API_KEY", "")
HELICONE_ENABLED = bool(HELICONE_API_KEY)

# OpenAI-Konfiguration für direkte Abfrage der Nutzungsstatistik
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_ORG_ID = os.environ.get("OPENAI_ORG_ID", "")

# Monitoring-Intervall in Sekunden
MONITORING_INTERVAL = int(os.environ.get("API_MONITORING_INTERVAL", "1800"))  # Standard: 30 Minuten

# Kosten pro Modell (in USD pro 1M Tokens)
MODEL_COSTS = {
    "qwq": {
        "input": 0.25,
        "output": 0.75,
        "description": "QwQ (Llama 3 70B)"
    },
    "claude_sonnet": {
        "input": 3.00,
        "output": 15.00,
        "description": "Claude 3.7 Sonnet"
    },
    "deepseek_r1": {
        "input": 0.50,
        "output": 1.50,
        "description": "DeepSeek R1"
    },
    "gpt4o_mini": {
        "input": 0.15,
        "output": 0.60,
        "description": "GPT-4o Mini"
    }
} 