#!/bin/bash
# Format code with ruff

set -e

echo "🎨 Formatting code with ruff..."

# Format all Python files
uv run ruff format .

# Fix auto-fixable issues
uv run ruff check --fix .

echo "✅ Code formatting complete!"