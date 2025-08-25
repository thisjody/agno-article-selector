#!/usr/bin/env python3
"""Test loading and processing articles from CSV without requiring AWS credentials."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import ArticleDatabase
from core.output_formatter import SelectionOutputFormatter
import pandas as pd
from datetime import datetime
import time

def test_csv_processing():
    """Test loading articles from CSV and simulating the selection process."""
    
    print("\n" + "="*80)
    print("🧪 TESTING ARTICLE SELECTOR WITH CSV DATA")
    print("="*80 + "\n")
    
    csv_path = "data/master_articles.csv"
    
    # Load CSV
    print(f"📁 Loading articles from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df)} articles from CSV")
    
    # Show sample
    print("\n📰 Sample articles:")
    for idx, row in df.head(3).iterrows():
        print(f"\n  {idx+1}. {row['Title'][:80]}...")
        print(f"     Domain: {row['Domain']}")
        print(f"     Decision: {row.get('Decision', 'Unknown')}")
    
    # Initialize local database
    print("\n🗄️  Initializing local DuckDB database...")
    db = ArticleDatabase(use_motherduck=False)
    
    # Load into database
    count = db.load_articles_from_csv(csv_path)
    print(f"✅ Loaded {count} articles into database")
    
    # Query unprocessed articles
    articles = db.get_unprocessed_articles(limit=10)
    print(f"\n📋 Retrieved {len(articles)} unprocessed articles for testing")
    
    # Simulate processing (without actual AI agents)
    print("\n🎯 Simulating article selection process...")
    
    start_time = time.time()
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Simulate first pass (use Decision column if available)
    relevant_articles = []
    for article in articles:
        # For testing, mark articles with certain domains as relevant
        preferred_domains = ['kernel.org', 'openssl.org', 'apache.org', 'rust-lang.org', 'snyk.io']
        is_relevant = any(domain in article.get('domain', '') for domain in preferred_domains)
        
        if is_relevant:
            relevant_articles.append(article)
    
    print(f"   Phase 1: {len(relevant_articles)}/{len(articles)} passed first pass")
    
    # Simulate scoring
    scored_articles = []
    for article in relevant_articles:
        # Generate mock score based on title length and domain
        score = 7.0 + (len(article.get('title', '')) % 30) / 10
        scored_articles.append({
            **article,
            'overall_score': score,
            'selection_reasoning': f"High relevance to open source security"
        })
    
    scored_articles.sort(key=lambda x: x['overall_score'], reverse=True)
    print(f"   Phase 2: Scored {len(scored_articles)} articles")
    
    # Select top articles
    max_articles = 5
    selected_articles = []
    for idx, article in enumerate(scored_articles[:max_articles], 1):
        selected_articles.append({
            'rank': idx,
            'title': article.get('title', 'Untitled'),
            'domain': article.get('domain', 'Unknown'),
            'url': article.get('url', ''),
            'content': article.get('content', '')[:500],
            'overall_score': article.get('overall_score', 0),
            'selection_reasoning': article.get('selection_reasoning', ''),
        })
    
    print(f"   Phase 3: Selected top {len(selected_articles)} articles")
    
    elapsed_time = time.time() - start_time
    
    # Display results using the formatter
    SelectionOutputFormatter.display_selection_results(
        selected_articles=selected_articles,
        batch_id=batch_id,
        total_processed=len(articles),
        total_relevant=len(relevant_articles),
        show_details=True
    )
    
    # Display summary
    phase_stats = {
        'first_pass': {
            'total': len(articles),
            'relevant': len(relevant_articles),
            'filtered': len(articles) - len(relevant_articles),
            'pass_rate': (len(relevant_articles) / len(articles) * 100) if articles else 0
        },
        'scoring': {
            'total': len(scored_articles),
            'avg_score': sum(a['overall_score'] for a in scored_articles) / max(len(scored_articles), 1) if scored_articles else 0,
            'high_quality': len([a for a in scored_articles if a['overall_score'] > 7])
        },
        'selection': {
            'candidates': len(scored_articles),
            'selected': len(selected_articles),
            'avg_selected_score': sum(a['overall_score'] for a in selected_articles) / max(len(selected_articles), 1) if selected_articles else 0
        }
    }
    
    SelectionOutputFormatter.display_processing_summary(
        phase_stats=phase_stats,
        elapsed_time=elapsed_time
    )
    
    # Save to database
    print("\n💾 Saving results to database...")
    for idx, article in enumerate(selected_articles):
        # Save selection (simplified)
        pass
    
    db.close()
    print("✅ Test complete!")
    
    return True


if __name__ == "__main__":
    try:
        test_csv_processing()
        
        print("\n" + "="*80)
        print("📝 NEXT STEPS")
        print("="*80)
        print("\n1. Add AWS credentials to .env for Claude:")
        print("   AWS_ACCESS_KEY_ID=your_key")
        print("   AWS_SECRET_ACCESS_KEY=your_secret")
        print("\n2. Run with actual AI agents:")
        print("   python run_article_selector.py --csv data/master_articles.csv")
        print("\n3. Or connect to MotherDuck if raw articles table exists:")
        print("   python run_article_selector.py --db motherduck --start-date 2025-08-13")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()