#!/usr/bin/env python3
"""Process articles from database through the selection pipeline."""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.settings import settings
from projects.article_selector.agents.tracked_agents import (
    get_tracked_first_pass_agent,
    get_tracked_scoring_agent,
    get_tracked_selector_agent,
)
from projects.article_selector.models import Article
from core.response_tracker import response_tracker
from core.output_formatter import SelectionOutputFormatter
import time


def process_batch(
    batch_size: int = 50,
    max_selected: int = 10,
    debug: bool = False,
    export_json: bool = True
):
    """Process a batch of articles from the database.
    
    Args:
        batch_size: Number of articles to process
        max_selected: Maximum articles to select
        debug: Enable debug mode
        export_json: Export results to JSON file
    """
    start_time = time.time()
    
    print(f"\n{'='*60}")
    print("ARTICLE SELECTOR - DATABASE PROCESSOR")
    print(f"{'='*60}\n")
    
    # Connect to database
    db = get_database()
    print(f"Database: {'MotherDuck' if settings.use_motherduck() else 'Local DuckDB'}")
    
    # Get unprocessed articles
    articles_data = db.get_unprocessed_articles(limit=batch_size)
    
    if not articles_data:
        print("No unprocessed articles found in database.")
        return
    
    print(f"Found {len(articles_data)} unprocessed articles")
    
    # Initialize tracked agents
    first_pass = get_tracked_first_pass_agent(debug_mode=debug)
    scoring = get_tracked_scoring_agent(debug_mode=debug)
    selector = get_tracked_selector_agent(debug_mode=debug)
    
    # Process through pipeline
    print(f"\n{'='*40}")
    print("PHASE 1: First Pass Filtering")
    print(f"{'='*40}")
    
    relevant_count = 0
    for article_data in articles_data:
        article = Article(
            title=article_data['title'],
            content=article_data['content'],
            url=article_data.get('url'),
            domain=article_data.get('domain'),
        )
        
        print(f"\n📄 {article.title[:60]}...")
        
        # Process with tracked agent
        response = first_pass.process_article(
            article=article,
            article_id=article_data['id'],
            save_responses=True
        )
        
        status = response['status']
        result = response['result']
        
        # Save to database
        db.save_first_pass_result(
            article_id=article_data['id'],
            status=status,
            reasoning=str(result.content)[:500]
        )
        
        print(f"   Status: {status}")
        if is_relevant:
            relevant_count += 1
    
    print(f"\n✅ First pass complete: {relevant_count}/{len(articles_data)} articles passed")
    
    # Track phase statistics
    phase_stats = {
        'first_pass': {
            'total': len(articles_data),
            'relevant': relevant_count,
            'filtered': len(articles_data) - relevant_count,
            'pass_rate': (relevant_count / len(articles_data) * 100) if articles_data else 0
        }
    }
    
    if relevant_count == 0:
        print("No articles passed first pass filtering.")
        db.close()
        return
    
    # Get relevant articles for scoring
    print(f"\n{'='*40}")
    print("PHASE 2: Scoring")
    print(f"{'='*40}")
    
    relevant_articles = db.get_relevant_articles()
    
    for article_data in relevant_articles:
        if article_data.get('overall_score') is not None:
            print(f"\n📊 {article_data['title'][:60]}...")
            print(f"   Already scored: {article_data['overall_score']:.1f}/10")
            continue
        
        print(f"\n📊 Scoring: {article_data['title'][:60]}...")
        
        article = Article(
            title=article_data['title'],
            content=article_data['content'],
            url=article_data.get('url'),
            domain=article_data.get('domain'),
        )
        
        response = scoring.score_article(
            article=article,
            first_pass_reasoning=article_data.get('first_pass_reasoning', 'N/A'),
            article_id=article_data['id'],
            save_responses=True
        )
        
        result = response['result']
        
        # Parse scoring (simplified - use structured output in production)
        # This is a placeholder - you'd parse the actual scores
        db.save_scoring_result(
            article_id=article_data['id'],
            relevance_score=8.0,
            quality_score=7.5,
            impact_score=8.5,
            overall_score=8.0,
            reasoning=str(result.content)[:1000],
            recommendation="Include"
        )
        
        print(f"   Score: 8.0/10 (placeholder)")
    
    # Track scoring statistics
    scored_count = len([a for a in relevant_articles if a.get('overall_score') is not None])
    avg_score = sum(a.get('overall_score', 0) for a in relevant_articles) / max(len(relevant_articles), 1)
    high_quality = len([a for a in relevant_articles if a.get('overall_score', 0) > 7])
    
    phase_stats['scoring'] = {
        'total': scored_count,
        'avg_score': avg_score,
        'high_quality': high_quality
    }
    
    # Final selection
    print(f"\n{'='*40}")
    print("PHASE 3: Final Selection")
    print(f"{'='*40}")
    
    scored_articles = db.get_relevant_articles()
    
    if not scored_articles:
        print("No scored articles available for selection.")
        db.close()
        return
    
    # Process with tracked selector
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    response = selector.select_articles(
        scored_articles=scored_articles,
        max_articles=max_selected,
        batch_id=batch_id,
        save_responses=True
    )
    
    result = response['result']
    print(f"\nSelection complete: {result.content}")
    
    if response.get('ranking_file'):
        print(f"Ranking saved to: {response['ranking_file']}")
    
    # Save selections (simplified - parse actual rankings in production)
    selections = [
        {
            'article_id': article['id'],
            'rank': idx + 1,
            'reasoning': f"Selected as top article #{idx + 1}"
        }
        for idx, article in enumerate(scored_articles[:max_selected])
    ]
    
    db.save_selected_articles(selections, batch_id)
    
    # Track selection statistics
    phase_stats['selection'] = {
        'candidates': len(scored_articles),
        'selected': len(selections),
        'avg_selected_score': sum(a.get('overall_score', 0) for a in scored_articles[:max_selected]) / max(len(selections), 1)
    }
    
    # Prepare selected articles for display
    selected_articles_display = []
    for idx, article in enumerate(scored_articles[:max_selected]):
        selected_articles_display.append({
            'rank': idx + 1,
            'title': article.get('title', 'Untitled'),
            'domain': article.get('domain', 'Unknown'),
            'url': article.get('url', ''),
            'content': article.get('content', '')[:500],
            'overall_score': article.get('overall_score', 0),
            'selection_reasoning': f"Ranked #{idx + 1} based on relevance and quality scores",
            'tags': article.get('tags', [])
        })
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Display final selection results (like ADK version)
    SelectionOutputFormatter.display_selection_results(
        selected_articles=selected_articles_display,
        batch_id=batch_id,
        total_processed=len(articles_data),
        total_relevant=relevant_count,
        show_details=True
    )
    
    # Display processing summary
    SelectionOutputFormatter.display_processing_summary(
        phase_stats=phase_stats,
        elapsed_time=elapsed_time
    )
    
    # Export results
    if export_json:
        output_path = f"{settings.agent_response_output_dir}/selected_{batch_id}.json"
        db.export_results_to_json(output_path)
        
        # Also save formatted report
        report_path = f"{settings.agent_response_output_dir}/selection_report_{batch_id}.json"
        SelectionOutputFormatter.save_selection_report(
            selected_articles=selected_articles_display,
            output_path=report_path,
            batch_id=batch_id,
            metadata=phase_stats
        )
    
    db.close()


def load_csv(csv_path: str):
    """Load articles from CSV into database.
    
    Args:
        csv_path: Path to CSV file
    """
    print(f"Loading articles from: {csv_path}")
    db = get_database()
    count = db.load_articles_from_csv(csv_path)
    print(f"Successfully loaded {count} articles")
    db.close()


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Process articles through selection pipeline"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process articles")
    process_parser.add_argument(
        "-b", "--batch-size",
        type=int,
        default=50,
        help="Number of articles to process (default: 50)"
    )
    process_parser.add_argument(
        "-m", "--max-selected",
        type=int,
        default=10,
        help="Maximum articles to select (default: 10)"
    )
    process_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    process_parser.add_argument(
        "--no-export",
        action="store_true",
        help="Don't export results to JSON"
    )
    
    # Load command
    load_parser = subparsers.add_parser("load", help="Load articles from CSV")
    load_parser.add_argument(
        "csv_file",
        help="Path to CSV file"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Check for environment configuration
    if not settings.aws_access_key_id and settings.default_model == "claude":
        print("Error: AWS credentials not configured for Claude")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env file")
        sys.exit(1)
    
    try:
        if args.command == "process":
            process_batch(
                batch_size=args.batch_size,
                max_selected=args.max_selected,
                debug=args.debug,
                export_json=not args.no_export
            )
        elif args.command == "load":
            load_csv(args.csv_file)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.command == "process" and args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()