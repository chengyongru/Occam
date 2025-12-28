"""
Data models for knowledge entry system
Using Pydantic for data validation and Instructor for structured AI output
"""
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class ArticleContent(BaseModel):
    """Raw content extracted from webpage"""
    url: HttpUrl
    title: str
    content: str  # Markdown format
    user_notes: Optional[str] = None  # User's notes/thoughts


class KnowledgeEntry(BaseModel):
    """
    Structured knowledge entry matching Notion Database schema
    This model will be used with Instructor to extract structured data from AI
    """
    title: str = Field(description="Article title")
    ai_summary: str = Field(description="One-sentence core insight or summary")
    critical_thinking: List[str] = Field(
        description="3 critical thinking points or counter-intuitive insights",
        min_length=3,
        max_length=3
    )
    tags: List[str] = Field(
        description="Automatic categorization tags (e.g., cognitive science, economics)",
        default_factory=list
    )
    score: int = Field(
        description="Value score from 0 to 100",
        ge=0,
        le=100
    )
    url: HttpUrl = Field(description="Original article URL")
    page_content: str = Field(description="Full Markdown content from webpage plus user notes")

