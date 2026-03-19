"""
CRUD operations for Academic Q&A Agent.
Provides clean database access functions for sessions, messages, and research tasks.
"""
import json
from typing import Any, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChatSession, ChatMessage, MessageRole, ResearchTask
from app.schemas import SessionCreate, SessionUpdate, MessageCreate


# ========== Session CRUD ==========

def create_session(db: Session, session: SessionCreate) -> ChatSession:
    """
    Create a new chat session.

    Args:
        db: Database session
        session: Session creation schema

    Returns:
        Created ChatSession instance
    """
    db_session = ChatSession(title=session.title)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_session(db: Session, session_id: int) -> Optional[ChatSession]:
    """
    Get a chat session by ID.

    Args:
        db: Database session
        session_id: Session ID to retrieve

    Returns:
        ChatSession if found, None otherwise
    """
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()


def get_sessions(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    query: str | None = None,
) -> List[ChatSession]:
    """
    Get all chat sessions with pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of ChatSession instances
    """
    session_query = db.query(ChatSession)

    if query:
        search_term = f"%{query.strip().lower()}%"
        session_query = session_query.filter(func.lower(ChatSession.title).like(search_term))

    return (
        session_query
        .order_by(ChatSession.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_session(db: Session, session_id: int, session: SessionUpdate) -> Optional[ChatSession]:
    """
    Update a chat session.

    Args:
        db: Database session
        session_id: Session ID to update
        session: Session update schema

    Returns:
        Updated ChatSession if found, None otherwise
    """
    db_session = get_session(db, session_id)
    if db_session is None:
        return None

    if session.title is not None:
        db_session.title = session.title

    db.commit()
    db.refresh(db_session)
    return db_session


def delete_session(db: Session, session_id: int) -> bool:
    """
    Delete a chat session and all its messages.

    Args:
        db: Database session
        session_id: Session ID to delete

    Returns:
        True if deleted, False if not found
    """
    db_session = get_session(db, session_id)
    if db_session is None:
        return False

    db.delete(db_session)
    db.commit()
    return True


# ========== Message CRUD ==========

def create_message(db: Session, message: MessageCreate) -> ChatMessage:
    """
    Create a new chat message.

    Args:
        db: Database session
        message: Message creation schema

    Returns:
        Created ChatMessage instance
    """
    db_message = ChatMessage(
        session_id=message.session_id,
        role=message.role,
        content=message.content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def get_messages_by_session(db: Session, session_id: int) -> List[ChatMessage]:
    """
    Get all messages for a session.

    Args:
        db: Database session
        session_id: Session ID to get messages for

    Returns:
        List of ChatMessage instances ordered by created_at
    """
    return db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()


def get_message(db: Session, session_id: int, message_id: int) -> Optional[ChatMessage]:
    """Get a message by session and message id."""
    return db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.id == message_id,
    ).first()


def update_message_content(
    db: Session,
    session_id: int,
    message_id: int,
    content: str,
) -> Optional[ChatMessage]:
    """Update a message content in place."""
    db_message = get_message(db, session_id, message_id)
    if db_message is None:
        return None

    db_message.content = content
    db.commit()
    db.refresh(db_message)
    return db_message


def create_message_direct(
    db: Session,
    session_id: int,
    role: str,
    content: str
) -> ChatMessage:
    """
    Create a message directly with parameters (for WebSocket use).

    Args:
        db: Database session
        session_id: Session ID
        role: Message role ("user" or "assistant")
        content: Message content

    Returns:
        Created ChatMessage instance
    """
    db_message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


# ========== Research Task CRUD ==========

def create_research_task(
    db: Session,
    *,
    session_id: int | None,
    result: dict[str, Any],
) -> ResearchTask:
    """Persist a completed research task result."""
    db_task = ResearchTask(
        session_id=session_id,
        query=result["query"],
        status=result["status"],
        report_filename=result["report_filename"],
        answer=result["answer"],
        plan_json=json.dumps(result["plan"]),
        sources_json=json.dumps(result["sources"]),
        report_markdown=result["report_markdown"],
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_research_task(db: Session, task_id: int) -> Optional[ResearchTask]:
    """Get one persisted research task by id."""
    return db.query(ResearchTask).filter(ResearchTask.id == task_id).first()


def get_research_tasks_by_session(db: Session, session_id: int) -> List[ResearchTask]:
    """List research tasks for a session, newest first."""
    return (
        db.query(ResearchTask)
        .filter(ResearchTask.session_id == session_id)
        .order_by(ResearchTask.created_at.desc())
        .all()
    )


def update_research_task(
    db: Session,
    task_id: int,
    *,
    query: str,
    report_filename: str,
) -> Optional[ResearchTask]:
    """Rename a persisted research task and keep its export filename aligned."""
    task = get_research_task(db, task_id)
    if task is None:
        return None

    task.query = query
    task.report_filename = report_filename
    db.commit()
    db.refresh(task)
    return task


def refresh_research_task(
    db: Session,
    task_id: int,
    *,
    result: dict[str, Any],
) -> Optional[ResearchTask]:
    """Replace a persisted research task with a freshly rerun result."""
    task = get_research_task(db, task_id)
    if task is None:
        return None

    task.query = result["query"]
    task.status = result["status"]
    task.report_filename = result["report_filename"]
    task.answer = result["answer"]
    task.plan_json = json.dumps(result["plan"])
    task.sources_json = json.dumps(result["sources"])
    task.report_markdown = result["report_markdown"]
    db.commit()
    db.refresh(task)
    return task


def delete_research_task(db: Session, task_id: int) -> bool:
    """Delete a persisted research task."""
    task = get_research_task(db, task_id)
    if task is None:
        return False

    db.delete(task)
    db.commit()
    return True
