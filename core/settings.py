"""Application settings and configuration management."""

import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # LLM Configuration
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_default_region: str = Field(default="us-east-1", env="AWS_DEFAULT_REGION")
    
    google_cloud_project: Optional[str] = Field(default=None, env="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field(default="us-central1", env="GOOGLE_CLOUD_LOCATION")
    google_application_credentials: Optional[str] = Field(default=None, env="GOOGLE_APPLICATION_CREDENTIALS")
    google_genai_use_vertexai: bool = Field(default=False, env="GOOGLE_GENAI_USE_VERTEXAI")
    
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Database Configuration
    candidate_embed_db_path: str = Field(
        default="data/test_articles.duckdb",
        env="CANDIDATE_EMBED_DB_PATH"
    )
    agent_response_output_dir: str = Field(
        default="output/responses",
        env="AGENT_RESPONSE_OUTPUT_DIR"
    )
    selector_candidate_db: str = Field(
        default="data/selector_candidates.duckdb",
        env="SELECTOR_CANDIDATE_DB"
    )
    
    # MotherDuck Configuration
    motherduck_token: Optional[str] = Field(default=None, env="MOTHERDUCK_TOKEN")
    motherduck_database: str = Field(default="newsletter-data", env="MOTHERDUCK_DATABASE")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=True, env="API_RELOAD")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    
    # Agent Configuration
    default_model: str = Field(default="claude", env="DEFAULT_MODEL")
    default_model_id: str = Field(
        default="us.anthropic.claude-sonnet-4-20250514-v1:0",
        env="DEFAULT_MODEL_ID"
    )
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    max_articles_per_batch: int = Field(default=50, env="MAX_ARTICLES_PER_BATCH")
    default_max_selected_articles: int = Field(default=10, env="DEFAULT_MAX_SELECTED_ARTICLES")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/article_selector.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def ensure_directories(self):
        """Ensure all required directories exist."""
        dirs = [
            Path(self.candidate_embed_db_path).parent,
            Path(self.agent_response_output_dir),
            Path(self.selector_candidate_db).parent,
            Path(self.log_file).parent,
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_model_config(self):
        """Get model configuration based on default_model setting.
        
        Returns:
            Dict with model configuration
        """
        if self.default_model == "claude":
            return {
                "provider": "aws_bedrock",
                "model_id": self.default_model_id,
                "credentials": {
                    "aws_access_key_id": self.aws_access_key_id,
                    "aws_secret_access_key": self.aws_secret_access_key,
                    "region": self.aws_default_region,
                }
            }
        elif self.default_model == "gemini":
            return {
                "provider": "vertex_ai" if self.google_genai_use_vertexai else "google_genai",
                "model_id": "gemini-2.0-flash",
                "credentials": {
                    "project": self.google_cloud_project,
                    "location": self.google_cloud_location,
                    "credentials_file": self.google_application_credentials,
                }
            }
        elif self.default_model == "openai":
            return {
                "provider": "openai",
                "model_id": "gpt-4",
                "credentials": {
                    "api_key": self.openai_api_key,
                }
            }
        else:
            raise ValueError(f"Unknown model: {self.default_model}")
    
    def use_motherduck(self) -> bool:
        """Check if MotherDuck should be used instead of local DuckDB.
        
        Returns:
            True if MotherDuck token is configured
        """
        return bool(self.motherduck_token)


# Global settings instance
settings = Settings()

# Ensure directories exist on startup
settings.ensure_directories()