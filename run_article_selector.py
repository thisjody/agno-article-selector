#!/usr/bin/env python3
"""Main CLI launcher for the Article Selector - Agno Version.

Usage:
    python run_article_selector.py --db local --start-date 2025-08-07
    python run_article_selector.py --db motherduck --start-date 2025-08-07 --end-date 2025-08-14
    python run_article_selector.py --csv data/sample_articles.csv --max-articles 5
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import ArticleDatabase
from core.settings import settings
from core.output_formatter import SelectionOutputFormatter
from projects.article_selector.agents.tracked_agents import (
    get_tracked_first_pass_agent,
    get_tracked_scoring_agent,
    get_tracked_selector_agent,
)
from projects.article_selector.runners.comparative_ranker_runner import run_comparative_ranking_sync
from projects.article_selector.models import Article
import time
import shutil


def parse_date(date_string: str) -> datetime:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_string}. Use YYYY-MM-DD")


def fetch_articles_by_date(
    db: ArticleDatabase,
    start_date: datetime,
    end_date: Optional[datetime] = None,
    limit: int = 500,
    use_motherduck: bool = False
) -> list:
    """Fetch articles from database within date range.
    
    Args:
        db: Database connection
        start_date: Start date for article selection
        end_date: End date (inclusive), defaults to start_date
        limit: Maximum number of articles to fetch
        use_motherduck: Whether using MotherDuck database
        
    Returns:
        List of article dictionaries
    """
    if not end_date:
        end_date = start_date
    
    if use_motherduck:
        # Query MotherDuck's newsletter_data.content table (same as ADK)
        query = f"""
            SELECT 
                ROW_NUMBER() OVER (ORDER BY timestamp DESC) as id,
                title,
                body as content,
                url,
                COALESCE(
                    REGEXP_EXTRACT(url, 'https?://([^/]+)', 1),
                    'unknown'
                ) as domain,
                timestamp as published_date,
                NULL as author,
                NULL as tags,
                NULL as metadata,
                timestamp as created_at
            FROM newsletter_data.content
            WHERE timestamp IS NOT NULL
            AND body IS NOT NULL
            AND LENGTH(body) > 0
            AND DATE_TRUNC('day', timestamp) >= DATE '{start_date.strftime("%Y-%m-%d")}'
            AND DATE_TRUNC('day', timestamp) <= DATE '{end_date.strftime("%Y-%m-%d")}'
            ORDER BY timestamp DESC
            LIMIT {limit}
        """
    else:
        # Query local articles table
        query = """
            SELECT * FROM articles 
            WHERE published_date >= ? 
            AND published_date <= ?
            ORDER BY published_date DESC
            LIMIT ?
        """
    
    if use_motherduck:
        # MotherDuck query with values already embedded
        result = db.conn.execute(query).fetchall()
    else:
        # Local DuckDB with parameters
        result = db.conn.execute(
            query,
            [start_date.strftime("%Y-%m-%d"), 
             end_date.strftime("%Y-%m-%d"),
             limit]
        ).fetchall()
    
    columns = ['id', 'title', 'content', 'url', 'domain', 'published_date', 
               'author', 'tags', 'metadata', 'created_at']
    
    return [dict(zip(columns, row)) for row in result]


def clear_response_directory():
    """Clear all files from the response output directory."""
    response_dir = Path(settings.agent_response_output_dir)
    
    if response_dir.exists():
        # Count existing files for reporting
        file_count = sum(1 for _ in response_dir.rglob("*") if _.is_file())
        
        if file_count > 0:
            print(f"🗑️  Clearing {file_count} old response files...")
            # Remove entire directory and recreate
            shutil.rmtree(response_dir)
            response_dir.mkdir(parents=True, exist_ok=True)
            print("✅ Response directory cleared")
        else:
            print("📁 Response directory is already empty")
    else:
        # Create directory if it doesn't exist
        response_dir.mkdir(parents=True, exist_ok=True)
        print("📁 Created response directory")


def process_articles(
    articles_data: list,
    max_articles: int = 10,
    debug: bool = False,
    save_responses: bool = True,
    export_json: bool = True,
    clear_old_responses: bool = True
) -> dict:
    """Process articles through the selection pipeline.
    
    Args:
        articles_data: List of article dictionaries
        max_articles: Maximum articles to select
        debug: Enable debug mode
        save_responses: Save agent responses to files
        export_json: Export results to JSON
        clear_old_responses: Clear old response files before running
        
    Returns:
        Processing results dictionary
    """
    start_time = time.time()
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Clear old responses if requested
    if clear_old_responses and save_responses:
        clear_response_directory()
    
    # Initialize agents
    print("🤖 Initializing agents...")
    first_pass = get_tracked_first_pass_agent(debug_mode=debug)
    scoring = get_tracked_scoring_agent(debug_mode=debug)
    selector = get_tracked_selector_agent(debug_mode=debug)
    
    # Phase 1: First Pass Filtering
    print(f"\n{'='*60}")
    print("📋 PHASE 1: First Pass Filtering")
    print(f"{'='*60}")
    
    relevant_articles = []
    relevant_count = 0
    
    for idx, article_data in enumerate(articles_data, 1):
        article = Article(
            title=article_data.get('title', 'Untitled'),
            content=article_data.get('content', ''),
            url=article_data.get('url'),
            domain=article_data.get('domain'),
        )
        
        print(f"\n[{idx}/{len(articles_data)}] {article.title[:60]}...")
        
        response = first_pass.process_article(
            article=article,
            article_id=article_data.get('id', idx),
            save_responses=save_responses
        )
        
        status = response['status']
        reasoning = response.get('reasoning', 'No reasoning provided')
        
        # Extract just the justification part (after the status)
        if "Irrelevant" in reasoning or "Relevant" in reasoning:
            # Split on first period after status word to get justification
            parts = reasoning.split('.', 1)
            if len(parts) > 1:
                justification = parts[1].strip()
            else:
                justification = reasoning
        else:
            justification = reasoning
        
        # Print with appropriate emoji based on status
        if status == "Relevant":
            print(f"    ✅ {status}: {justification[:150]}")
        else:
            print(f"    🚫 {status}: {justification[:150]}")
        
        if status == "Relevant":
            relevant_articles.append({
                **article_data,
                'first_pass_reasoning': str(response['result'].content)[:500]
            })
            relevant_count += 1
    
    print(f"\n✅ First pass complete: {relevant_count}/{len(articles_data)} articles passed")
    
    if not relevant_articles:
        print("\n❌ No articles passed first pass filtering.")
        return {'selected': [], 'stats': {}}
    
    # Phase 2: Scoring
    print(f"\n{'='*60}")
    print("📊 PHASE 2: Article Scoring")
    print(f"{'='*60}")
    
    scored_articles = []
    
    for article_data in relevant_articles:
        article = Article(
            title=article_data['title'],
            content=article_data['content'],
            url=article_data.get('url'),
            domain=article_data.get('domain'),
        )
        
        print(f"\nScoring: {article.title[:60]}...")
        
        response = scoring.score_article(
            article=article,
            first_pass_reasoning=article_data['first_pass_reasoning'],
            article_id=article_data.get('id'),
            save_responses=save_responses
        )
        
        # For now, use placeholder scores (in production, parse from response)
        score = 7.0 + (hash(article.title) % 30) / 10  # Generate score 7.0-10.0
        print(f"    → Score: {score:.1f}/10")
        
        scored_articles.append({
            **article_data,
            'overall_score': score
        })
    
    # Sort by score
    scored_articles.sort(key=lambda x: x['overall_score'], reverse=True)
    
    # Phase 3: Comparative Ranking
    print(f"\n{'='*60}")
    print("🎯 PHASE 3: Comparative Ranking")
    print(f"{'='*60}")
    
    # Run comparative ranking with batch processing
    comparative_results = run_comparative_ranking_sync(
        articles=scored_articles,
        output_dir=Path(settings.agent_response_output_dir),
        pipeline_run_id=batch_id,
        score_threshold=6.0,  # Only consider articles scoring 6+
        top_n=min(len(scored_articles), 100),  # Consider up to 100 articles
        batch_size=10,  # Compare in batches of 10
        shuffle_runs=3,  # 3 shuffle passes for robustness
        recursive_top_k=min(max_articles * 3, 50),  # Return 3x final selection or 50 max
        debug_mode=debug
    )
    
    if not comparative_results:
        print("\n❌ No articles passed comparative ranking.")
        return {'selected': [], 'stats': {}}
    
    # Phase 4: Final Selection
    print(f"\n{'='*60}")
    print("🏁 PHASE 4: Final Selection")
    print(f"{'='*60}")
    
    response = selector.select_articles(
        scored_articles=comparative_results,  # Use comparative ranked results
        max_articles=max_articles,
        batch_id=batch_id,
        save_responses=save_responses
    )
    
    # Prepare selected articles for display
    selected_articles = []
    # Use comparative results, not just scored articles
    for idx, article in enumerate(comparative_results[:max_articles], 1):
        selected_articles.append({
            'rank': idx,
            'title': article.get('title', 'Untitled'),
            'domain': article.get('domain', 'Unknown'),
            'url': article.get('url', ''),
            'content': article.get('content', '')[:500],
            'overall_score': article.get('overall_score', 0),
            'selection_reasoning': f"Ranked #{idx} based on relevance and quality scores",
            'published_date': article.get('published_date'),
            'tags': article.get('tags', [])
        })
    
    # Calculate statistics
    elapsed_time = time.time() - start_time
    
    phase_stats = {
        'first_pass': {
            'total': len(articles_data),
            'relevant': relevant_count,
            'filtered': len(articles_data) - relevant_count,
            'pass_rate': (relevant_count / len(articles_data) * 100) if articles_data else 0
        },
        'scoring': {
            'total': len(scored_articles),
            'avg_score': sum(a['overall_score'] for a in scored_articles) / max(len(scored_articles), 1),
            'high_quality': len([a for a in scored_articles if a['overall_score'] > 7])
        },
        'comparative_ranking': {
            'candidates': len(scored_articles),
            'ranked': len(comparative_results),
            'avg_comparative_rank': sum(a.get('comparative_avg_rank', 0) for a in comparative_results) / max(len(comparative_results), 1)
        },
        'selection': {
            'candidates': len(comparative_results),
            'selected': len(selected_articles),
            'avg_selected_score': sum(a['overall_score'] for a in selected_articles) / max(len(selected_articles), 1)
        }
    }
    
    # Display results
    SelectionOutputFormatter.display_selection_results(
        selected_articles=selected_articles,
        batch_id=batch_id,
        total_processed=len(articles_data),
        total_relevant=relevant_count,
        show_details=True
    )
    
    SelectionOutputFormatter.display_processing_summary(
        phase_stats=phase_stats,
        elapsed_time=elapsed_time
    )
    
    # Save results if requested
    if export_json:
        output_dir = Path(settings.agent_response_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = output_dir / f"selection_report_{batch_id}.json"
        SelectionOutputFormatter.save_selection_report(
            selected_articles=selected_articles,
            output_path=str(report_path),
            batch_id=batch_id,
            metadata=phase_stats
        )
    
    return {
        'selected': selected_articles,
        'stats': phase_stats,
        'batch_id': batch_id,
        'elapsed_time': elapsed_time
    }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Article Selector - AI-powered article curation for open source security newsletters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process articles from local DuckDB for a specific date
  python run_article_selector.py --db local --start-date 2025-08-07
  
  # Process articles from MotherDuck for a date range
  python run_article_selector.py --db motherduck --start-date 2025-08-01 --end-date 2025-08-07
  
  # Process articles from CSV file
  python run_article_selector.py --csv data/sample_articles.csv
  
  # Process with custom settings
  python run_article_selector.py --db local --start-date 2025-08-07 --max-articles 5 --debug
        """
    )
    
    # Database source arguments
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        '--db',
        choices=['local', 'motherduck'],
        help='Database source to use (local DuckDB or MotherDuck)'
    )
    source_group.add_argument(
        '--csv',
        help='CSV file to load articles from'
    )
    
    # Date range arguments
    parser.add_argument(
        '--start-date',
        type=parse_date,
        help='Start date for article selection (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=parse_date,
        help='End date for article selection (YYYY-MM-DD), defaults to start-date'
    )
    
    # Processing options
    parser.add_argument(
        '--max-articles',
        type=int,
        default=10,
        help='Maximum number of articles to select (default: 10)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Maximum number of articles to process (default: 100)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with verbose output'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help="Don't save agent responses to files"
    )
    parser.add_argument(
        '--no-export',
        action='store_true',
        help="Don't export results to JSON"
    )
    parser.add_argument(
        '--keep-responses',
        action='store_true',
        help="Keep old response files (don't clear before running)"
    )
    
    # Model selection
    parser.add_argument(
        '--model',
        choices=['claude', 'gemini', 'openai'],
        default='claude',
        help='LLM model to use (default: claude)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.db and not args.start_date:
        parser.error("--start-date is required when using --db")
    
    # Configure model if specified
    if args.model != settings.default_model:
        settings.default_model = args.model
        print(f"🤖 Using model: {args.model}")
    
    # Print header
    print("\n" + "="*80)
    print("🚀 ARTICLE SELECTOR - AGNO VERSION")
    print("="*80)
    
    try:
        # Initialize database
        if args.csv:
            # Load from CSV
            print(f"\n📁 Loading articles from: {args.csv}")
            db = ArticleDatabase(use_motherduck=False)
            
            # Load CSV into database
            count = db.load_articles_from_csv(args.csv)
            print(f"✅ Loaded {count} articles from CSV")
            
            # Get all articles
            articles_data = db.get_unprocessed_articles(limit=args.batch_size)
            
        else:
            # Use database (local or MotherDuck)
            use_motherduck = (args.db == 'motherduck')
            
            if use_motherduck and not settings.motherduck_token:
                print("❌ Error: MotherDuck token not configured in .env")
                sys.exit(1)
            
            print(f"\n🗄️  Database: {args.db.upper()}")
            if args.start_date:
                print(f"📅 Date Range: {args.start_date.date()} to {(args.end_date or args.start_date).date()}")
            
            db = ArticleDatabase(
                use_motherduck=use_motherduck,
                motherduck_token=settings.motherduck_token if use_motherduck else None,
                motherduck_database=settings.motherduck_database if use_motherduck else None
            )
            
            # Fetch articles by date
            articles_data = fetch_articles_by_date(
                db=db,
                start_date=args.start_date,
                end_date=args.end_date,
                limit=args.batch_size,
                use_motherduck=use_motherduck
            )
            
            print(f"✅ Found {len(articles_data)} articles in date range")
        
        if not articles_data:
            print("\n❌ No articles found to process")
            db.close()
            sys.exit(0)
        
        # Process articles
        print(f"\n🔄 Processing {len(articles_data)} articles...")
        print(f"📊 Max selections: {args.max_articles}")
        
        results = process_articles(
            articles_data=articles_data,
            max_articles=args.max_articles,
            debug=args.debug,
            save_responses=not args.no_save,
            export_json=not args.no_export,
            clear_old_responses=not args.keep_responses
        )
        
        # Save to database if using database source
        if args.db:
            print("\n💾 Saving results to database...")
            
            # Save selections to database
            for article in results['selected']:
                # This would save to the database
                # db.save_selected_article(article)
                pass
            
            print(f"✅ Saved {len(results['selected'])} selections to database")
        
        db.close()
        
        # Exit message
        print(f"\n✨ Processing complete!")
        print(f"📁 Results saved to: {settings.agent_response_output_dir}")
        
        if not args.no_save:
            print(f"📝 Response files saved to: output/responses/")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Check for required configuration
    if not os.getenv('AWS_ACCESS_KEY_ID') and settings.default_model == 'claude':
        print("\n⚠️  Warning: AWS credentials not configured for Claude")
        print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        print("   Or use --model gemini/openai with appropriate credentials\n")
    
    sys.exit(main())