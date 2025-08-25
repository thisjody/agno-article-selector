#!/bin/bash
# Development setup script for Article Selector

set -e

echo "🚀 Setting up Article Selector development environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing UV package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ UV installed successfully"
else
    echo "✅ UV is already installed"
fi

# Create virtual environment
echo "🔧 Creating virtual environment..."
uv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📚 Installing project dependencies..."
uv pip install -e .

# Install development dependencies
echo "🛠️  Installing development dependencies..."
uv pip install -e ".[dev]"

# Sync dependencies
echo "🔄 Syncing dependencies..."
uv sync

echo "✨ Development environment setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the CLI:"
echo "  uv run python cli/run_agent.py list"
echo ""
echo "To start the API server:"
echo "  uv run uvicorn api.main:app --reload"