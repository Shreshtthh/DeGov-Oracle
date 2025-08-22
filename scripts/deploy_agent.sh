#!/bin/bash

echo "🤖 Setting up DeGov Oracle Agent..."

cd agent

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.template .env
    echo "Please edit .env with your configuration"
    exit 1
fi

# Test the agent locally
echo "Testing agent..."
python src/main.py &
AGENT_PID=$!

# Wait a moment for startup
sleep 3

# Kill test process
kill $AGENT_PID

echo "✅ Agent setup complete!"
echo "To run the agent: cd agent && source venv/bin/activate && python src/main.py"