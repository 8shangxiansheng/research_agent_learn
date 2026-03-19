"""
Database models for Academic Q&A Agent application.
Defines ChatSession and ChatMessage models for multi-turn conversation tracking.
"""
from datetime import UTC, datetime
from typing import List

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
import enum

from app.database import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class MessageRole(str, enum.Enum):
    """Enum for message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"


class ChatSession(Base):
    """
    Chat session model representing a single conversation.
    Each session can have multiple messages.
    """
    __tablename__ = "chat_sessions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Session fields
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    
    # Relationship to messages (one-to-many)
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )
    
    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, title='{self.title}')>"


class ChatMessage(Base):
    """
    Chat message model representing a single message in a conversation.
    Each message belongs to one session.
    """
    __tablename__ = "chat_messages"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign key to session
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    
    # Message fields
    role: Mapped[MessageRole] = mapped_column(
        String(20), 
        nullable=False
    )  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    
    # Relationship to session (many-to-one)
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role='{self.role}', session_id={self.session_id})>"
