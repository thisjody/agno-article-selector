"""Comparative Ranker Agent for relative article ranking within batches."""

from typing import Optional, List, Dict, Any
from pathlib import Path
from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field


class RankedArticle(BaseModel):
    """Single ranked article in comparative analysis."""
    original_title: str = Field(description="Exact title from input")
    refined_rank: int = Field(description="Rank within batch (1=best)")
    comparative_rationale: str = Field(description="Why this rank relative to others")


class ComparativeRankingResult(BaseModel):
    """Result of comparative ranking for a batch."""
    ranked_articles: List[RankedArticle] = Field(description="Articles ranked within batch")


def get_comparative_ranker_instructions() -> str:
    """Generate instructions for the comparative ranker agent."""
    
    # Load the prompts
    prompt_dir = Path(__file__).parent.parent / "prompts"
    with open(prompt_dir / "system_prompt.txt", "r") as f:
        system_prompt = f.read()
    
    with open(prompt_dir / "comparative_ranker_prompt.txt", "r") as f:
        ranker_prompt = f.read()
    
    return system_prompt + "\n\n---\n\n" + ranker_prompt


def get_comparative_ranker_agent(
    model_id: str = "gemini-2.0-flash",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Agent:
    """Factory function to create the Comparative Ranker Agent.
    
    Args:
        model_id: The model ID to use (defaults to Gemini Flash for ADK parity)
        user_id: Optional user ID for tracking
        session_id: Optional session ID for conversation context
        debug_mode: Enable debug output
        
    Returns:
        Configured Agent instance
    """
    
    return Agent(
        name="Comparative Ranker",
        agent_id="comparative_ranker_agent",
        user_id=user_id,
        session_id=session_id,
        model=Gemini(id=model_id),
        description="Re-ranks articles within batches using comparative analysis and domain credibility",
        instructions=get_comparative_ranker_instructions(),
        response_model=ComparativeRankingResult,
        markdown=False,  # Structured JSON output
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )