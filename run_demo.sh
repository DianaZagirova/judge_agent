#!/bin/bash

# 🧬 Aging Theory Paper Filter - Demo Runner Script
# This script sets up the environment and runs the demo

echo "🧬 Aging Theory Paper Filter - Demo Setup"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/pyvenv.cfg" ] || [ ! -d "venv/lib" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
USE_MODULE=openai

# Processing Configuration
MAX_WORKERS=10
CHECKPOINT_INTERVAL=50
EOF
    echo "📝 Created .env template. Please add your OpenAI API key!"
    echo "   Edit .env file and add your OPENAI_API_KEY"
    exit 1
fi

# Check if API key is set
if grep -q "your_openai_api_key_here" .env; then
    echo "⚠️  Please set your OpenAI API key in the .env file"
    echo "   Edit .env and replace 'your_openai_api_key_here' with your actual API key"
    exit 1
fi

echo "✅ Environment setup complete!"
echo ""

# Run the demo
echo "🚀 Starting the demo..."
echo "=========================="

# Run with different options based on arguments
if [ "$1" = "--quick" ]; then
    echo "⚡ Quick demo mode (3 papers)"
    python demo_aging_filter.py --limit 3
elif [ "$1" = "--verbose" ]; then
    echo "🔍 Verbose demo mode (5 papers)"
    python demo_aging_filter.py --limit 5 --verbose --save-results
elif [ "$1" = "--test" ]; then
    echo "🧪 Test mode (2 papers)"
    python demo_aging_filter.py --limit 2 --quiet
else
    echo "📊 Standard demo mode (5 papers)"
    python demo_aging_filter.py --limit 5 --save-results
fi

echo ""
echo "🎉 Demo completed!"
echo "📊 Check the results above and any generated files"
