"""Enhanced agents with response tracking capabilities."""

from typing import Optional, Dict, Any, List
from pathlib import Path
from agno.models.message import Message
from core.response_tracker import ResponseTracker
from projects.article_selector.agents import (
    get_first_pass_agent as base_first_pass_agent,
    get_scoring_agent as base_scoring_agent,
    get_selector_agent as base_selector_agent,
)
from projects.article_selector.models import Article


class TrackedFirstPassAgent:
    """First pass agent with response tracking."""
    
    def __init__(self, debug_mode: bool = False):
        """Initialize tracked first pass agent."""
        self.agent = base_first_pass_agent(debug_mode=debug_mode)
        self.tracker = ResponseTracker(Path("output/responses"))
    
    def process_article(
        self,
        article: Article,
        article_id: Optional[Any] = None,
        save_responses: bool = True
    ) -> Dict[str, Any]:
        """Process article through first pass filter.
        
        Args:
            article: Article to process
            article_id: Optional article ID for tracking
            save_responses: Whether to save responses to files
            
        Returns:
            Processing result with status
        """
        # Prepare input
        input_text = f"""Article Title: {article.title}
Source Domain: {article.domain or 'unknown'}
Article Content: {article.content[:1000] if article.content else 'None'}"""
        
        input_data = {
            "title": article.title,
            "content": article.content[:1000] if article.content else "",
            "domain": article.domain,
            "url": article.url
        }
        
        try:
            # Run the agent with proper Message format
            messages = [Message(role="user", content=input_text)]
            result = self.agent.run(messages=messages)
            
            # Parse result - now expecting plain text like ADK
            result_text = str(result.content) if hasattr(result, 'content') else str(result)
            
            # Parse ADK format: "first_pass_result: Relevant/Irrelevant. Reasoning..."
            if "first_pass_result:" in result_text:
                # Extract status and reasoning from ADK format
                parts = result_text.split("first_pass_result:", 1)[1].strip()
                if parts.startswith("Relevant"):
                    status = "Relevant"
                    reasoning = parts[8:].strip().lstrip('.').strip()
                elif parts.startswith("Irrelevant"):
                    status = "Irrelevant"
                    reasoning = parts[10:].strip().lstrip('.').strip()
                else:
                    # Fallback
                    status = "Relevant" if "Relevant" in result_text and "Irrelevant" not in result_text.split(".")[0] else "Irrelevant"
                    reasoning = result_text
            else:
                # Fallback to simple parsing
                status = "Relevant" if "Relevant" in result_text and "Irrelevant" not in result_text.split(".")[0] else "Irrelevant"
                reasoning = result_text
            
            # Save if requested
            if save_responses:
                self.tracker.save_agent_interaction(
                    agent_type="first_pass",
                    article_id=article_id or article.title[:50],
                    input_data=input_data,
                    output_data=result_text
                )
            
            return {
                "status": status,
                "result": result,
                "reasoning": reasoning
            }
            
        except Exception as e:
            print(f"Error in first pass agent: {e}")
            return {
                "status": "Irrelevant",
                "result": None,
                "reasoning": f"Error: {str(e)}"
            }


class TrackedScoringAgent:
    """Scoring agent with response tracking."""
    
    def __init__(self, debug_mode: bool = False):
        """Initialize tracked scoring agent."""
        self.agent = base_scoring_agent(debug_mode=debug_mode)
        self.tracker = ResponseTracker(Path("output/responses"))
    
    def score_article(
        self,
        article: Article,
        first_pass_reasoning: str,
        article_id: Optional[Any] = None,
        save_responses: bool = True
    ) -> Dict[str, Any]:
        """Score article for relevance and quality.
        
        Args:
            article: Article to score
            first_pass_reasoning: Reasoning from first pass
            article_id: Optional article ID for tracking
            save_responses: Whether to save responses
            
        Returns:
            Scoring result
        """
        # Prepare input
        input_text = f"""Article Title: {article.title}
Source Domain: {article.domain or 'unknown'}
Summary: {article.content[:500] if article.content else 'No content'}
URL: {article.url or 'N/A'}

First Pass Assessment: {first_pass_reasoning}

Please score this article from 0-10 based on open source security relevance."""
        
        input_data = {
            "title": article.title,
            "content_preview": article.content[:500] if article.content else "",
            "domain": article.domain,
            "url": article.url,
            "first_pass_reasoning": first_pass_reasoning
        }
        
        try:
            # Run the agent
            messages = [Message(role="user", content=input_text)]
            result = self.agent.run(messages=messages)
            
            # Parse score from result (look for number 0-10)
            result_text = str(result.content) if hasattr(result, 'content') else str(result)
            
            # Try to extract score
            import re
            score_match = re.search(r'score:\s*(\d+(?:\.\d+)?)', result_text, re.IGNORECASE)
            if score_match:
                score = float(score_match.group(1))
            else:
                # Fallback: look for any number 0-10
                numbers = re.findall(r'\b([0-9]|10)(?:\.\d+)?\b', result_text)
                score = float(numbers[0]) if numbers else 5.0
            
            # Save if requested
            if save_responses:
                self.tracker.save_agent_interaction(
                    agent_type="scoring",
                    article_id=article_id or article.title[:50],
                    input_data=input_data,
                    output_data=result_text
                )
            
            return {
                "score": score,
                "result": result,
                "rationale": result_text
            }
            
        except Exception as e:
            print(f"Error in scoring agent: {e}")
            return {
                "score": 0.0,
                "result": None,
                "rationale": f"Error: {str(e)}"
            }


class TrackedSelectorAgent:
    """Selector agent with response tracking."""
    
    def __init__(self, debug_mode: bool = False):
        """Initialize tracked selector agent."""
        self.agent = base_selector_agent(debug_mode=debug_mode)
        self.tracker = ResponseTracker(Path("output/responses"))
    
    def select_articles(
        self,
        scored_articles: List[Dict[str, Any]],
        max_articles: int = 10,
        batch_id: Optional[str] = None,
        save_responses: bool = True
    ) -> Dict[str, Any]:
        """Select best articles from scored candidates.
        
        Args:
            scored_articles: List of scored articles
            max_articles: Maximum articles to select
            batch_id: Optional batch ID
            save_responses: Whether to save responses
            
        Returns:
            Selection result
        """
        # Prepare articles list for agent
        articles_text = []
        for idx, article in enumerate(scored_articles[:50], 1):  # Limit to top 50
            articles_text.append(
                f"{idx}. {article.get('title', 'Untitled')}\n"
                f"   Score: {article.get('overall_score', article.get('score', 0)):.1f}\n"
                f"   Domain: {article.get('domain', 'unknown')}\n"
                f"   URL: {article.get('url', 'N/A')}\n"
                f"   Rationale: {str(article.get('scoring_rationale', article.get('rationale', '')))[:200]}"
            )
        
        input_text = f"""Select the best {max_articles} articles from this ranked list for the newsletter:

{chr(10).join(articles_text)}

Ensure source diversity - avoid selecting too many articles from the same domain, especially discussion forums like Reddit."""
        
        input_data = {
            "articles_count": len(scored_articles),
            "max_selections": max_articles,
            "top_articles": articles_text[:10]  # Save top 10 for reference
        }
        
        try:
            # Run the agent
            messages = [Message(role="user", content=input_text)]
            result = self.agent.run(messages=messages)
            
            result_text = str(result.content) if hasattr(result, 'content') else str(result)
            
            # Save if requested
            if save_responses:
                self.tracker.save_agent_interaction(
                    agent_type="selector",
                    article_id=batch_id or "selection_batch",
                    input_data=input_data,
                    output_data=result_text
                )
            
            return {
                "result": result,
                "selection_text": result_text
            }
            
        except Exception as e:
            print(f"Error in selector agent: {e}")
            return {
                "result": None,
                "selection_text": f"Error: {str(e)}"
            }


def get_tracked_first_pass_agent(debug_mode: bool = False) -> TrackedFirstPassAgent:
    """Get tracked first pass agent."""
    return TrackedFirstPassAgent(debug_mode=debug_mode)


def get_tracked_scoring_agent(debug_mode: bool = False) -> TrackedScoringAgent:
    """Get tracked scoring agent."""
    return TrackedScoringAgent(debug_mode=debug_mode)


def get_tracked_selector_agent(debug_mode: bool = False) -> TrackedSelectorAgent:
    """Get tracked selector agent."""
    return TrackedSelectorAgent(debug_mode=debug_mode)