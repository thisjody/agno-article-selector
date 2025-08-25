"""Article Selector Workflows Registration."""

from core.workflows import workflow_registry
from .article_selection_workflow import get_article_selection_workflow, process_articles

# Register the workflow
workflow_registry.register(
    workflow_id="article_selection",
    name="Article Selection Pipeline",
    description="Multi-stage article selection for open source security newsletter",
    category="article_selector",
    factory=get_article_selection_workflow,
)

__all__ = [
    "get_article_selection_workflow",
    "process_articles",
]