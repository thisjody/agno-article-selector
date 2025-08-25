"""Article Selection Workflow orchestrating multiple agents."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from agno.workflow.v2 import Step, Workflow
from projects.article_selector.agents import (
    get_first_pass_agent,
    get_scoring_agent,
    get_selector_agent,
)
from projects.article_selector.models import (
    Article,
    FirstPassResult,
    ScoringResult,
)


def create_first_pass_step(articles: List[Article]) -> List[Dict[str, Any]]:
    """Create input for first pass agent to process articles."""
    return [
        {
            "article": article.model_dump(),
            "instruction": f"Evaluate this article:\nTitle: {article.title}\nContent: {article.content[:500]}...\nDomain: {article.domain or 'Unknown'}"
        }
        for article in articles
    ]


def create_scoring_step_input(articles_with_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create input for scoring agent based on first pass results."""
    relevant_articles = []
    for item in articles_with_results:
        if item.get("first_pass_result", {}).get("status") == "Relevant":
            article = item["article"]
            relevant_articles.append({
                "article": article,
                "first_pass_reasoning": item["first_pass_result"]["reasoning"],
                "instruction": f"Score this article that passed first-pass filtering:\nTitle: {article['title']}\nContent: {article['content'][:700]}...\nDomain: {article.get('domain', 'Unknown')}\nFirst-pass reasoning: {item['first_pass_result']['reasoning']}"
            })
    return relevant_articles


def create_selector_step_input(scored_articles: List[Dict[str, Any]], max_articles: int) -> Dict[str, Any]:
    """Create input for selector agent."""
    return {
        "scored_articles": scored_articles,
        "max_articles": max_articles,
        "instruction": f"Select and rank the top {max_articles} articles from {len(scored_articles)} scored candidates."
    }


def get_article_selection_workflow(
    agent_id: str = "article_selection_workflow",
    user_id: str = "default",
    session_id: str = "default",
    debug_mode: bool = False,
) -> Workflow:
    """Create the article selection workflow.
    
    This workflow orchestrates three agents:
    1. First Pass Agent - Filters articles for relevance
    2. Scoring Agent - Scores relevant articles 
    3. Selector Agent - Selects and ranks final articles
    
    Args:
        agent_id: Workflow identifier
        user_id: User ID for tracking
        session_id: Session ID for context
        debug_mode: Enable debug output
        
    Returns:
        Configured Workflow instance
    """
    
    # Create agents with consistent configuration
    first_pass = get_first_pass_agent(
        user_id=user_id,
        session_id=f"{session_id}_first_pass",
        debug_mode=debug_mode,
    )
    
    scoring = get_scoring_agent(
        user_id=user_id,
        session_id=f"{session_id}_scoring",
        debug_mode=debug_mode,
    )
    
    selector = get_selector_agent(
        user_id=user_id,
        session_id=f"{session_id}_selector",
        debug_mode=debug_mode,
    )
    
    # Define workflow steps
    return Workflow(
        name="Article Selection Pipeline",
        description="Multi-stage article selection for open source security newsletter",
        steps=[
            Step(
                name="First Pass Filtering",
                agent=first_pass,
                description="Filter articles for open source security relevance",
            ),
            Step(
                name="Article Scoring",
                agent=scoring,
                description="Score relevant articles on quality and impact",
            ),
            Step(
                name="Final Selection",
                agent=selector,
                description="Select and rank the best articles for the newsletter",
            ),
        ],
    )


def process_articles(
    articles: List[Article],
    max_articles: int = 10,
    user_id: str = "default",
    session_id: str = "default",
    debug_mode: bool = False,
) -> Dict[str, Any]:
    """Process articles through the selection workflow.
    
    This is a convenience function that runs the workflow with proper data transformation
    between steps.
    
    Args:
        articles: List of articles to process
        max_articles: Maximum number of articles to select
        user_id: User ID for tracking
        session_id: Session ID for context
        debug_mode: Enable debug output
        
    Returns:
        ArticleSelectionOutput with selected articles and statistics
    """
    start_time = datetime.now()
    
    # Create workflow
    workflow = get_article_selection_workflow(
        user_id=user_id,
        session_id=session_id,
        debug_mode=debug_mode,
    )
    
    # Process through workflow steps
    # Note: In actual implementation, this would use the Workflow.run() method
    # with proper data transformation between steps
    
    # For now, return a placeholder
    # This would be replaced with actual workflow execution
    return {
        "selected_articles": [],
        "statistics": {
            "total_input": len(articles),
            "total_selected": 0,
            "processing_time": (datetime.now() - start_time).total_seconds(),
        },
        "processing_time": (datetime.now() - start_time).total_seconds(),
    }