#!/usr/bin/env python3
"""
Script to update the CI pipeline workflow file.
"""

import os
from pathlib import Path

# Ensure the workflow directory exists
os.makedirs(".github/workflows", exist_ok=True)

# The content of the CI pipeline workflow
workflow_content = """name: API Monitoring CI

on:
  push:
    branches: [ main, develop, 'features/**' ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test-monitoring:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0  # Vollständige Git-History für korrekte Tests
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
        pip install pytest pytest-asyncio
    
    - name: Install monitoring dependencies
      run: |
        pip install streamlit pandas plotly altair matplotlib
    
    - name: Configure Git
      run: |
        git config --global user.name "GitHub Actions"
        git config --global user.email "actions@github.com"
    
    - name: Create data directories
      run: |
        mkdir -p data/monitoring/backups
    
    - name: Run backup functionality tests
      run: |
        python -m scripts.monitoring.test_monitoring --backup --days 3
    
    - name: Run GitHub sync tests
      run: |
        python -m scripts.monitoring.test_github_sync --no-backup
    
    - name: Check backup files integrity
      run: |
        # Prüft, ob generierte Backup-Dateien vorhanden sind
        if [ -z "$(ls -A data/monitoring/backups)" ]; then
          echo "Keine Backup-Dateien gefunden!"
          exit 1
        else
          echo "Backup-Dateien erfolgreich erstellt"
          ls -la data/monitoring/backups
        fi
    
    - name: Validate monitoring data structure
      run: |
        # Prüft, ob die Nutzungsdatei korrekt erzeugt wurde
        if [ ! -f "data/monitoring/api_usage.json" ]; then
          echo "API-Nutzungsdatei nicht gefunden!"
          exit 1
        else
          echo "API-Nutzungsdatei erfolgreich erstellt"
          cat data/monitoring/api_usage.json
        fi
    
    - name: Push test backup to artifacts
      uses: actions/upload-artifact@v3
      with:
        name: monitoring-backups
        path: data/monitoring/backups/
        retention-days: 7
"""

# Write the workflow content to the file
with open(".github/workflows/ci_pipeline.yml", "w") as file:
    file.write(workflow_content)

print("CI pipeline workflow updated successfully!") 