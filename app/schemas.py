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
