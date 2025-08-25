# Makefile for Article Selector

.PHONY: help setup install dev clean format lint test run-api run-cli

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Run complete development setup
	@./scripts/dev_setup.sh

install: ## Install project dependencies with UV
	@uv pip install -e .

dev: ## Install development dependencies
	@uv pip install -e ".[dev]"

clean: ## Clean up generated files
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.pid" -delete
	@echo "✅ Cleanup complete"

format: ## Format code with ruff
	@./scripts/format.sh

lint: ## Run linting and type checking
	@echo "🔍 Running linting..."
	@uv run ruff check .
	@echo "🔬 Running type checking..."
	@uv run mypy .

test: ## Run all tests
	@echo "🧪 Running tests..."
	@uv run pytest tests/ -v

validate: ## Run all validation checks (lint + test)
	@./scripts/validate.sh

run-api: ## Start the FastAPI server
	@echo "🚀 Starting API server..."
	@uv run uvicorn api.main:app --reload

run-cli: ## Run CLI agent selector (usage: make run-cli ARGS="list")
	@uv run python cli/run_agent.py $(ARGS)

# Main launcher commands
run: ## Run article selector with today's articles
	@uv run python run_article_selector.py --db local --start-date $$(date +%Y-%m-%d)

run-motherduck: ## Run article selector with MotherDuck
	@uv run python run_article_selector.py --db motherduck --start-date $$(date +%Y-%m-%d)

run-date: ## Run for specific date (usage: make run-date DATE=2025-08-07)
	@uv run python run_article_selector.py --db local --start-date $(DATE)

run-csv: ## Run with CSV file (usage: make run-csv FILE=data/sample_articles.csv)
	@uv run python run_article_selector.py --csv $(FILE)

run-quick: ## Quick run with wrapper script
	@./scripts/run.sh

first-pass: ## Test first pass agent with sample data
	@echo "🔍 Running first pass agent..."
	@uv run python cli/run_agent.py first_pass -p

scoring: ## Test scoring agent with sample data
	@echo "📊 Running scoring agent..."
	@uv run python cli/run_agent.py scoring -p

list-agents: ## List all available agents
	@uv run python cli/run_agent.py list

sync: ## Sync all dependencies
	@echo "🔄 Syncing dependencies..."
	@uv sync

freeze: ## Generate requirements.txt
	@echo "📝 Generating requirements.txt..."
	@uv pip freeze > requirements.txt
	@echo "✅ requirements.txt updated"

# Database and processing commands
process: ## Process articles from database
	@echo "🔄 Processing articles..."
	@uv run python cli/process_articles.py process

load-csv: ## Load sample articles into database
	@echo "📥 Loading sample articles..."
	@uv run python cli/process_articles.py load data/sample_articles.csv

# Response viewing commands
view-responses: ## View response summary
	@uv run python cli/view_responses.py summary

list-responses: ## List all response files
	@uv run python cli/view_responses.py list

view-latest: ## View latest response file
	@uv run python cli/view_responses.py list -l 1

clean-responses: ## Clean old response files (dry run)
	@uv run python cli/view_responses.py clean

clean-responses-confirm: ## Actually delete old response files
	@uv run python cli/view_responses.py clean --confirm