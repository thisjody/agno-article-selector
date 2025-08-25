"""Base agent classes and registry."""

from typing import Dict, Callable, Optional, List, Any
from abc import ABC, abstractmethod


class AgentRegistry:
    """Registry for managing agents by category."""
    
    def __init__(self):
        self._agents: Dict[str, Dict[str, Callable]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_agent(
        self, 
        category: str, 
        agent_id: str, 
        factory: Callable,
        description: Optional[str] = None,
        **metadata
    ) -> None:
        """Register an agent with the registry.
        
        Args:
            category: Category for the agent (e.g., 'article_selector')
            agent_id: Unique identifier for the agent within the category
            factory: Factory function to create the agent
            description: Optional description of the agent
            **metadata: Additional metadata for the agent
        """
        if category not in self._agents:
            self._agents[category] = {}
            self._metadata[category] = {}
        
        self._agents[category][agent_id] = factory
        self._metadata[category][agent_id] = {
            "description": description,
            **metadata
        }
    
    def get_agent(self, category: str, agent_id: str) -> Optional[Callable]:
        """Get an agent factory by category and ID.
        
        Args:
            category: Category of the agent
            agent_id: ID of the agent
            
        Returns:
            Agent factory function or None if not found
        """
        return self._agents.get(category, {}).get(agent_id)
    
    def list_agents(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """List all registered agents.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            Dictionary of categories and their agent IDs
        """
        if category:
            return {category: list(self._agents.get(category, {}).keys())}
        return {cat: list(agents.keys()) for cat, agents in self._agents.items()}
    
    def get_metadata(self, category: str, agent_id: str) -> Dict[str, Any]:
        """Get metadata for an agent.
        
        Args:
            category: Category of the agent
            agent_id: ID of the agent
            
        Returns:
            Agent metadata dictionary
        """
        return self._metadata.get(category, {}).get(agent_id, {})