#!/usr/bin/env python3
"""Demo script showing the complete article selection workflow with formatted output."""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__)))

from projects.article_selector.models import Article
from projects.article_selector.agents.tracked_agents import (
    get_tracked_first_pass_agent,
    get_tracked_scoring_agent,
    get_tracked_selector_agent,
)
from core.output_formatter import SelectionOutputFormatter
import time


def main():
    """Run complete article selection workflow with formatted output."""
    
    print("\n" + "="*80)
    print("🚀 ARTICLE SELECTION WORKFLOW DEMO")
    print("="*80)
    print("\nThis demo shows the complete article selection pipeline")
    print("with formatted output similar to the ADK version.\n")
    
    start_time = time.time()
    
    # Sample articles for demo
    test_articles = [
        Article(
            title="Critical Zero-Day Vulnerability Discovered in Linux Kernel",
            content="A critical zero-day vulnerability has been discovered in the Linux kernel affecting all major distributions. The vulnerability, tracked as CVE-2024-0001, allows local privilege escalation and could potentially lead to remote code execution. The Linux security team has released emergency patches.",
            domain="kernel.org",
            url="https://kernel.org/security/cve-2024-0001"
        ),
        Article(
            title="Microsoft Releases Emergency Windows 11 Security Update",
            content="Microsoft has released an out-of-band security update for Windows 11 addressing multiple critical vulnerabilities. The update fixes issues in Windows Defender and the Windows kernel.",
            domain="microsoft.com",
            url="https://microsoft.com/security/updates"
        ),
        Article(
            title="Supply Chain Attack Targets Popular npm Packages",
            content="Security researchers have uncovered a sophisticated supply chain attack targeting multiple popular npm packages. The attack involves malicious code injection that can steal environment variables and authentication tokens. Over 10 million weekly downloads were potentially affected.",
            domain="snyk.io",
            url="https://snyk.io/blog/npm-supply-chain-attack"
        ),
        Article(
            title="OpenSSL Releases Critical Security Patch",
            content="The OpenSSL team has released version 3.0.12 addressing a critical vulnerability that could allow remote attackers to cause a denial of service or potentially execute arbitrary code. All users of OpenSSL 3.0.x are urged to update immediately.",
            domain="openssl.org",
            url="https://www.openssl.org/news/secadv/"
        ),
        Article(
            title="New Ransomware Campaign Targets Healthcare Sector",
            content="A new ransomware campaign dubbed 'MedLock' is actively targeting healthcare organizations worldwide. The campaign uses sophisticated phishing emails and exploits known vulnerabilities in medical software.",
            domain="bleepingcomputer.com",
            url="https://bleepingcomputer.com/news/security/"
        ),
    ]
    
    # Initialize agents
    print("🤖 Initializing agents...")
    first_pass_agent = get_tracked_first_pass_agent(debug_mode=False)
    scoring_agent = get_tracked_scoring_agent(debug_mode=False)
    selector_agent = get_tracked_selector_agent(debug_mode=False)
    
    # Phase 1: First Pass Filtering
    print("\n" + "="*60)
    print("📋 PHASE 1: First Pass Filtering")
    print("="*60)
    
    relevant_articles = []
    phase_stats = {'first_pass': {'total': len(test_articles), 'relevant': 0, 'filtered': 0}}
    
    for idx, article in enumerate(test_articles, 1):
        print(f"\n[{idx}/{len(test_articles)}] {article.title[:60]}...")
        
        response = first_pass_agent.process_article(
            article=article,
            article_id=idx,
            save_responses=True
        )
        
        status = response['status']
        print(f"    → Status: {status}")
        
        if status == "Relevant":
            relevant_articles.append({
                'id': idx,
                'article': article,
                'first_pass_reasoning': str(response['result'].content)[:200]
            })
            phase_stats['first_pass']['relevant'] += 1
        else:
            phase_stats['first_pass']['filtered'] += 1
    
    phase_stats['first_pass']['pass_rate'] = (
        phase_stats['first_pass']['relevant'] / phase_stats['first_pass']['total'] * 100
    )
    
    print(f"\n✅ First pass complete: {len(relevant_articles)}/{len(test_articles)} articles passed")
    
    if not relevant_articles:
        print("\n❌ No articles passed first pass filtering. Exiting.")
        return
    
    # Phase 2: Scoring
    print("\n" + "="*60)
    print("📊 PHASE 2: Article Scoring")
    print("="*60)
    
    scored_articles = []
    
    for item in relevant_articles:
        article = item['article']
        print(f"\nScoring: {article.title[:60]}...")
        
        response = scoring_agent.score_article(
            article=article,
            first_pass_reasoning=item['first_pass_reasoning'],
            article_id=item['id'],
            save_responses=True
        )
        
        # For demo, use placeholder scores
        score = 7.5 + (item['id'] % 3)  # Vary scores for demo
        print(f"    → Score: {score:.1f}/10")
        
        scored_articles.append({
            'id': item['id'],
            'title': article.title,
            'domain': article.domain,
            'url': article.url,
            'content': article.content,
            'overall_score': score,
            'first_pass_reasoning': item['first_pass_reasoning']
        })
    
    # Sort by score
    scored_articles.sort(key=lambda x: x['overall_score'], reverse=True)
    
    phase_stats['scoring'] = {
        'total': len(scored_articles),
        'avg_score': sum(a['overall_score'] for a in scored_articles) / len(scored_articles),
        'high_quality': len([a for a in scored_articles if a['overall_score'] > 7])
    }
    
    # Phase 3: Final Selection
    print("\n" + "="*60)
    print("🎯 PHASE 3: Final Selection")
    print("="*60)
    
    max_articles = 3
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    response = selector_agent.select_articles(
        scored_articles=scored_articles,
        max_articles=max_articles,
        batch_id=batch_id,
        save_responses=True
    )
    
    # Prepare final selections
    selected_articles = []
    for idx, article in enumerate(scored_articles[:max_articles], 1):
        selected_articles.append({
            'rank': idx,
            'title': article['title'],
            'domain': article['domain'],
            'url': article['url'],
            'content': article['content'][:300],
            'overall_score': article['overall_score'],
            'selection_reasoning': f"Selected as #{idx} based on high relevance to open source security and quality score",
            'tags': ['security', 'open-source', 'vulnerability']
        })
    
    phase_stats['selection'] = {
        'candidates': len(scored_articles),
        'selected': len(selected_articles),
        'avg_selected_score': sum(a['overall_score'] for a in selected_articles) / len(selected_articles)
    }
    
    # Calculate total time
    elapsed_time = time.time() - start_time
    
    # Display final results (like ADK version)
    SelectionOutputFormatter.display_selection_results(
        selected_articles=selected_articles,
        batch_id=batch_id,
        total_processed=len(test_articles),
        total_relevant=len(relevant_articles),
        show_details=True
    )
    
    # Display processing summary
    SelectionOutputFormatter.display_processing_summary(
        phase_stats=phase_stats,
        elapsed_time=elapsed_time
    )
    
    print("\n💡 Note: This demo uses simplified scoring. In production,")
    print("   the agents would provide detailed analysis and scores.")
    print("\n📁 Check output/responses/ for saved agent interactions.")


if __name__ == "__main__":
    print("\n⚠️  Note: This demo requires AWS credentials for Claude.")
    print("   Make sure you have configured your .env file.\n")
    
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTip: Make sure you have:")
        print("1. Created and configured .env file")
        print("2. Set AWS credentials for Claude")
        print("3. Installed dependencies with: ./scripts/dev_setup.sh")
        sys.exit(1)