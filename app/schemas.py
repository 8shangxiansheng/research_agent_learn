"""
Pydantic schemas for API request/response validation.
Provides type-safe API boundaries for session and message operations.
"""
from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, ConfigDict


# ========== Session Schemas ==========

class SessionCreate(BaseModel):
    """Schema for creating a new chat session."""
    title: str = "New Chat"


class SessionUpdate(BaseModel):
    """Schema for updating an existing chat session."""
    title: Optional[str] = None


class MessageResponse(BaseModel):
    """Schema for message response in session details."""
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    """Schema for chat session response."""
    id: int
    title: str
    created_at: datetime
    messages: Optional[List[MessageResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class SessionListResponse(BaseModel):
    """Schema for session list item (without messages)."""
    id: int
    title: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionExportResponse(BaseModel):
    """Schema for markdown export payload."""
    filename: str
    content: str


# ========== Message Schemas ==========

class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    session_id: int
    role: Literal["user", "assistant"]
    content: str


class MessageCreateWithSession(BaseModel):
    """Schema for creating a message with session context (for WebSocket)."""
    role: Literal["user", "assistant"]
    content: str


# ========== Research Schemas ==========

class ResearchTaskCreate(BaseModel):
    """Schema for starting a research workflow."""
    query: str
    max_sources: int = 3
    session_id: Optional[int] = None
    document: Optional["ResearchDocumentInput"] = None


class ResearchDocumentInput(BaseModel):
    """Schema for a locally uploaded research document."""
    filename: str
    content_base64: str
    mime_type: Optional[str] = None


class ResearchTaskUpdate(BaseModel):
    """Schema for renaming an existing research task."""
    query: str


class ResearchShareRequest(BaseModel):
    """Schema for injecting research results back into a chat session."""
    mode: Literal["summary", "full"] = "summary"


class ResearchSourceResponse(BaseModel):
    """Normalized source metadata for research results."""
    source_id: str
    citation_label: str
    arxiv_id: Optional[str] = None
    title: str
    authors: list[str]
    abstract: str
    published_at: str
    url: str
    pdf_url: Optional[str] = None
    primary_category: Optional[str] = None
    categories: list[str] = []
    comment: Optional[str] = None
    journal_ref: Optional[str] = None
    doi: Optional[str] = None
    citation_text: Optional[str] = None
    source_type: str
    score: int


class ResearchTaskResponse(BaseModel):
    """Schema for the minimal research workflow result."""
    id: int
    session_id: Optional[int] = None
    query: str
    status: str
    generated_at: datetime
    report_filename: str
    plan: list[str]
    sources: list[ResearchSourceResponse]
    answer: str
    report_markdown: str
