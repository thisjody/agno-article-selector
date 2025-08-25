#!/usr/bin/env python3
"""Example usage of the Article Selector agents."""

import json
from datetime import datetime
from projects.article_selector.models import Article
from projects.article_selector.agents import (
    get_first_pass_agent,
    get_scoring_agent,
    get_selector_agent,
)


def main():
    """Demonstrate the article selection pipeline."""
    
    # Sample articles for testing
    articles = [
        Article(
            title="Critical Vulnerability Found in OpenSSL 3.0",
            content="A critical vulnerability has been discovered in OpenSSL 3.0 that could allow remote code execution. The vulnerability affects all versions prior to 3.0.12. The OpenSSL team has released an emergency patch.",
            url="https://www.openssl.org/news/",
            domain="openssl.org",
            published_date=datetime.now(),
        ),
        Article(
            title="Microsoft Patches Windows Zero-Day",
            content="Microsoft has released an emergency patch for a zero-day vulnerability in Windows 11. The vulnerability was being actively exploited in the wild.",
            url="https://www.microsoft.com/",
            domain="microsoft.com",
            published_date=datetime.now(),
        ),
        Article(
            title="New Supply Chain Attack on npm Packages",
            content="Security researchers discovered a sophisticated supply chain attack targeting popular npm packages. The attack affected packages with millions of weekly downloads including several React components.",
            url="https://snyk.io/blog/",
            domain="snyk.io",
            published_date=datetime.now(),
        ),
    ]
    
    print("=" * 60)
    print("ARTICLE SELECTOR - EXAMPLE USAGE")
    print("=" * 60)
    
    # Step 1: First Pass Filtering
    print("\n📋 STEP 1: First Pass Filtering")
    print("-" * 40)
    
    first_pass = get_first_pass_agent(debug_mode=False)
    filtered_articles = []
    
    for article in articles:
        print(f"\nEvaluating: {article.title}")
        
        message = f"""Evaluate this article:
Title: {article.title}
Content: {article.content}
Domain: {article.domain}"""
        
        result = first_pass.run(message)
        print(f"  Status: {result.content}")
        
        # Parse result (in real implementation, use structured output)
        if "Relevant" in str(result.content):
            filtered_articles.append(article)
            print(f"  ✅ Passed first pass filter")
        else:
            print(f"  ❌ Filtered out")
    
    # Step 2: Scoring
    print("\n📊 STEP 2: Scoring Relevant Articles")
    print("-" * 40)
    
    if filtered_articles:
        scoring = get_scoring_agent(debug_mode=False)
        scored_articles = []
        
        for article in filtered_articles:
            print(f"\nScoring: {article.title}")
            
            message = f"""Score this article that passed first-pass filtering:
Title: {article.title}
Content: {article.content}
Domain: {article.domain}
First-pass reasoning: Passed initial relevance check for open source security."""
            
            result = scoring.run(message)
            print(f"  Score: {result.content}")
            scored_articles.append({
                "article": article,
                "score": result.content
            })
    
    # Step 3: Final Selection
    print("\n🏆 STEP 3: Final Selection")
    print("-" * 40)
    
    if scored_articles:
        selector = get_selector_agent(debug_mode=False)
        
        articles_summary = "\n".join([
            f"- {item['article'].title} (Domain: {item['article'].domain})"
            for item in scored_articles
        ])
        
        message = f"""Select and rank the top articles from these scored candidates:

{articles_summary}

Select the best articles for an open source security newsletter."""
        
        result = selector.run(message)
        print(f"\nFinal Selection:\n{result.content}")
    
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Note: This requires AWS credentials to be configured for Claude
    print("\nNote: Make sure AWS credentials are configured for Claude (Bedrock)")
    print("Export: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION\n")
    
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTip: Make sure you have:")
        print("1. Installed dependencies: ./scripts/dev_setup.sh")
        print("2. Configured AWS credentials for Claude")
        print("3. Activated the virtual environment: source .venv/bin/activate")