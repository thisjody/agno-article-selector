"""
Async-enabled tracked agents with error handling and retry logic.
"""

import asyncio
import time
import random
from typing import Optional, Dict, Any, List
from pathlib import Path

from agno.models.message import Message

from projects.article_selector.agents import (
    get_first_pass_agent,
    get_scoring_agent,
    get_selector_agent,
    get_comparative_ranker_agent,
)
from projects.article_selector.models import Article
from core.response_tracker import ResponseTracker
from core.settings import settings


class AsyncRetryConfig:
    """Configuration for async retry logic."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    timeout: float = 30.0  # Timeout for each attempt


async def async_retry(
    func,
    *args,
    config: AsyncRetryConfig = AsyncRetryConfig(),
    **kwargs
):
    """Execute a function with async retry logic."""
    last_exception = None
    delay = config.initial_delay
    
    for attempt in range(config.max_retries):
        try:
            # Add timeout to the function call
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=config.timeout
            )
        except asyncio.TimeoutError as e:
            last_exception = e
            print(f"⏱️ Attempt {attempt + 1} timed out after {config.timeout}s")
        except Exception as e:
            last_exception = e
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
        
        if attempt < config.max_retries - 1:
            if config.jitter:
                actual_delay = delay * (0.5 + random.random())
            else:
                actual_delay = delay
            
            print(f"⏳ Retrying in {actual_delay:.1f} seconds...")
            await asyncio.sleep(actual_delay)
            
            delay = min(delay * config.exponential_base, config.max_delay)
    
    raise last_exception


class AsyncTrackedFirstPassAgent:
    """Async version of first pass agent with tracking and error handling."""
    
    def __init__(self, debug_mode: bool = False):
        self.agent = get_first_pass_agent(debug_mode=debug_mode)
        self.tracker = ResponseTracker(Path(settings.agent_response_output_dir))
        self.retry_config = AsyncRetryConfig()
    
    async def process_article_async(
        self,
        article: Article,
        article_id: Optional[int] = None,
        save_responses: bool = True,
    ) -> Dict[str, Any]:
        """Process an article asynchronously with retry logic."""
        
        async def _process():
            # Prepare input
            input_text = (
                f"Article Title: {article.title}\n"
                f"Source Domain: {article.domain or 'unknown'}\n"
                f"Article Content: {article.content[:1000]}"
            )
            
            input_data = {
                "title": article.title,
                "domain": article.domain,
                "content": article.content[:1000],
            }
            
            # Run agent (convert to async)
            loop = asyncio.get_event_loop()
            messages = [Message(role="user", content=input_text)]
            
            result = await loop.run_in_executor(
                None,
                self.agent.run,
                messages
            )
            
            # Parse result
            result_text = str(result.content) if hasattr(result, 'content') else str(result)
            
            # Parse ADK format
            if "first_pass_result:" in result_text:
                parts = result_text.split("first_pass_result:", 1)[1].strip()
                if parts.startswith("Relevant"):
                    status = "Relevant"
                    reasoning = parts[8:].strip().lstrip('.').strip()
                elif parts.startswith("Irrelevant"):
                    status = "Irrelevant"
                    reasoning = parts[10:].strip().lstrip('.').strip()
                else:
                    status = "Relevant" if "Relevant" in result_text else "Irrelevant"
                    reasoning = result_text
            else:
                status = "Relevant" if "Relevant" in result_text and "Irrelevant" not in result_text.split(".")[0] else "Irrelevant"
                reasoning = result_text
            
            # Save if requested
            if save_responses:
                await loop.run_in_executor(
                    None,
                    self.tracker.save_agent_interaction,
                    "first_pass",
                    article_id or article.title[:50],
                    input_data,
                    result_text
                )
            
            return {
                "status": status,
                "result": result,
                "reasoning": reasoning,
                "article": article,
                "article_id": article_id,
            }
        
        # Execute with retry
        return await async_retry(_process, config=self.retry_config)


class AsyncTrackedScoringAgent:
    """Async version of scoring agent with tracking and error handling."""
    
    def __init__(self, debug_mode: bool = False):
        self.agent = get_scoring_agent(debug_mode=debug_mode)
        self.tracker = ResponseTracker(Path(settings.agent_response_output_dir))
        self.retry_config = AsyncRetryConfig()
    
    async def score_article_async(
        self,
        article: Article,
        first_pass_reasoning: str = "",
        article_id: Optional[int] = None,
        save_responses: bool = True,
    ) -> Dict[str, Any]:
        """Score an article asynchronously with retry logic."""
        
        async def _score():
            # Prepare input
            input_text = (
                f"Article Title: {article.title}\n"
                f"Source Domain: {article.domain or 'unknown'}\n"
                f"URL: {article.url or 'N/A'}\n"
                f"Summary: {article.content[:500]}\n"
                f"First Pass Assessment: {first_pass_reasoning}"
            )
            
            input_data = {
                "title": article.title,
                "domain": article.domain,
                "url": article.url,
                "summary": article.content[:500],
                "first_pass_reasoning": first_pass_reasoning,
            }
            
            # Run agent
            loop = asyncio.get_event_loop()
            messages = [Message(role="user", content=input_text)]
            
            result = await loop.run_in_executor(
                None,
                self.agent.run,
                messages
            )
            
            # Parse result
            result_text = str(result.content) if hasattr(result, 'content') else str(result)
            
            # Extract score
            import re
            score = 7.5  # Default
            reasoning = result_text
            
            score_match = re.search(r'Score:\s*(\d+(?:\.\d+)?)', result_text)
            if score_match:
                score = float(score_match.group(1))
            
            reason_match = re.search(r'Reason:\s*(.+)', result_text, re.MULTILINE | re.DOTALL)
            if reason_match:
                reasoning = reason_match.group(1).strip()
            
            # Save if requested
            if save_responses:
                await loop.run_in_executor(
                    None,
                    self.tracker.save_agent_interaction,
                    "scoring",
                    article_id or article.title[:50],
                    input_data,
                    result_text
                )
            
            return {
                "score": score,
                "reasoning": reasoning,
                "result": result,
                "article": article,
                "article_id": article_id,
            }
        
        # Execute with retry
        return await async_retry(_score, config=self.retry_config)


class AsyncTrackedComparativeRanker:
    """Async version of comparative ranker with tracking and error handling."""
    
    def __init__(self, debug_mode: bool = False):
        self.agent = get_comparative_ranker_agent(debug_mode=debug_mode)
        self.tracker = ResponseTracker(Path(settings.agent_response_output_dir))
        self.retry_config = AsyncRetryConfig()
    
    async def rank_batch_async(
        self,
        articles: List[Dict[str, Any]],
        batch_id: str,
        save_responses: bool = True,
    ) -> List[Dict[str, Any]]:
        """Rank a batch of articles asynchronously."""
        
        async def _rank():
            # Prepare batch content
            batch_text = "\n\n".join([
                f"- Title: {a['title']}\n"
                f"  Score: {a.get('overall_score', a.get('score', 0))}\n"
                f"  Domain: {a.get('domain', 'unknown')}\n"
                f"  Rationale: {a.get('scoring_rationale', '')[:200]}"
                for a in articles
            ])
            
            # Run agent
            loop = asyncio.get_event_loop()
            messages = [Message(
                role="user",
                content=f"Rank these {len(articles)} articles comparatively:\n\n{batch_text}"
            )]
            
            result = await loop.run_in_executor(
                None,
                self.agent.run,
                messages
            )
            
            # Parse ranking
            result_text = str(result.content) if hasattr(result, 'content') else str(result)
            
            # Simple ranking extraction (could be improved)
            ranked_articles = []
            for rank, article in enumerate(articles, 1):
                article_copy = article.copy()
                article_copy['rank'] = rank
                article_copy['ranking_rationale'] = f"Batch rank: {rank}"
                ranked_articles.append(article_copy)
            
            # Save if requested
            if save_responses:
                await loop.run_in_executor(
                    None,
                    self.tracker.save_agent_interaction,
                    "comparative_ranker",
                    batch_id,
                    {"batch": articles},
                    result_text
                )
            
            return ranked_articles
        
        # Execute with retry
        return await async_retry(_rank, config=self.retry_config)


class AsyncTrackedSelectorAgent:
    """Async version of selector agent with tracking and error handling."""
    
    def __init__(self, debug_mode: bool = False):
        self.agent = get_selector_agent(debug_mode=debug_mode)
        self.tracker = ResponseTracker(Path(settings.agent_response_output_dir))
        self.retry_config = AsyncRetryConfig()
    
    async def select_articles_async(
        self,
        scored_articles: List[Dict[str, Any]],
        max_articles: int = 10,
        batch_id: Optional[str] = None,
        save_responses: bool = True,
    ) -> Dict[str, Any]:
        """Select final articles asynchronously."""
        
        async def _select():
            # Format articles for selection
            articles_text = "\n\n".join([
                f"{idx}. {a['title']}\n"
                f"   Score: {a.get('overall_score', 0):.1f}\n"
                f"   Domain: {a.get('domain', 'unknown')}\n"
                f"   Rank: {a.get('comparative_avg_rank', idx):.1f}"
                for idx, a in enumerate(scored_articles[:max_articles * 2], 1)
            ])
            
            input_text = (
                f"Select the top {max_articles} articles with good source diversity "
                f"from these {len(scored_articles)} candidates:\n\n{articles_text}"
            )
            
            # Run agent
            loop = asyncio.get_event_loop()
            messages = [Message(role="user", content=input_text)]
            
            result = await loop.run_in_executor(
                None,
                self.agent.run,
                messages
            )
            
            # For now, just take top N
            selected = scored_articles[:max_articles]
            
            # Save if requested
            if save_responses:
                await loop.run_in_executor(
                    None,
                    self.tracker.save_agent_interaction,
                    "selector",
                    batch_id or "selection",
                    {"candidates": len(scored_articles), "max_articles": max_articles},
                    str(result.content) if hasattr(result, 'content') else str(result)
                )
            
            return {
                "selected": selected,
                "result": result,
            }
        
        # Execute with retry
        return await async_retry(_select, config=self.retry_config)


# Factory functions for async agents
def get_async_tracked_first_pass_agent(debug_mode: bool = False) -> AsyncTrackedFirstPassAgent:
    """Create async tracked first pass agent."""
    return AsyncTrackedFirstPassAgent(debug_mode=debug_mode)


def get_async_tracked_scoring_agent(debug_mode: bool = False) -> AsyncTrackedScoringAgent:
    """Create async tracked scoring agent."""
    return AsyncTrackedScoringAgent(debug_mode=debug_mode)


def get_async_tracked_comparative_ranker(debug_mode: bool = False) -> AsyncTrackedComparativeRanker:
    """Create async tracked comparative ranker."""
    return AsyncTrackedComparativeRanker(debug_mode=debug_mode)


def get_async_tracked_selector_agent(debug_mode: bool = False) -> AsyncTrackedSelectorAgent:
    """Create async tracked selector agent."""
    return AsyncTrackedSelectorAgent(debug_mode=debug_mode)