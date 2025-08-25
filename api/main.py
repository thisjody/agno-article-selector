"""FastAPI application for article selector."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import projects to register agents and workflows
import projects.article_selector.agents  # noqa: F401
import projects.article_selector.workflows  # noqa: F401


def create_app() -> FastAPI:
    """Create a FastAPI App."""
    
    # Create FastAPI App
    app = FastAPI(
        title="Article Selector API",
        version="1.0.0",
        description="API for article selection using Agno agents",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "article-selector"}
    
    # Add agent listing endpoint
    @app.get("/agents")
    async def list_agents():
        from core.agents import agent_registry
        return agent_registry.list_agents()
    
    # Add workflow listing endpoint
    @app.get("/workflows")
    async def list_workflows():
        from core.workflows import workflow_registry
        return workflow_registry.list_workflows()
    
    return app


# Create the app instance
app = create_app()