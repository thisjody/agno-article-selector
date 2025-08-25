"""Core agent infrastructure."""

from .base import AgentRegistry

# Global agent registry
agent_registry = AgentRegistry()

__all__ = ["agent_registry"]