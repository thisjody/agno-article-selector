# Article Selector - Agno Version

An AI-powered article selection system for open source security newsletters, built with the Agno framework. This project converts the original Google ADK implementation to use Agno patterns and best practices.

> **Package Management**: This project uses [UV](https://github.com/astral-sh/uv) for fast, reliable Python package management.

## Quick Start

```bash
# Setup (one-time)
./scripts/dev_setup.sh
cp .env.example .env
# Edit .env with your credentials

# Run article selector (like ADK version)
python run_article_selector.py --db local --start-date 2025-08-07
python run_article_selector.py --db motherduck --start-date 2025-08-07
python run_article_selector.py --csv data/sample_articles.csv

# Or use the convenient wrapper
./scripts/run.sh --date 2025-08-07 --max 5
```

## Overview

The Article Selector uses a multi-agent pipeline to intelligently filter, score, and select the most relevant articles for an open source security newsletter. It employs three specialized agents working in sequence:

1. **First Pass Agent** - Filters articles based on strict open source security relevance criteria
2. **Scoring Agent** - Evaluates filtered articles on quality, impact, and relevance (0-10 scale)
3. **Selector Agent** - Selects and ranks the best articles for the final newsletter

## Project Structure

```
article_selector/
├── api/                      # FastAPI application
│   └── main.py              # API endpoints and app configuration
├── cli/                      # Command-line tools
│   └── run_agent.py         # CLI for testing agents
├── core/                     # Shared infrastructure
│   ├── agents/              # Agent registry and base classes
│   └── workflows/           # Workflow registry
├── projects/
│   └── article_selector/    # Main project
│       ├── agents/          # Three specialized agents
│       │   ├── first_pass_agent.py
│       │   ├── scoring_agent.py
│       │   ├── selector_agent.py
│       │   └── sample-inputs/       # Test data
│       ├── config/          # Domain configuration
│       │   └── domain_config.py    # Trusted/untrusted domains
│       ├── models/          # Pydantic models
│       │   └── article_models.py   # Data structures
│       └── workflows/       # Multi-agent orchestration
│           └── article_selection_workflow.py
└── requirements.txt         # Python dependencies
```

## Features

### Formatted Terminal Output
- **Selection Results Display**: Beautiful terminal output showing selected articles with rankings
- **Processing Statistics**: Real-time statistics for each phase (like ADK version)
- **Article Details**: Shows title, domain, URL, score, and selection reasoning
- **Summary Reports**: Processing time, throughput, and success rates

### Intelligent Filtering
- Strict open source security relevance criteria
- Domain credibility assessment (preferred, caution, vendor domains)
- Automatic exclusion of proprietary software news without OSS impact
- Detection of generic news already covered in mainstream media

### Multi-Dimensional Scoring
- **Relevance Score**: Direct relation to open source security (0-10)
- **Quality Score**: Journalistic and technical quality assessment (0-10)
- **Impact Score**: Potential impact on the OSS community (0-10)
- **Overall Score**: Weighted average for final ranking

### Smart Selection
- Balanced newsletter composition
- Diversity enforcement (avoids redundant coverage)
- Configurable selection limits
- Ranking with clear rationale

## Installation

### Prerequisites

- Python 3.12 or higher
- [UV package manager](https://github.com/astral-sh/uv) (will be installed automatically if not present)

### Quick Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd prodbox
```

2. Run the development setup script:
```bash
./scripts/dev_setup.sh
```

This script will:
- Install UV if not already installed
- Create a virtual environment
- Install all project dependencies
- Install development tools

3. Create your environment configuration:
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. Activate the virtual environment:
```bash
source .venv/bin/activate
```

5. Configure your credentials in `.env`:
   - **For Claude (AWS Bedrock)**: Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - **For MotherDuck** (optional): Set `MOTHERDUCK_TOKEN` and `MOTHERDUCK_DATABASE`
   - **For local DuckDB**: Articles will be stored in `data/test_articles.duckdb` by default

### Manual Setup with UV

If you prefer manual setup:

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Install dependencies
uv pip install -e .
uv pip install -e ".[dev]"  # For development dependencies

# Sync all dependencies
uv sync
```

## Usage

### Main Launch Commands (Like ADK Version)

The Agno version can be launched with similar commands to the ADK version:

```bash
# Process articles from local DuckDB for a specific date
python run_article_selector.py --db local --start-date 2025-08-07

# Process articles from MotherDuck for a date range  
python run_article_selector.py --db motherduck --start-date 2025-08-01 --end-date 2025-08-07

# Process with custom settings
python run_article_selector.py --db local --start-date 2025-08-07 --max-articles 5 --debug

# Process from CSV file
python run_article_selector.py --csv data/sample_articles.csv

# Use convenient Makefile commands
make run                        # Today's articles from local DB
make run-motherduck            # Today's articles from MotherDuck
make run-date DATE=2025-08-07 # Specific date
make run-csv FILE=data/test.csv # From CSV file
```

### Command-Line Options

```
--db {local,motherduck}    Database source to use
--csv FILE                 CSV file to load articles from
--start-date YYYY-MM-DD    Start date for article selection
--end-date YYYY-MM-DD      End date (optional, defaults to start-date)
--max-articles N           Maximum articles to select (default: 10)
--batch-size N             Maximum articles to process (default: 100)
--debug                    Enable debug mode
--no-save                  Don't save agent responses
--no-export                Don't export results to JSON
--model {claude,gemini,openai}  LLM model to use
```

### Database Operations

Load articles from CSV and process them:

```bash
# Load sample articles into database
uv run python cli/process_articles.py load data/sample_articles.csv
# Or use: make load-csv

# Process articles from database (with formatted output)
uv run python cli/process_articles.py process
# Or use: make process

# Run demo workflow to see formatted output
uv run python demo_workflow.py

# Process with custom settings
uv run python cli/process_articles.py process --batch-size 20 --max-selected 5

# Process with debug output
uv run python cli/process_articles.py process --debug
```

### Response Tracking

The system automatically saves all agent inputs and outputs to JSON files in `output/responses/`:

```bash
# View summary of all saved responses
uv run python cli/view_responses.py summary
# Or use: make view-responses

# List response files
uv run python cli/view_responses.py list
uv run python cli/view_responses.py list --agent first_pass
uv run python cli/view_responses.py list --article-id 123

# View a specific response file
uv run python cli/view_responses.py view first_pass_article_1_20240820_143022.json

# Compare two response files
uv run python cli/view_responses.py compare file1.json file2.json

# Clean old response files (older than 7 days)
uv run python cli/view_responses.py clean          # Dry run
uv run python cli/view_responses.py clean --confirm # Actually delete
```

Response files are organized by agent type:
- `output/responses/first_pass/` - First pass filtering results
- `output/responses/scoring/` - Article scoring results  
- `output/responses/selector/` - Final selection results
- `output/responses/comparative_ranker/` - Global rankings

Each interaction saves:
- Input data sent to the agent
- Output received from the agent
- Metadata (timestamps, article IDs, etc.)
- Sanity check input files (plain text format)

### Command Line Interface

Test individual agents using UV:

```bash
# List available agents
uv run python cli/run_agent.py list

# Run first pass filter with sample data
uv run python cli/run_agent.py first_pass

# Run with custom JSON file
uv run python cli/run_agent.py first_pass -f my_article.json

# Run with inline JSON
uv run python cli/run_agent.py first_pass -d '{"title": "Linux Security Update", "content": "..."}'

# Enable debug mode
uv run python cli/run_agent.py first_pass --debug

# Pretty print output
uv run python cli/run_agent.py scoring -p
```

### API Server

Start the FastAPI server with UV:

```bash
# Development mode with auto-reload
uv run uvicorn api.main:app --reload

# Production mode
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Access the API:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- List Agents: http://localhost:8000/agents
- List Workflows: http://localhost:8000/workflows

### Sample Input Format

For the first pass agent:
```json
{
  "title": "Critical Vulnerability Found in OpenSSL 3.0",
  "content": "A critical vulnerability has been discovered...",
  "url": "https://www.openssl.org/news/",
  "domain": "openssl.org",
  "published_date": "2024-08-15T10:00:00Z",
  "author": "OpenSSL Security Team",
  "tags": ["vulnerability", "openssl", "security"]
}
```

For the scoring agent:
```json
{
  "article": {
    "title": "New Linux Kernel Exploit Discovered",
    "content": "Security researchers have uncovered...",
    "domain": "kernel.org"
  },
  "first_pass_reasoning": "Directly affects open source Linux security..."
}
```

## Configuration

### Database Configuration

The system supports both local DuckDB and cloud-based MotherDuck:

#### Local DuckDB (Default)
- Articles stored in `data/test_articles.duckdb`
- No additional configuration required
- Perfect for development and testing

#### MotherDuck (Cloud DuckDB)
- Set `MOTHERDUCK_TOKEN` in `.env` file
- Set `MOTHERDUCK_DATABASE` for your database name
- Enables cloud storage and sharing of article data
- Ideal for production and team collaboration

The system automatically detects which database to use based on the presence of `MOTHERDUCK_TOKEN`.

### Domain Configuration

The system uses domain-based credibility assessment defined in `projects/article_selector/config/domain_config.py`:

- **Preferred Domains**: High credibility security news sources
- **Project/Vendor Domains**: Authoritative but not primary news sources  
- **Caution Domains**: Sources to avoid as primary references
- **Special Cases**: EU policy news and other exceptions

### Model Configuration

All agents use Claude Sonnet via AWS Bedrock:
- Model ID: `us.anthropic.claude-sonnet-4-20250514-v1:0`
- Provider: AWS Bedrock
- Region: us-east-1

## Architecture

### Agent Design
Each agent follows the Agno pattern:
- Factory function for instantiation (`get_*_agent()`)
- Structured output using Pydantic models
- Clear, detailed instructions
- Debug mode support
- Session and user tracking

### Workflow Orchestration
The workflow uses Agno's Workflow V2:
- Sequential processing through three agents
- Data transformation between steps
- Error handling and validation
- Statistics and metrics collection

### Data Models
Pydantic models ensure type safety:
- `Article`: Core article data structure
- `FirstPassResult`: Relevance determination
- `ScoringResult`: Multi-dimensional scores
- `SelectorResult`: Final selection with rankings
- `ArticleSelectionInput/Output`: Workflow I/O

## Development

### Package Management with UV

```bash
# Add a new dependency
uv pip install package-name
uv add package-name  # Adds to pyproject.toml

# Add a development dependency
uv add --dev package-name

# Update all dependencies
uv sync

# Show installed packages
uv pip list

# Create requirements.txt for compatibility
uv pip freeze > requirements.txt
```

### Code Quality Tools

```bash
# Format code automatically
./scripts/format.sh

# Run all validation checks
./scripts/validate.sh

# Or run individual tools with UV:
uv run ruff format .     # Format code
uv run ruff check .      # Lint code
uv run mypy .           # Type checking
uv run pytest tests/    # Run tests
```

### Running Tests
```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest --cov=projects --cov=core tests/

# Run specific test file
uv run pytest tests/test_agents.py -v
```

## Key Differences from ADK Version

1. **Framework**: Uses Agno instead of Google ADK
2. **Model**: Claude via AWS Bedrock instead of Gemini
3. **Architecture**: Follows LFX-AI patterns with registries
4. **Instructions**: Direct prompt strings instead of Jinja2 templates
5. **Workflow**: Agno Workflow V2 for orchestration
6. **API**: FastAPI instead of custom server implementation

## Future Enhancements

- [ ] Add persistent storage for processed articles
- [ ] Implement batch processing for large article sets
- [ ] Add caching for repeated article evaluation
- [ ] Create web UI for article review and selection
- [ ] Add metrics and monitoring
- [ ] Implement feedback loop for improving selection
- [ ] Add support for multiple newsletter formats
- [ ] Integrate with email delivery systems

## License

[Your License Here]

## Contributing

Contributions are welcome! Please follow the existing code patterns and include tests for new features.