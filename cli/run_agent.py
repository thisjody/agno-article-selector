#!/usr/bin/env python3
"""CLI for running article selector agents."""

import json
import argparse
from typing import Optional, Dict, Any
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agents import agent_registry
from projects.article_selector.models import Article


def load_json_file(filepath: str) -> Dict[str, Any]:
    """Load JSON data from a file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def run_first_pass_agent(input_data: Dict[str, Any], debug: bool = False):
    """Run the first pass filtering agent."""
    from projects.article_selector.agents import get_first_pass_agent
    
    agent = get_first_pass_agent(debug_mode=debug)
    
    # Create article from input
    article = Article(**input_data)
    
    # Format message for agent
    message = f"""Evaluate this article:
Title: {article.title}
Content: {article.content}
Domain: {article.domain or 'Unknown'}
URL: {article.url or 'N/A'}"""
    
    # Run agent
    result = agent.run(message)
    return result


def run_scoring_agent(input_data: Dict[str, Any], debug: bool = False):
    """Run the scoring agent."""
    from projects.article_selector.agents import get_scoring_agent
    
    agent = get_scoring_agent(debug_mode=debug)
    
    # Extract article and reasoning
    article = Article(**input_data.get("article", input_data))
    first_pass_reasoning = input_data.get("first_pass_reasoning", "Passed initial filtering")
    
    # Format message for agent
    message = f"""Score this article that passed first-pass filtering:
Title: {article.title}
Content: {article.content}
Domain: {article.domain or 'Unknown'}
URL: {article.url or 'N/A'}
First-pass reasoning: {first_pass_reasoning}"""
    
    # Run agent
    result = agent.run(message)
    return result


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Run article selector agents")
    parser.add_argument(
        "agent",
        choices=["first_pass", "scoring", "list"],
        help="Agent to run or 'list' to show available agents"
    )
    parser.add_argument(
        "-f", "--file",
        help="JSON file with input data"
    )
    parser.add_argument(
        "-d", "--data",
        help="JSON string with input data"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "-p", "--pretty",
        action="store_true",
        help="Pretty print JSON output"
    )
    
    args = parser.parse_args()
    
    # Handle list command
    if args.agent == "list":
        agents = agent_registry.list_agents("article_selector")
        print("Available agents:")
        for agent_id in agents.get("article_selector", []):
            print(f"  - {agent_id}")
        return
    
    # Load input data
    input_data = {}
    if args.file:
        input_data = load_json_file(args.file)
    elif args.data:
        input_data = json.loads(args.data)
    else:
        # Try to load sample input
        sample_file = Path(__file__).parent.parent / f"projects/article_selector/agents/sample-inputs/{args.agent}_agent.json"
        if sample_file.exists():
            print(f"Using sample input from {sample_file}")
            input_data = load_json_file(str(sample_file))
        else:
            print("Error: No input data provided. Use -f FILE or -d JSON_STRING")
            sys.exit(1)
    
    # Run the appropriate agent
    try:
        if args.agent == "first_pass":
            result = run_first_pass_agent(input_data, args.debug)
        elif args.agent == "scoring":
            result = run_scoring_agent(input_data, args.debug)
        else:
            print(f"Unknown agent: {args.agent}")
            sys.exit(1)
        
        # Output result
        if args.pretty:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(result)
            
    except Exception as e:
        print(f"Error running agent: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()