"""Response tracking system for saving agent inputs and outputs."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from core.settings import settings


class ResponseTracker:
    """Tracks and saves agent inputs and outputs to JSON files."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize response tracker.
        
        Args:
            output_dir: Directory to save responses (uses settings default if not provided)
        """
        self.output_dir = Path(output_dir or settings.agent_response_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for each agent type
        self.agent_dirs = {
            'first_pass': self.output_dir / 'first_pass',
            'scoring': self.output_dir / 'scoring',
            'selector': self.output_dir / 'selector',
            'comparative_ranker': self.output_dir / 'comparative_ranker',
        }
        
        for dir_path in self.agent_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def save_agent_interaction(
        self,
        agent_type: str,
        article_id: Any,
        input_data: Dict[str, Any],
        output_data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save agent input and output to JSON file.
        
        Args:
            agent_type: Type of agent (first_pass, scoring, selector)
            article_id: ID of the article being processed
            input_data: Input sent to the agent
            output_data: Output received from the agent
            metadata: Additional metadata to save
            
        Returns:
            Path to saved file
        """
        # Determine output directory
        output_dir = self.agent_dirs.get(agent_type, self.output_dir / agent_type)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{agent_type}_article_{article_id}_{timestamp}.json"
        filepath = output_dir / filename
        
        # Prepare data to save
        data = {
            "agent_type": agent_type,
            "article_id": str(article_id),
            "timestamp": datetime.now().isoformat(),
            "input": input_data,
            "output": self._serialize_output(output_data),
            "metadata": metadata or {}
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return str(filepath)
    
    def save_batch_interaction(
        self,
        agent_type: str,
        batch_id: str,
        input_data: Dict[str, Any],
        output_data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save batch processing input and output.
        
        Args:
            agent_type: Type of agent
            batch_id: Batch identifier
            input_data: Input sent to the agent
            output_data: Output received from the agent
            metadata: Additional metadata
            
        Returns:
            Path to saved file
        """
        output_dir = self.agent_dirs.get(agent_type, self.output_dir / agent_type)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename for batch
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{agent_type}_batch_{batch_id}_{timestamp}.json"
        filepath = output_dir / filename
        
        # Prepare data
        data = {
            "agent_type": agent_type,
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "input": input_data,
            "output": self._serialize_output(output_data),
            "metadata": metadata or {}
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return str(filepath)
    
    def save_sanity_check_input(
        self,
        agent_type: str,
        article_id: Any,
        input_text: str
    ) -> str:
        """Save sanity check input file (plain text format like ADK version).
        
        Args:
            agent_type: Type of agent
            article_id: Article identifier
            input_text: Raw input text for the agent
            
        Returns:
            Path to saved file
        """
        output_dir = self.agent_dirs.get(agent_type, self.output_dir / agent_type)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename matching ADK pattern
        filename = f"sanity_check_{agent_type}_input_{article_id}.txt"
        filepath = output_dir / filename
        
        # Save plain text
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(input_text)
        
        return str(filepath)
    
    def save_global_ranking(
        self,
        ranked_articles: list,
        batch_id: Optional[str] = None
    ) -> str:
        """Save global ranking results.
        
        Args:
            ranked_articles: List of ranked articles
            batch_id: Optional batch identifier
            
        Returns:
            Path to saved file
        """
        output_dir = self.agent_dirs.get('comparative_ranker', self.output_dir / 'comparative_ranker')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        batch_id = batch_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"global_ranked_articles_{batch_id}.json"
        filepath = output_dir / filename
        
        # Prepare data
        data = {
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "total_articles": len(ranked_articles),
            "ranked_articles": ranked_articles
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return str(filepath)
    
    def _serialize_output(self, output_data: Any) -> Any:
        """Serialize output data for JSON storage.
        
        Args:
            output_data: Output data from agent
            
        Returns:
            JSON-serializable version of the output
        """
        if hasattr(output_data, 'model_dump'):
            # Pydantic model
            return output_data.model_dump()
        elif hasattr(output_data, 'content'):
            # Agent response object
            return str(output_data.content)
        elif isinstance(output_data, dict):
            return output_data
        else:
            return str(output_data)
    
    def get_response_files(
        self,
        agent_type: Optional[str] = None,
        article_id: Optional[Any] = None,
        limit: int = 100
    ) -> list:
        """Get list of response files.
        
        Args:
            agent_type: Filter by agent type
            article_id: Filter by article ID
            limit: Maximum number of files to return
            
        Returns:
            List of file paths
        """
        files = []
        
        # Determine directories to search
        if agent_type:
            dirs = [self.agent_dirs.get(agent_type, self.output_dir / agent_type)]
        else:
            dirs = list(self.agent_dirs.values())
        
        # Search for files
        for dir_path in dirs:
            if not dir_path.exists():
                continue
            
            for filepath in sorted(dir_path.glob("*.json"), reverse=True)[:limit]:
                if article_id:
                    # Filter by article ID if specified
                    if f"article_{article_id}_" in filepath.name:
                        files.append(str(filepath))
                else:
                    files.append(str(filepath))
        
        return files[:limit]
    
    def load_response(self, filepath: str) -> Dict[str, Any]:
        """Load a response file.
        
        Args:
            filepath: Path to response file
            
        Returns:
            Response data
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all saved responses.
        
        Returns:
            Summary statistics
        """
        summary = {
            "total_responses": 0,
            "by_agent": {},
            "latest_files": []
        }
        
        for agent_type, dir_path in self.agent_dirs.items():
            if not dir_path.exists():
                continue
            
            files = list(dir_path.glob("*.json")) + list(dir_path.glob("*.txt"))
            count = len(files)
            summary["total_responses"] += count
            summary["by_agent"][agent_type] = count
            
            # Add latest file for this agent
            if files:
                latest = max(files, key=lambda f: f.stat().st_mtime)
                summary["latest_files"].append({
                    "agent": agent_type,
                    "file": str(latest),
                    "modified": datetime.fromtimestamp(latest.stat().st_mtime).isoformat()
                })
        
        return summary


# Global tracker instance
response_tracker = ResponseTracker()