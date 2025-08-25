"""Selector Agent for final article selection and ranking."""

from textwrap import dedent
from typing import Optional
from pathlib import Path
from agno.agent import Agent
from agno.models.google import Gemini
from projects.article_selector.models import SelectorResult


def get_selector_instructions() -> str:
    """Generate instructions for the selector agent."""
    
    # Load the prompts
    prompt_dir = Path(__file__).parent.parent / "prompts"
    with open(prompt_dir / "system_prompt.txt", "r") as f:
        system_prompt = f.read()
    
    with open(prompt_dir / "selector_prompt.txt", "r") as f:
        selector_prompt = f.read()
    
    return system_prompt + "\n\n---\n\n" + selector_prompt


def get_selector_agent(
    model_id: str = "gemini-2.0-flash",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Agent:
    """Factory function to create the Selector Agent.
    
    Args:
        model_id: The model ID to use
        user_id: Optional user ID for tracking
        session_id: Optional session ID for conversation context
        debug_mode: Enable debug output
        
    Returns:
        Configured Agent instance
    """
    
    return Agent(
        name="Article Selector",
        agent_id="selector_agent",
        user_id=user_id,
        session_id=session_id,
        model=Gemini(id=model_id),
        description="Selects and ranks the best articles from scored candidates for the newsletter",
        instructions=get_selector_instructions(),
        response_model=SelectorResult,
        markdown=False,  # Structured output
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )