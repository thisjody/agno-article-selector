"""Base workflow classes and registry."""

from typing import Dict, Callable, Optional, List, Any


class WorkflowRegistry:
    """Registry for managing workflows."""
    
    def __init__(self):
        self._workflows: Dict[str, Dict[str, Any]] = {}
    
    def register(
        self,
        workflow_id: str,
        name: str,
        description: str,
        category: str,
        factory: Callable,
        **metadata
    ) -> None:
        """Register a workflow with the registry.
        
        Args:
            workflow_id: Unique identifier for the workflow
            name: Human-readable name for the workflow
            description: Description of what the workflow does
            category: Category for the workflow (e.g., 'article_selector')
            factory: Factory function to create the workflow
            **metadata: Additional metadata for the workflow
        """
        self._workflows[workflow_id] = {
            "name": name,
            "description": description,
            "category": category,
            "factory": factory,
            **metadata
        }
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a workflow by ID.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow metadata dictionary or None if not found
        """
        return self._workflows.get(workflow_id)
    
    def get_factory(self, workflow_id: str) -> Optional[Callable]:
        """Get a workflow factory function by ID.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow factory function or None if not found
        """
        workflow = self._workflows.get(workflow_id)
        return workflow.get("factory") if workflow else None
    
    def list_workflows(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all registered workflows.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            List of workflow metadata dictionaries
        """
        workflows = []
        for workflow_id, metadata in self._workflows.items():
            if category is None or metadata.get("category") == category:
                workflows.append({
                    "id": workflow_id,
                    **{k: v for k, v in metadata.items() if k != "factory"}
                })
        return workflows