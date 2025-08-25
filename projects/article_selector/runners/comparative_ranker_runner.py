"""Comparative Ranker Runner - Handles batch processing and rank accumulation."""

import random
import json
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from projects.article_selector.agents.comparative_ranker_agent import (
    get_comparative_ranker_agent,
    ComparativeRankingResult,
)
from core.response_tracker import ResponseTracker


def split_into_batches(items: List[dict], batch_size: int) -> List[List[dict]]:
    """Split items into batches of specified size."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def run_comparative_ranking(
    articles: List[Dict[str, Any]],
    output_dir: Path,
    pipeline_run_id: str,
    score_threshold: float = 6.0,
    top_n: int = 100,
    batch_size: int = 10,
    shuffle_runs: int = 3,
    recursive_top_k: int = 50,
    debug_mode: bool = False,
) -> List[Dict[str, Any]]:
    """
    Run comparative ranking on scored articles.
    
    This implements the ADK's sophisticated ranking algorithm:
    1. Filter articles by score threshold
    2. Take top N candidates
    3. Split into batches
    4. Run multiple shuffle passes
    5. Accumulate rankings across passes
    6. Return final ranked list
    
    Args:
        articles: List of scored articles
        output_dir: Directory for saving outputs
        pipeline_run_id: Unique ID for this pipeline run
        score_threshold: Minimum score to consider (default 6.0)
        top_n: Maximum candidates to consider (default 100)
        batch_size: Articles per batch for comparison (default 10)
        shuffle_runs: Number of shuffle passes (default 3)
        recursive_top_k: Final number to return (default 50)
        debug_mode: Enable debug output
        
    Returns:
        List of top-ranked articles with comparative rankings
    """
    
    print(f"\n{'='*60}")
    print("📊 COMPARATIVE RANKING")
    print(f"{'='*60}")
    
    # Step 1: Filter and truncate
    filtered = [a for a in articles if a.get("overall_score", a.get("score", 0)) >= score_threshold]
    filtered.sort(key=lambda x: x.get("overall_score", x.get("score", 0)), reverse=True)
    candidates = filtered[:top_n]
    
    print(f"📋 Candidates: {len(candidates)} articles (threshold: {score_threshold}, top_n: {top_n})")
    
    if not candidates:
        print("❌ No candidates meet the threshold for comparative ranking")
        return []
    
    # Step 2: Create batches
    batches = split_into_batches(candidates, batch_size)
    print(f"🎲 Batches: {len(batches)} batches of up to {batch_size} articles")
    print(f"🔄 Shuffle runs: {shuffle_runs}")
    
    # Initialize accumulators for ranks and rationales
    rank_accumulator = defaultdict(list)
    rationale_map = defaultdict(list)
    
    # Initialize response tracker
    tracker = ResponseTracker(output_dir)
    
    # Create comparative ranker agent
    ranker_agent = get_comparative_ranker_agent(debug_mode=debug_mode)
    
    # Step 3: Multiple shuffle passes for robustness
    for pass_num in range(shuffle_runs):
        print(f"\n🔁 Shuffle Pass {pass_num + 1}/{shuffle_runs}")
        
        # Shuffle batches for variety across passes
        shuffled_batches = batches.copy()
        random.shuffle(shuffled_batches)
        
        for batch_idx, batch in enumerate(shuffled_batches):
            # Shuffle items within batch
            shuffled_batch = batch.copy()
            random.shuffle(shuffled_batch)
            
            print(f"  📦 Processing batch {batch_idx + 1}/{len(shuffled_batches)} ({len(shuffled_batch)} articles)")
            
            # Prepare batch content for agent
            batch_content = []
            for article in shuffled_batch:
                batch_content.append({
                    "title": article.get("title", "Untitled"),
                    "score": article.get("overall_score", article.get("score", 0)),
                    "domain": article.get("domain", "unknown"),
                    "url": article.get("url", ""),
                    "rationale": article.get("scoring_rationale", article.get("rationale", "")),
                    "content": article.get("content", "")[:500],  # Truncate for context
                })
            
            # Format batch for agent
            batch_text = "\n\n".join([
                f"- Title: {a['title']}\n"
                f"  Score: {a['score']}\n"
                f"  Domain: {a['domain']}\n"
                f"  URL: {a['url']}\n"
                f"  Rationale: {a['rationale']}\n"
                f"  Content: {a['content']}"
                for a in batch_content
            ])
            
            try:
                # Run comparative ranking on this batch
                # Use Message object for proper Agno format
                from agno.models.message import Message
                messages = [Message(
                    role="user",
                    content=f"Rank these {len(batch_content)} articles comparatively:\n\n{batch_text}"
                )]
                result = ranker_agent.run(messages=messages)
                
                # Save agent interaction
                tracker.save_agent_interaction(
                    agent_type="comparative_ranker",
                    article_id=f"batch_{pass_num}_{batch_idx}",
                    input_data={"batch": batch_content, "pass": pass_num, "batch_idx": batch_idx},
                    output_data=result.content if hasattr(result, 'content') else str(result),
                )
                
                # Parse result - the agent returns a RunResponse with content
                ranking_result = None
                
                if hasattr(result, 'content'):
                    # Check if content is already a ComparativeRankingResult
                    if isinstance(result.content, ComparativeRankingResult):
                        ranking_result = result.content
                    elif isinstance(result.content, dict):
                        # Content is a dict, convert to model
                        try:
                            ranking_result = ComparativeRankingResult(**result.content)
                        except Exception as e:
                            print(f"    ⚠️ Failed to parse dict result for batch {batch_idx + 1}: {e}")
                            if debug_mode:
                                print(f"    Result content: {result.content}")
                    elif isinstance(result.content, str):
                        # Content is a JSON string
                        try:
                            parsed = json.loads(result.content)
                            ranking_result = ComparativeRankingResult(**parsed)
                        except Exception as e:
                            print(f"    ⚠️ Failed to parse JSON result for batch {batch_idx + 1}: {e}")
                            if debug_mode:
                                print(f"    Result content: {result.content}")
                    else:
                        # Try to access ranked_articles directly
                        if hasattr(result.content, 'ranked_articles'):
                            ranking_result = result.content
                        else:
                            print(f"    ⚠️ Unexpected content type for batch {batch_idx + 1}: {type(result.content)}")
                            if debug_mode:
                                print(f"    Result content: {result.content}")
                
                if not ranking_result:
                    print(f"    ⚠️ Could not extract ranking result for batch {batch_idx + 1}")
                    # Fallback: use original scores as ranks
                    print(f"    📊 Using score-based ranking as fallback")
                    sorted_batch = sorted(shuffled_batch, key=lambda x: x.get('overall_score', x.get('score', 0)), reverse=True)
                    for rank, article in enumerate(sorted_batch, 1):
                        title = article.get('title', 'Untitled')
                        rank_accumulator[title].append(rank)
                        rationale_map[title].append(f"Score-based rank: {article.get('overall_score', article.get('score', 0))}")
                    continue
                
                # Accumulate rankings
                for ranked_article in ranking_result.ranked_articles:
                    title = ranked_article.original_title
                    rank = ranked_article.refined_rank
                    rationale = ranked_article.comparative_rationale
                    
                    rank_accumulator[title].append(rank)
                    rationale_map[title].append(rationale)
                    
                print(f"    ✅ Ranked {len(ranking_result.ranked_articles)} articles")
                
            except Exception as e:
                print(f"    ❌ Error ranking batch {batch_idx + 1}: {e}")
                if debug_mode:
                    import traceback
                    traceback.print_exc()
    
    # Step 4: Aggregate rankings and compute final scores
    print(f"\n📈 Aggregating rankings from {shuffle_runs} passes...")
    
    ranked_results = []
    for article in candidates:
        title = article.get("title", "Untitled")
        
        if title not in rank_accumulator:
            print(f"⚠️ Article '{title[:50]}...' not found in rankings, skipping")
            continue
        
        # Calculate average rank across all passes
        ranks = rank_accumulator[title]
        avg_rank = sum(ranks) / len(ranks)
        
        # Compile rationales
        rationales = rationale_map[title]
        
        # Add to results with comparative ranking info
        ranked_article = article.copy()
        ranked_article.update({
            "comparative_avg_rank": avg_rank,
            "comparative_ranks": ranks,
            "comparative_rationales": rationales,
            "final_score": article.get("overall_score", article.get("score", 0)) - (avg_rank * 0.1),  # Adjust score by rank
        })
        ranked_results.append(ranked_article)
    
    # Sort by average comparative rank (lower is better)
    ranked_results.sort(key=lambda x: x["comparative_avg_rank"])
    
    # Take top K
    final_results = ranked_results[:recursive_top_k]
    
    print(f"✅ Final ranking complete: {len(final_results)} articles")
    
    # Display top 10 for verification
    print("\n🏆 Top 10 Comparative Rankings:")
    for i, article in enumerate(final_results[:10], 1):
        print(f"{i}. {article['title'][:60]}...")
        print(f"   Domain: {article.get('domain', 'unknown')}")
        print(f"   Avg Rank: {article['comparative_avg_rank']:.2f}")
        print(f"   Original Score: {article.get('overall_score', article.get('score', 0)):.1f}")
    
    return final_results


# Alias for backward compatibility
run_comparative_ranking_sync = run_comparative_ranking