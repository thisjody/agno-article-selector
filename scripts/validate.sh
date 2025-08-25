#!/bin/bash
# Run code validation checks

set -e

echo "🔍 Running code validation..."

# Run ruff linting
echo "📝 Running ruff linter..."
uv run ruff check .

# Run mypy type checking
echo "🔬 Running mypy type checker..."
uv run mypy .

# Run tests if they exist
if [ -d "tests" ]; then
    echo "🧪 Running tests..."
    uv run pytest tests/
else
    echo "⚠️  No tests directory found, skipping tests"
fi

echo "✅ All validation checks passed!"