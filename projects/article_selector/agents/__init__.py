"""Article Selector Agents Registration."""

from core.agents import agent_registry
from .first_pass_agent import get_first_pass_agent
from .scoring_agent import get_scoring_agent
from .selector_agent import get_selector_agent
from .comparative_ranker_agent import get_comparative_ranker_agent

# Register agents with the article_selector category
agent_registry.register_agent("article_selector", "first_pass", get_first_pass_agent)
agent_registry.register_agent("article_selector", "scoring", get_scoring_agent)
agent_registry.register_agent("article_selector", "comparative_ranker", get_comparative_ranker_agent)
agent_registry.register_agent("article_selector", "selector", get_selector_agent)

__all__ = [
    "get_first_pass_agent",
    "get_scoring_agent",
    "get_comparative_ranker_agent",
    "get_selector_agent",
]