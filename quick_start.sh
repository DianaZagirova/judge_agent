#!/bin/bash
# Quick start script for LLM judge paper processing

set -e

echo "============================================"
echo "LLM Judge - Paper Processing Quick Start"
echo "============================================"
echo ""

# Check if running from correct directory
if [ ! -f "src/process_papers.py" ]; then
    echo "Error: Must run from llm_judge directory"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Please create .env with OPENAI_API_KEY=your_key"
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data

echo "Choose an option:"
echo "1) Test run (5 papers, 2 workers)"
echo "2) Small batch (100 papers, 5 workers)"
echo "3) Medium batch (1000 papers, 10 workers)"
echo "4) View statistics"
echo "5) View recent results (20)"
echo "6) Export to CSV"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        echo "Running test with 5 papers..."
        python src/process_papers.py --test
        ;;
    2)
        echo "Processing 100 papers with 5 workers..."
        python src/process_papers.py --limit 100 --workers 5
        ;;
    3)
        echo "Processing 1000 papers with 10 workers..."
        python src/process_papers.py --limit 1000 --workers 10
        ;;
    4)
        echo "Showing statistics..."
        python src/view_results.py --stats
        ;;
    5)
        echo "Showing recent results..."
        python src/view_results.py --recent 20
        ;;
    6)
        read -p "Enter output filename (e.g., results.csv): " filename
        python src/view_results.py --export "$filename"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Done!"
