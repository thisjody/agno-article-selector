#!/bin/bash
# Convenient wrapper script for running the article selector

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DB_TYPE="local"
START_DATE=$(date +%Y-%m-%d)
MAX_ARTICLES=10

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --motherduck)
            DB_TYPE="motherduck"
            shift
            ;;
        --date)
            START_DATE="$2"
            shift 2
            ;;
        --max)
            MAX_ARTICLES="$2"
            shift 2
            ;;
        --debug)
            DEBUG_FLAG="--debug"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --motherduck     Use MotherDuck instead of local DuckDB"
            echo "  --date DATE      Process articles from DATE (YYYY-MM-DD)"
            echo "  --max N          Select maximum N articles (default: 10)"
            echo "  --debug          Enable debug mode"
            echo "  --help           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Process today's articles from local DB"
            echo "  $0 --date 2025-08-07         # Process specific date"
            echo "  $0 --motherduck --max 5      # Use MotherDuck, select 5 articles"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source .venv/bin/activate 2>/dev/null || {
        echo -e "${RED}Virtual environment not found. Run ./scripts/dev_setup.sh first${NC}"
        exit 1
    }
fi

# Check for .env file
if [[ ! -f .env ]]; then
    echo -e "${YELLOW}Creating .env from template...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env with your credentials before running${NC}"
    exit 1
fi

# Run the article selector
echo -e "${GREEN}Running Article Selector${NC}"
echo "Database: $DB_TYPE"
echo "Date: $START_DATE"
echo "Max Articles: $MAX_ARTICLES"
echo ""

uv run python run_article_selector.py \
    --db "$DB_TYPE" \
    --start-date "$START_DATE" \
    --max-articles "$MAX_ARTICLES" \
    $DEBUG_FLAG