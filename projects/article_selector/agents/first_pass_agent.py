"""First Pass Filtering Agent for article selection."""

from textwrap import dedent
from typing import Optional
from pathlib import Path
from agno.agent import Agent
from agno.models.google import Gemini
from projects.article_selector.models import FirstPassResult


def get_first_pass_instructions() -> str:
    """Generate instructions for the first pass agent."""
    
    # Load the system prompt
    prompt_dir = Path(__file__).parent.parent / "prompts"
    with open(prompt_dir / "system_prompt.txt", "r") as f:
        system_prompt = f.read()
    
    with open(prompt_dir / "first_pass_prompt.txt", "r") as f:
        first_pass_prompt = f.read()
    
    return system_prompt + "\n\n---\n\n" + first_pass_prompt


def get_first_pass_agent(
    model_id: str = "gemini-2.0-flash",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Agent:
    """Factory function to create the First Pass Filtering Agent.
    
    Args:
        model_id: The model ID to use (defaults to Gemini Flash for ADK parity)
        user_id: Optional user ID for tracking
        session_id: Optional session ID for conversation context
        debug_mode: Enable debug output
        
    Returns:
        Configured Agent instance
    """
    
    return Agent(
        name="First Pass Filter",
        agent_id="first_pass_agent",
        user_id=user_id,
        session_id=session_id,
        model=Gemini(id=model_id),
        description="Determines if an article is relevant based on strict open source security criteria and domain credibility",
        instructions=get_first_pass_instructions(),
        # response_model=FirstPassResult,  # Disabled to match ADK plain text output
        markdown=False,
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
    )