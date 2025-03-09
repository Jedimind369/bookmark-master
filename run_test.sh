#!/bin/bash
# Script to run the optimized pipeline test

# Set up virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements-optimized.txt

# Run the test
echo "Running test..."
python scripts/test_optimized_pipeline.py --num-urls 5 --max-workers 2 --compare-original

# Deactivate virtual environment
deactivate

echo "Test completed. Check logs and plots in data/plots directory." 