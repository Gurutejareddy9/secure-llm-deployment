#!/usr/bin/env bash
# Environment setup script for secure-llm-deployment
set -euo pipefail

echo "=== Secure LLM Deployment – Environment Setup ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip --quiet

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt --quiet

# Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and set JWT_SECRET and OPENAI_API_KEY before running."
fi

echo ""
echo "✅ Setup complete!"
echo "   Activate venv: source .venv/bin/activate"
echo "   Run dev server: bash scripts/run_dev.sh"
