"""Output formatting for article selection results."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json


class SelectionOutputFormatter:
    """Formats and displays article selection results."""
    
    @staticmethod
    def display_selection_results(
        selected_articles: List[Dict[str, Any]],
        batch_id: Optional[str] = None,
        total_processed: int = 0,
        total_relevant: int = 0,
        show_details: bool = True
    ):
        """Display formatted selection results to terminal.
        
        Args:
            selected_articles: List of selected articles with rankings
            batch_id: Batch identifier
            total_processed: Total articles processed
            total_relevant: Total articles that passed first pass
            show_details: Whether to show detailed article information
        """
        # Header
        print("\n" + "="*80)
        print("📰 ARTICLE SELECTION RESULTS")
        print("="*80)
        
        # Summary statistics
        if batch_id:
            print(f"\n🔖 Batch ID: {batch_id}")
        
        print(f"\n📊 Statistics:")
        print(f"   • Total Processed: {total_processed}")
        print(f"   • Passed First Pass: {total_relevant}")
        print(f"   • Final Selected: {len(selected_articles)}")
        print(f"   • Selection Rate: {len(selected_articles)/max(total_processed, 1)*100:.1f}%")
        
        # Selected articles
        print(f"\n🏆 TOP {len(selected_articles)} SELECTED ARTICLES:")
        print("-"*80)
        
        for idx, article in enumerate(selected_articles, 1):
            SelectionOutputFormatter._display_article(idx, article, show_details)
        
        # Footer
        print("\n" + "="*80)
        print("✅ SELECTION COMPLETE")
        print("="*80)
    
    @staticmethod
    def _display_article(rank: int, article: Dict[str, Any], show_details: bool = True):
        """Display a single article with formatting.
        
        Args:
            rank: Article rank
            article: Article data
            show_details: Whether to show detailed information
        """
        # Rank and title
        title = article.get('title', 'Untitled')[:100]
        print(f"\n{rank}. {title}")
        
        # Article metadata
        domain = article.get('domain', 'Unknown')
        url = article.get('url', 'N/A')
        score = article.get('overall_score', article.get('score', 'N/A'))
        
        print(f"   📍 Domain: {domain}")
        # Don't truncate URLs - show full URL
        print(f"   🔗 URL: {url}")
        
        if isinstance(score, (int, float)):
            print(f"   ⭐ Score: {score:.1f}/10")
        else:
            print(f"   ⭐ Score: {score}")
        
        # Show details if requested
        if show_details:
            # Selection reasoning
            if article.get('selection_reasoning'):
                print(f"   💭 Selection Reason: {article['selection_reasoning'][:200]}")
            
            # Content preview
            if article.get('content'):
                content_preview = article['content'][:150].replace('\n', ' ')
                print(f"   📄 Preview: {content_preview}...")
            
            # Tags if available
            if article.get('tags'):
                tags = ', '.join(article['tags'][:5])
                print(f"   🏷️  Tags: {tags}")
    
    @staticmethod
    def display_comparative_ranking(
        ranked_articles: List[Dict[str, Any]],
        comparison_criteria: Optional[Dict[str, Any]] = None
    ):
        """Display comparative ranking results.
        
        Args:
            ranked_articles: Articles with comparative rankings
            comparison_criteria: Criteria used for comparison
        """
        print("\n" + "="*80)
        print("🏅 COMPARATIVE RANKING RESULTS")
        print("="*80)
        
        if comparison_criteria:
            print("\n📋 Ranking Criteria:")
            for key, value in comparison_criteria.items():
                print(f"   • {key}: {value}")
        
        print(f"\n📊 Ranked Articles ({len(ranked_articles)} total):")
        print("-"*80)
        
        for idx, article in enumerate(ranked_articles, 1):
            print(f"\n{idx}. {article.get('title', 'Untitled')[:80]}")
            
            # Show comparative scores if available
            if article.get('relevance_score'):
                print(f"   Relevance: {article['relevance_score']:.1f}")
            if article.get('quality_score'):
                print(f"   Quality: {article['quality_score']:.1f}")
            if article.get('impact_score'):
                print(f"   Impact: {article['impact_score']:.1f}")
            if article.get('overall_score'):
                print(f"   Overall: {article['overall_score']:.1f}")
            
            # Comparison notes
            if article.get('comparison_notes'):
                print(f"   Notes: {article['comparison_notes'][:150]}")
    
    @staticmethod
    def save_selection_report(
        selected_articles: List[Dict[str, Any]],
        output_path: str,
        batch_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save selection results to a formatted report file.
        
        Args:
            selected_articles: Selected articles
            output_path: Path for output file
            batch_id: Batch identifier
            metadata: Additional metadata to include
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "batch_id": batch_id,
            "total_selected": len(selected_articles),
            "articles": selected_articles,
            "metadata": metadata or {}
        }
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📁 Report saved to: {output_path}")
    
    @staticmethod
    def display_processing_summary(
        phase_stats: Dict[str, Any],
        elapsed_time: float
    ):
        """Display processing phase summary.
        
        Args:
            phase_stats: Statistics for each processing phase
            elapsed_time: Total processing time in seconds
        """
        print("\n" + "="*80)
        print("⚙️  PROCESSING SUMMARY")
        print("="*80)
        
        print("\n📈 Phase Statistics:")
        
        # First pass
        if 'first_pass' in phase_stats:
            fp = phase_stats['first_pass']
            print(f"\n   First Pass Filtering:")
            print(f"      • Processed: {fp.get('total', 0)}")
            print(f"      • Relevant: {fp.get('relevant', 0)}")
            print(f"      • Filtered: {fp.get('filtered', 0)}")
            print(f"      • Pass Rate: {fp.get('pass_rate', 0):.1f}%")
        
        # Scoring
        if 'scoring' in phase_stats:
            sc = phase_stats['scoring']
            print(f"\n   Article Scoring:")
            print(f"      • Scored: {sc.get('total', 0)}")
            print(f"      • Avg Score: {sc.get('avg_score', 0):.1f}/10")
            print(f"      • High Quality (>7): {sc.get('high_quality', 0)}")
        
        # Selection
        if 'selection' in phase_stats:
            sel = phase_stats['selection']
            print(f"\n   Final Selection:")
            print(f"      • Candidates: {sel.get('candidates', 0)}")
            print(f"      • Selected: {sel.get('selected', 0)}")
            print(f"      • Avg Selected Score: {sel.get('avg_selected_score', 0):.1f}/10")
        
        # Timing
        print(f"\n⏱️  Processing Time: {elapsed_time:.2f} seconds")
        
        if elapsed_time > 0:
            articles_per_sec = phase_stats.get('first_pass', {}).get('total', 0) / elapsed_time
            print(f"   • Throughput: {articles_per_sec:.1f} articles/second")
        
        print("\n" + "="*80)