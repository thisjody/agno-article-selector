"""Pydantic models for article selection agents."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class RelevanceStatus(str, Enum):
    """Article relevance status."""
    RELEVANT = "Relevant"
    IRRELEVANT = "Irrelevant"


class Article(BaseModel):
    """Article data model."""
    title: str = Field(description="Article title")
    content: str = Field(description="Article content or summary")
    url: Optional[str] = Field(default=None, description="Article URL")
    domain: Optional[str] = Field(default=None, description="Source domain")
    published_date: Optional[datetime] = Field(default=None, description="Publication date")
    author: Optional[str] = Field(default=None, description="Article author")
    tags: Optional[List[str]] = Field(default=None, description="Article tags or categories")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class FirstPassResult(BaseModel):
    """Result from first pass filtering agent."""
    status: RelevanceStatus = Field(description="Relevance status")
    reasoning: str = Field(description="Concise justification for the decision")
    confidence: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Confidence score (0-1)"
    )


class ScoringResult(BaseModel):
    """Result from scoring agent."""
    relevance_score: float = Field(
        ge=0.0, 
        le=10.0, 
        description="Relevance score (0-10)"
    )
    quality_score: float = Field(
        ge=0.0, 
        le=10.0, 
        description="Quality score (0-10)"
    )
    impact_score: float = Field(
        ge=0.0, 
        le=10.0, 
        description="Impact score (0-10)"
    )
    overall_score: float = Field(
        ge=0.0, 
        le=10.0, 
        description="Overall score (0-10)"
    )
    reasoning: str = Field(description="Detailed scoring rationale")
    recommendation: str = Field(description="Include/Exclude recommendation with explanation")


class RankedArticle(BaseModel):
    """Article with ranking information."""
    article: Article
    first_pass_result: Optional[FirstPassResult] = None
    scoring_result: Optional[ScoringResult] = None
    rank: Optional[int] = Field(default=None, description="Article rank in selection")
    selection_reasoning: Optional[str] = Field(default=None, description="Why this article was selected")


class SelectorResult(BaseModel):
    """Result from selector agent."""
    selected_articles: List[RankedArticle] = Field(
        description="List of selected articles with rankings"
    )
    total_reviewed: int = Field(description="Total number of articles reviewed")
    total_selected: int = Field(description="Number of articles selected")
    selection_summary: str = Field(description="Summary of selection process and key findings")


class ArticleSelectionInput(BaseModel):
    """Input for article selection workflow."""
    articles: List[Article] = Field(description="List of articles to process")
    max_articles: Optional[int] = Field(
        default=10, 
        description="Maximum number of articles to select"
    )
    focus_areas: Optional[List[str]] = Field(
        default=None,
        description="Specific security focus areas to prioritize"
    )
    exclude_domains: Optional[List[str]] = Field(
        default=None,
        description="Additional domains to exclude"
    )


class ArticleSelectionOutput(BaseModel):
    """Output from article selection workflow."""
    selected_articles: List[RankedArticle] = Field(
        description="Final list of selected articles"
    )
    statistics: Dict[str, Any] = Field(
        description="Selection statistics and metrics"
    )
    processing_time: Optional[float] = Field(
        default=None,
        description="Total processing time in seconds"
    )