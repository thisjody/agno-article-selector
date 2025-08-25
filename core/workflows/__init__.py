"""Core workflow infrastructure."""

from .base import WorkflowRegistry

# Global workflow registry
workflow_registry = WorkflowRegistry()

__all__ = ["workflow_registry"]