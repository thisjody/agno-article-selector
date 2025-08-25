"""Scoring Agent for article quality and relevance assessment."""

from textwrap import dedent
from typing import Optional
from pathlib import Path
from agno.agent import Agent
from agno.models.google import Gemini
from projects.article_selector.models import ScoringResult


def get_scoring_instructions() -> str:
    """Generate instructions for the scoring agent."""
    
    # Load the prompts
    prompt_dir = Path(__file__).parent.parent / "prompts"
    with open(prompt_dir / "system_prompt.txt", "r") as f:
        system_prompt = f.read()
    
    with open(prompt_dir / "scoring_prompt.txt", "r") as f:
        scoring_prompt = f.read()
    
    return system_prompt + "\n\n---\n\n" + scoring_prompt


def get_scoring_agent(
    model_id: str = "gemini-2.0-flash",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Agent:
    """Factory function to create the Scoring Agent.
    
    Args:
        model_id: The model ID to use
        user_id: Optional user ID for tracking
        session_id: Optional session ID for conversation context
        debug_mode: Enable debug output
        
    Returns:
        Configured Agent instance
    """
    
    return Agent(
        name="Article Scorer",
        agent_id="scoring_agent",
        user_id=user_id,
        session_id=session_id,
        model=Gemini(id=model_id),
        description="Scores filtered articles on relevance, quality, and impact for open source security",
        instructions=get_scoring_instructions(),
        response_model=ScoringResult,
        markdown=False,  # Structured output
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )