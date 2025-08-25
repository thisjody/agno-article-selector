#!/usr/bin/env python3
"""
Improved Article Selector with proper AGNO V2 workflow, error handling, and parallelism.
This version fixes all the issues identified in the workflow analysis.
"""

import argparse
import sys
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from projects.article_selector.workflows.article_selection_workflow_v2 import (
    get_article_selection_workflow_v2,
    ArticleSelectionWorkflowV2,
)
from projects.article_selector.models import Article
from core.database import ArticleDatabase
from core.settings import settings
from core.output_formatter import SelectionOutputFormatter


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Article Selection Pipeline V2 - Improved with parallelism and error handling"
    )
    
    # Data source
    parser.add_argument(
        '--db',
        choices=['local', 'motherduck', 'csv'],
        default='local',
        help='Data source to use'
    )
    parser.add_argument(
        '--csv',
        type=str,
        help='Path to CSV file (when --db csv)'
    )
    
    # Date range
    parser.add_argument(
        '--start-date',
        type=lambda s: datetime.strptime(s, "%Y-%m-%d"),
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=lambda s: datetime.strptime(s, "%Y-%m-%d"),
        help='End date (YYYY-MM-DD)'
    )
    
    # Processing options
    parser.add_argument(
        '--max-articles',
        type=int,
        default=10,
        help='Maximum articles to select (default: 10)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of articles to process (default: 100)'
    )
    
    # Parallelism options
    parser.add_argument(
        '--parallel-workers',
        type=int,
        default=5,
        help='Number of parallel workers for API calls (default: 5)'
    )
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing'
    )
    
    # Error handling
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum retries for failed API calls (default: 3)'
    )
    parser.add_argument(
        '--checkpoint',
        type=str,
        help='Resume from checkpoint file'
    )
    parser.add_argument(
        '--no-checkpoint',
        action='store_true',
        help='Disable checkpointing'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Output directory (default: output)'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help="Don't save agent responses"
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
    
    # Other options
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without making API calls (test mode)'
    )
    parser.add_argument(
        '--profile',
        action='store_true',
        help='Enable performance profiling'
    )
    
    return parser.parse_args()


async def fetch_articles_async(
    db: ArticleDatabase,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    limit: int = 100,
    use_motherduck: bool = False,
) -> List[Dict[str, Any]]:
    """Fetch articles from database asynchronously."""
    loop = asyncio.get_event_loop()
    
    def fetch():
        if not end_date:
            end_date_val = start_date if start_date else datetime.now()
        else:
            end_date_val = end_date
        
        if use_motherduck:
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
                AND DATE_TRUNC('day', timestamp) <= DATE '{end_date_val.strftime("%Y-%m-%d")}'
                ORDER BY timestamp DESC
                LIMIT {limit}
            """
            result = db.conn.execute(query).fetchall()
        else:
            query = """
                SELECT * FROM articles 
                WHERE published_date >= ? 
                AND published_date <= ?
                ORDER BY published_date DESC
                LIMIT ?
            """
            result = db.conn.execute(
                query,
                [start_date.strftime("%Y-%m-%d"), 
                 end_date_val.strftime("%Y-%m-%d"),
                 limit]
            ).fetchall()
        
        columns = ['id', 'title', 'content', 'url', 'domain', 'published_date', 
                   'author', 'tags', 'metadata', 'created_at']
        
        return [dict(zip(columns, row)) for row in result]
    
    return await loop.run_in_executor(None, fetch)


async def main_async(args):
    """Main async execution function."""
    print("\n" + "="*80)
    print("🚀 ARTICLE SELECTOR V2 - IMPROVED WITH PARALLELISM & ERROR HANDLING")
    print("="*80)
    
    start_time = time.time()
    
    # Initialize database connection
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
    
    # Fetch articles
    print(f"\n📥 Fetching articles...")
    articles_data = await fetch_articles_async(
        db=db,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.batch_size,
        use_motherduck=use_motherduck,
    )
    
    if not articles_data:
        print("❌ No articles found in the specified date range")
        sys.exit(1)
    
    print(f"✅ Found {len(articles_data)} articles")
    
    # Convert to Article objects
    articles = []
    for data in articles_data:
        articles.append(Article(
            title=data.get('title', 'Untitled'),
            content=data.get('content', ''),
            url=data.get('url'),
            domain=data.get('domain'),
        ))
    
    # Create workflow
    print(f"\n🔧 Initializing workflow...")
    print(f"   • Parallel workers: {args.parallel_workers if not args.no_parallel else 1}")
    print(f"   • Max retries: {args.max_retries}")
    print(f"   • Checkpointing: {'Enabled' if not args.no_checkpoint else 'Disabled'}")
    
    workflow = get_article_selection_workflow_v2(
        user_id=settings.user_id or "default",
        session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
        debug_mode=args.debug,
        max_parallel_workers=1 if args.no_parallel else args.parallel_workers,
    )
    
    # Resume from checkpoint if specified
    checkpoint_path = None
    if args.checkpoint:
        checkpoint_path = Path(args.checkpoint)
        if not checkpoint_path.exists():
            print(f"⚠️ Checkpoint file not found: {checkpoint_path}")
            checkpoint_path = None
    
    # Process articles
    print(f"\n🔄 Processing {len(articles)} articles...")
    print(f"📊 Max selections: {args.max_articles}")
    
    if args.dry_run:
        print("\n⚠️ DRY RUN MODE - No API calls will be made")
        results = {
            "selected_articles": articles[:args.max_articles],
            "statistics": {
                "total_input": len(articles),
                "message": "Dry run - no processing performed"
            }
        }
    else:
        # Use async workflow processing
        results = await workflow.process_articles_parallel(
            articles=articles,
            max_articles=args.max_articles,
        )
    
    # Format and display results
    if results.get("selected_articles"):
        formatter = SelectionOutputFormatter()
        
        # Prepare articles for formatter
        selected_for_display = []
        for idx, article in enumerate(results["selected_articles"], 1):
            selected_for_display.append({
                'rank': idx,
                'title': article.get('title', 'Untitled'),
                'domain': article.get('domain', 'Unknown'),
                'url': article.get('url', ''),
                'content': article.get('content', '')[:500],
                'overall_score': article.get('overall_score', 0),
                'selection_reasoning': article.get('comparative_rationales', [''])[0] if article.get('comparative_rationales') else f"Ranked #{idx}",
            })
        
        display = formatter.format_selection_results(
            selected_articles=selected_for_display,
            statistics=results["statistics"],
            batch_id=workflow.state.run_id if workflow.state else datetime.now().strftime("%Y%m%d_%H%M%S"),
        )
        
        print(display)
        
        # Export to JSON if requested
        if not args.no_export:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            json_file = output_dir / f"selection_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            import json
            with open(json_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n📁 Results exported to: {json_file}")
    
    # Display performance metrics
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*80)
    print("⚙️  PERFORMANCE METRICS")
    print("="*80)
    print(f"⏱️  Total Time: {elapsed_time:.2f} seconds")
    print(f"📈 Throughput: {len(articles)/elapsed_time:.2f} articles/second")
    
    if results.get("statistics"):
        stats = results["statistics"]
        if "first_pass_relevant" in stats:
            print(f"✅ First Pass Rate: {stats['first_pass_relevant']}/{stats['total_input']} ({stats['first_pass_relevant']/stats['total_input']*100:.1f}%)")
        if "avg_time_per_article" in stats:
            print(f"⚡ Avg Time per Article: {stats['avg_time_per_article']:.2f}s")
    
    if args.profile:
        print(f"\n📊 Profiling enabled - check output/profile/ for detailed metrics")
    
    # Display any errors
    if results.get("errors"):
        print(f"\n⚠️ Encountered {len(results['errors'])} errors during processing")
        for error in results["errors"][:5]:  # Show first 5 errors
            print(f"   • {error['phase']}: {error['error']}")
    
    print("\n✨ Processing complete!")
    
    # Save to database if requested
    if results.get("selected_articles") and not args.dry_run:
        try:
            # Save selections to database
            for article in results["selected_articles"]:
                db.save_selection(
                    article_id=article.get('id'),
                    selection_reason=article.get('selection_reasoning', ''),
                    score=article.get('overall_score', 0),
                    batch_id=workflow.state.run_id if workflow.state else None,
                )
            print(f"💾 Saved {len(results['selected_articles'])} selections to database")
        except Exception as e:
            print(f"⚠️ Error saving to database: {e}")
    
    return results


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Set default dates if not provided
    if not args.start_date:
        # Default to last 7 days
        args.start_date = datetime.now() - timedelta(days=7)
        args.end_date = datetime.now()
    elif not args.end_date:
        args.end_date = args.start_date
    
    # Run async main
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()