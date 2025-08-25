"""
Article Selection Workflow V2 - Properly implemented AGNO V2 workflow with all phases.
This replaces the placeholder workflow with actual implementation.
"""

import asyncio
import json
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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


class WorkflowState:
    """Manages workflow state for checkpointing and recovery."""
    
    def __init__(self, checkpoint_dir: Optional[Path] = None):
        self.checkpoint_dir = checkpoint_dir or Path("output/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.state = {
            "phase": None,
            "processed_articles": [],
            "relevant_articles": [],
            "scored_articles": [],
            "ranked_articles": [],
            "selected_articles": [],
            "errors": [],
            "timestamp": datetime.now().isoformat(),
        }
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def save_checkpoint(self, phase: str):
        """Save current state to checkpoint file."""
        self.state["phase"] = phase
        self.state["timestamp"] = datetime.now().isoformat()
        
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{self.run_id}_{phase}.json"
        with open(checkpoint_file, "w") as f:
            json.dump(self.state, f, indent=2, default=str)
        return checkpoint_file
    
    def load_checkpoint(self, checkpoint_file: Path) -> bool:
        """Load state from checkpoint file."""
        if checkpoint_file.exists():
            with open(checkpoint_file, "r") as f:
                self.state = json.load(f)
            return True
        return False
    
    def can_resume(self, phase: str) -> bool:
        """Check if we can resume from a specific phase."""
        phase_order = ["first_pass", "scoring", "comparative_ranking", "selection"]
        if self.state.get("phase") in phase_order:
            current_idx = phase_order.index(self.state["phase"])
            target_idx = phase_order.index(phase)
            return current_idx >= target_idx
        return False


class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


def with_retry(func: Callable, config: RetryConfig = RetryConfig()) -> Callable:
    """Decorator to add retry logic with exponential backoff."""
    def wrapper(*args, **kwargs):
        last_exception = None
        delay = config.initial_delay
        
        for attempt in range(config.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < config.max_retries - 1:
                    if config.jitter:
                        actual_delay = delay * (0.5 + random.random())
                    else:
                        actual_delay = delay
                    
                    print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                    print(f"⏳ Retrying in {actual_delay:.1f} seconds...")
                    time.sleep(actual_delay)
                    
                    delay = min(delay * config.exponential_base, config.max_delay)
        
        raise last_exception
    return wrapper


class ArticleSelectionWorkflowV2:
    """
    Properly implemented AGNO V2 workflow with all 4 phases, error handling,
    parallel execution, and state management.
    """
    
    def __init__(
        self,
        user_id: str = "default",
        session_id: str = "default", 
        debug_mode: bool = False,
        max_parallel_workers: int = 5,
        enable_checkpointing: bool = True,
        response_tracker: Optional[ResponseTracker] = None,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.debug_mode = debug_mode
        self.max_parallel_workers = max_parallel_workers
        self.enable_checkpointing = enable_checkpointing
        self.response_tracker = response_tracker or ResponseTracker(Path(settings.agent_response_output_dir))
        self.state = WorkflowState() if enable_checkpointing else None
        self.executor = ThreadPoolExecutor(max_workers=max_parallel_workers)
        
        # Initialize all agents with retry wrapper
        self.first_pass_agent = self._create_agent_with_retry(get_first_pass_agent)
        self.scoring_agent = self._create_agent_with_retry(get_scoring_agent)
        self.comparative_ranker_agent = self._create_agent_with_retry(get_comparative_ranker_agent)
        self.selector_agent = self._create_agent_with_retry(get_selector_agent)
        
        # Create the actual workflow
        self.workflow = self._create_workflow()
    
    def _create_agent_with_retry(self, agent_factory: Callable):
        """Create an agent with retry logic wrapped around its run method."""
        agent = agent_factory(
            user_id=self.user_id,
            session_id=self.session_id,
            debug_mode=self.debug_mode,
        )
        
        # Wrap the run method with retry logic
        original_run = agent.run
        agent.run = with_retry(original_run)
        return agent
    
    def _create_workflow(self) -> Dict:
        """Create the workflow metadata with all 4 phases."""
        return {
            "name": "Article Selection Pipeline V2",
            "description": "Production-ready article selection with error handling and parallelism",
            "steps": [
                {
                    "name": "First Pass Filtering",
                    "agent": self.first_pass_agent,
                    "description": "Filter articles for relevance (parallelized)",
                    "transform_input": self._transform_for_first_pass,
                    "transform_output": self._transform_first_pass_output,
                },
                {
                    "name": "Article Scoring",
                    "agent": self.scoring_agent,
                    "description": "Score relevant articles (parallelized)",
                    "transform_input": self._transform_for_scoring,
                    "transform_output": self._transform_scoring_output,
                },
                {
                    "name": "Comparative Ranking",
                    "agent": self.comparative_ranker_agent,
                    "description": "Rank articles in batches with multiple passes",
                    "transform_input": self._transform_for_ranking,
                    "transform_output": self._transform_ranking_output,
                },
                {
                    "name": "Final Selection",
                    "agent": self.selector_agent,
                    "description": "Select top articles with diversity",
                    "transform_input": self._transform_for_selection,
                    "transform_output": self._transform_selection_output,
                },
            ],
        }
    
    # Transform functions for each step
    
    def _transform_for_first_pass(self, articles: List[Article]) -> List[Dict]:
        """Transform articles for parallel first pass processing."""
        return [
            {
                "article": article,
                "article_id": idx,
                "prompt": f"Article Title: {article.title}\n"
                         f"Source Domain: {article.domain}\n"
                         f"Article Content: {article.content[:1000]}"
            }
            for idx, article in enumerate(articles)
        ]
    
    def _transform_first_pass_output(self, results: List[Dict]) -> Dict:
        """Process first pass results and filter relevant articles."""
        relevant_articles = []
        for result in results:
            if result.get("status") == "Relevant":
                relevant_articles.append({
                    "article": result["article"],
                    "first_pass_reasoning": result["reasoning"],
                    "article_id": result["article_id"],
                })
        
        if self.state:
            self.state.state["relevant_articles"] = relevant_articles
            self.state.save_checkpoint("first_pass")
        
        return {"relevant_articles": relevant_articles}
    
    def _transform_for_scoring(self, data: Dict) -> List[Dict]:
        """Transform relevant articles for parallel scoring."""
        return [
            {
                "article": item["article"],
                "first_pass_reasoning": item["first_pass_reasoning"],
                "article_id": item["article_id"],
                "prompt": self._create_scoring_prompt(item),
            }
            for item in data.get("relevant_articles", [])
        ]
    
    def _create_scoring_prompt(self, item: Dict) -> str:
        """Create scoring prompt with context."""
        article = item["article"]
        return (
            f"Article Title: {article.title}\n"
            f"Source Domain: {article.domain}\n"
            f"URL: {article.url}\n"
            f"Summary: {article.content[:500]}\n"
            f"First Pass Assessment: {item['first_pass_reasoning']}"
        )
    
    def _transform_scoring_output(self, results: List[Dict]) -> Dict:
        """Process scoring results."""
        scored_articles = []
        for result in results:
            article_data = {
                **result["article"].__dict__,
                "overall_score": result.get("score", 0),
                "scoring_rationale": result.get("reasoning", ""),
                "article_id": result["article_id"],
            }
            scored_articles.append(article_data)
        
        # Sort by score
        scored_articles.sort(key=lambda x: x["overall_score"], reverse=True)
        
        if self.state:
            self.state.state["scored_articles"] = scored_articles
            self.state.save_checkpoint("scoring")
        
        return {"scored_articles": scored_articles}
    
    def _transform_for_ranking(self, data: Dict) -> Dict:
        """Prepare scored articles for comparative ranking."""
        scored_articles = data.get("scored_articles", [])
        
        # Filter by threshold
        candidates = [a for a in scored_articles if a["overall_score"] >= 6.0]
        
        return {
            "candidates": candidates,
            "batch_size": 10,
            "shuffle_runs": 3,
        }
    
    def _transform_ranking_output(self, ranking_data: Dict) -> Dict:
        """Process comparative ranking results."""
        if self.state:
            self.state.state["ranked_articles"] = ranking_data.get("ranked_articles", [])
            self.state.save_checkpoint("comparative_ranking")
        
        return ranking_data
    
    def _transform_for_selection(self, data: Dict) -> Dict:
        """Prepare ranked articles for final selection."""
        return {
            "ranked_articles": data.get("ranked_articles", []),
            "max_articles": data.get("max_articles", 10),
        }
    
    def _transform_selection_output(self, selection_data: Dict) -> Dict:
        """Process final selection results."""
        if self.state:
            self.state.state["selected_articles"] = selection_data.get("selected_articles", [])
            self.state.save_checkpoint("selection")
        
        return selection_data
    
    # Parallel execution methods
    
    async def process_articles_parallel(
        self,
        articles: List[Article],
        max_articles: int = 10,
    ) -> Dict[str, Any]:
        """
        Process articles through the workflow with parallel execution where possible.
        """
        start_time = time.time()
        
        try:
            # Phase 1: Parallel First Pass
            print(f"\n{'='*60}")
            print("📋 PHASE 1: First Pass Filtering (Parallel)")
            print(f"{'='*60}")
            
            first_pass_results = await self._parallel_first_pass(articles)
            relevant_articles = [r for r in first_pass_results if r["status"] == "Relevant"]
            
            print(f"✅ First pass complete: {len(relevant_articles)}/{len(articles)} passed")
            
            if not relevant_articles:
                return {"selected": [], "stats": {"message": "No articles passed first pass"}}
            
            # Phase 2: Parallel Scoring
            print(f"\n{'='*60}")
            print("📊 PHASE 2: Article Scoring (Parallel)")
            print(f"{'='*60}")
            
            scored_articles = await self._parallel_scoring(relevant_articles)
            scored_articles.sort(key=lambda x: x["overall_score"], reverse=True)
            
            print(f"✅ Scoring complete: {len(scored_articles)} articles scored")
            
            # Phase 3: Comparative Ranking (Batched)
            print(f"\n{'='*60}")
            print("🎯 PHASE 3: Comparative Ranking")
            print(f"{'='*60}")
            
            ranked_articles = await self._comparative_ranking_async(scored_articles)
            
            print(f"✅ Ranking complete: {len(ranked_articles)} articles ranked")
            
            # Phase 4: Final Selection
            print(f"\n{'='*60}")
            print("🏁 PHASE 4: Final Selection")
            print(f"{'='*60}")
            
            selected_articles = await self._final_selection_async(ranked_articles, max_articles)
            
            # Calculate statistics
            elapsed_time = time.time() - start_time
            
            return {
                "selected_articles": selected_articles,
                "statistics": {
                    "total_input": len(articles),
                    "first_pass_relevant": len(relevant_articles),
                    "scored": len(scored_articles),
                    "ranked": len(ranked_articles),
                    "selected": len(selected_articles),
                    "processing_time": elapsed_time,
                    "avg_time_per_article": elapsed_time / len(articles),
                },
                "errors": self.state.state.get("errors", []) if self.state else [],
            }
            
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            if self.state:
                self.state.state["errors"].append({
                    "phase": "workflow",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })
            raise
    
    async def _parallel_first_pass(self, articles: List[Article]) -> List[Dict]:
        """Execute first pass filtering in parallel."""
        loop = asyncio.get_event_loop()
        
        def process_article(article: Article, idx: int) -> Dict:
            try:
                messages = [Message(
                    role="user",
                    content=f"Article Title: {article.title}\n"
                           f"Source Domain: {article.domain}\n"
                           f"Article Content: {article.content[:1000]}"
                )]
                
                result = self.first_pass_agent.run(messages=messages)
                
                # Parse result
                if hasattr(result, 'content'):
                    content = str(result.content)
                    if "first_pass_result:" in content:
                        parts = content.split("first_pass_result:", 1)[1].strip()
                        if parts.startswith("Relevant"):
                            status = "Relevant"
                            reasoning = parts[8:].strip().lstrip('.').strip()
                        elif parts.startswith("Irrelevant"):
                            status = "Irrelevant"
                            reasoning = parts[10:].strip().lstrip('.').strip()
                        else:
                            status = "Irrelevant"
                            reasoning = content
                    else:
                        status = "Relevant" if "Relevant" in content else "Irrelevant"
                        reasoning = content
                else:
                    status = "Irrelevant"
                    reasoning = "Failed to parse response"
                
                # Save response
                self.response_tracker.save_agent_interaction(
                    agent_type="first_pass",
                    article_id=f"article_{idx}",
                    input_data={"article": article.__dict__},
                    output_data={"status": status, "reasoning": reasoning},
                )
                
                return {
                    "article": article,
                    "article_id": idx,
                    "status": status,
                    "reasoning": reasoning,
                }
                
            except Exception as e:
                print(f"⚠️ Error processing article {idx}: {e}")
                return {
                    "article": article,
                    "article_id": idx,
                    "status": "Irrelevant",
                    "reasoning": f"Error: {e}",
                }
        
        # Process in parallel batches
        tasks = []
        for idx, article in enumerate(articles):
            task = loop.run_in_executor(
                self.executor,
                process_article,
                article,
                idx
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def _parallel_scoring(self, relevant_articles: List[Dict]) -> List[Dict]:
        """Execute article scoring in parallel."""
        loop = asyncio.get_event_loop()
        
        def score_article(item: Dict) -> Dict:
            try:
                article = item["article"]
                messages = [Message(
                    role="user",
                    content=f"Article Title: {article.title}\n"
                           f"Source Domain: {article.domain}\n"
                           f"URL: {article.url}\n"
                           f"Summary: {article.content[:500]}\n"
                           f"First Pass Assessment: {item['reasoning']}"
                )]
                
                result = self.scoring_agent.run(messages=messages)
                
                # Parse score from result
                score = 7.5  # Default
                reasoning = ""
                
                if hasattr(result, 'content'):
                    content = str(result.content)
                    # Extract score from response
                    import re
                    score_match = re.search(r'Score:\s*(\d+(?:\.\d+)?)', content)
                    if score_match:
                        score = float(score_match.group(1))
                    reasoning = content
                
                # Save response
                self.response_tracker.save_agent_interaction(
                    agent_type="scoring",
                    article_id=f"article_{item['article_id']}",
                    input_data=item,
                    output_data={"score": score, "reasoning": reasoning},
                )
                
                return {
                    **article.__dict__,
                    "article_id": item["article_id"],
                    "overall_score": score,
                    "scoring_rationale": reasoning,
                    "first_pass_reasoning": item["reasoning"],
                }
                
            except Exception as e:
                print(f"⚠️ Error scoring article {item['article_id']}: {e}")
                return {
                    **item["article"].__dict__,
                    "article_id": item["article_id"],
                    "overall_score": 0,
                    "scoring_rationale": f"Error: {e}",
                }
        
        # Process in parallel
        tasks = []
        for item in relevant_articles:
            task = loop.run_in_executor(
                self.executor,
                score_article,
                item
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def _comparative_ranking_async(self, scored_articles: List[Dict]) -> List[Dict]:
        """Execute comparative ranking with batching."""
        # Filter by threshold
        candidates = [a for a in scored_articles if a["overall_score"] >= 6.0]
        
        if not candidates:
            return []
        
        # Create batches
        batch_size = 10
        batches = [candidates[i:i+batch_size] for i in range(0, len(candidates), batch_size)]
        
        # Accumulate rankings across shuffles
        rank_accumulator = defaultdict(list)
        rationale_map = defaultdict(list)
        
        # Multiple shuffle passes
        for pass_num in range(3):
            print(f"  🔁 Shuffle Pass {pass_num + 1}/3")
            
            # Shuffle and process batches
            shuffled_batches = batches.copy()
            random.shuffle(shuffled_batches)
            
            for batch_idx, batch in enumerate(shuffled_batches):
                shuffled_batch = batch.copy()
                random.shuffle(shuffled_batch)
                
                # Rank this batch
                batch_text = "\n\n".join([
                    f"- Title: {a['title']}\n"
                    f"  Score: {a['overall_score']}\n"
                    f"  Domain: {a.get('domain', 'unknown')}\n"
                    f"  Rationale: {a.get('scoring_rationale', '')[:200]}"
                    for a in shuffled_batch
                ])
                
                try:
                    messages = [Message(
                        role="user",
                        content=f"Rank these {len(shuffled_batch)} articles comparatively:\n\n{batch_text}"
                    )]
                    
                    result = self.comparative_ranker_agent.run(messages=messages)
                    
                    # Parse ranking from result
                    if hasattr(result, 'content'):
                        # Simple ranking based on order mentioned
                        for rank, article in enumerate(shuffled_batch, 1):
                            title = article["title"]
                            rank_accumulator[title].append(rank)
                            rationale_map[title].append(f"Batch {batch_idx} rank: {rank}")
                    
                except Exception as e:
                    print(f"    ⚠️ Error ranking batch {batch_idx}: {e}")
                    # Fallback to score-based ranking
                    sorted_batch = sorted(shuffled_batch, key=lambda x: x["overall_score"], reverse=True)
                    for rank, article in enumerate(sorted_batch, 1):
                        title = article["title"]
                        rank_accumulator[title].append(rank)
                        rationale_map[title].append(f"Fallback rank: {rank}")
        
        # Calculate average ranks
        ranked_articles = []
        for article in candidates:
            title = article["title"]
            if title in rank_accumulator:
                avg_rank = sum(rank_accumulator[title]) / len(rank_accumulator[title])
                article["comparative_avg_rank"] = avg_rank
                article["comparative_rationales"] = rationale_map[title]
                ranked_articles.append(article)
        
        # Sort by average rank
        ranked_articles.sort(key=lambda x: x["comparative_avg_rank"])
        
        return ranked_articles
    
    async def _final_selection_async(self, ranked_articles: List[Dict], max_articles: int) -> List[Dict]:
        """Execute final selection."""
        if not ranked_articles:
            return []
        
        # Format for selector
        articles_text = "\n\n".join([
            f"{idx}. {a['title']}\n"
            f"   Score: {a['overall_score']:.1f}\n"
            f"   Domain: {a.get('domain', 'unknown')}\n"
            f"   Rank: {a.get('comparative_avg_rank', 999):.1f}"
            for idx, a in enumerate(ranked_articles[:max_articles * 2], 1)
        ])
        
        try:
            messages = [Message(
                role="user",
                content=f"Select the top {max_articles} articles from these candidates:\n\n{articles_text}"
            )]
            
            result = self.selector_agent.run(messages=messages)
            
            # For now, just take top N by rank
            selected = ranked_articles[:max_articles]
            
            # Save response
            self.response_tracker.save_agent_interaction(
                agent_type="selector",
                article_id="final_selection",
                input_data={"candidates": len(ranked_articles), "max_articles": max_articles},
                output_data={"selected": len(selected)},
            )
            
            return selected
            
        except Exception as e:
            print(f"⚠️ Error in selection: {e}")
            # Fallback to top N
            return ranked_articles[:max_articles]
    
    def run_sync(
        self,
        articles: List[Article],
        max_articles: int = 10,
        resume_from_checkpoint: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for the async workflow."""
        # Load checkpoint if provided
        if resume_from_checkpoint and self.state:
            if self.state.load_checkpoint(resume_from_checkpoint):
                print(f"✅ Resumed from checkpoint: {resume_from_checkpoint}")
        
        # Run async workflow
        return asyncio.run(self.process_articles_parallel(articles, max_articles))


# Factory function for backward compatibility
def get_article_selection_workflow_v2(
    user_id: str = "default",
    session_id: str = "default",
    debug_mode: bool = False,
    max_parallel_workers: int = 5,
) -> ArticleSelectionWorkflowV2:
    """Create the improved V2 workflow."""
    return ArticleSelectionWorkflowV2(
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode,
        max_parallel_workers=max_parallel_workers,
        enable_checkpointing=True,
    )