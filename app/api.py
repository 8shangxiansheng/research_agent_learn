"""
FastAPI API endpoints for Academic Q&A Agent.
Provides REST routes for sessions, research tasks, messages, and WebSocket streaming.
"""
import re
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas
from app.services.agent import get_agent
from app.services.research import get_research_orchestrator
from app.services.research.orchestrator import ResearchOrchestrator
from app.services.research.document_parser import parse_research_document


# Create router with API prefix
router = APIRouter(prefix="/api")
_citation_orchestrator = ResearchOrchestrator()


def _serialize_research_task(task: object) -> schemas.ResearchTaskResponse:
    """Convert a persisted research task ORM object into API shape."""
    sources = json.loads(task.sources_json)
    evidence_map = _citation_orchestrator.build_evidence_map(task.answer, sources)
    return schemas.ResearchTaskResponse(
        id=task.id,
        session_id=task.session_id,
        query=task.query,
        status=task.status,
        generated_at=task.created_at,
        report_filename=task.report_filename,
        plan=json.loads(task.plan_json),
        sources=sources,
        evidence_map=evidence_map,
        answer=task.answer,
        report_markdown=task.report_markdown,
    )


def _build_research_message_content(task: object, mode: str = "summary") -> str:
    """Render a persisted research task as chat-friendly markdown."""
    sources = json.loads(task.sources_json)
    if mode == "full":
        return task.report_markdown.strip()

    lines = [
        f"## Research Brief: {task.query}",
        "",
        task.answer,
        "",
    ]

    if sources:
        lines.extend(["### Key Sources", ""])
        for source in sources[:3]:
            lines.append(
                f"- [{source['citation_label']}] {source['title']} ({source['published_at'][:10]})"
            )

    return "\n".join(lines).strip()


def _extract_document_from_task(task: object) -> dict[str, str] | None:
    """Recover persisted local document context for reruns."""
    for source in json.loads(task.sources_json):
        if source.get("source_type") not in {"local_document", "local_pdf"}:
            continue
        document_text = source.get("document_text")
        document_filename = source.get("document_filename")
        if not document_text or not document_filename:
            continue
        return {
            "filename": document_filename,
            "mime_type": source.get("mime_type"),
            "source_type": source["source_type"],
            "text": document_text,
        }
    return None


def _build_raw_markdown_response(filename: str, content: str) -> PlainTextResponse:
    """Return markdown text with a download-friendly filename."""
    response = PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _slugify_report_filename(query: str) -> str:
    """Generate a stable report filename from a research query."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", query.strip().lower()).strip("-")
    return f"{slug or 'research-brief'}.md"


# ========== Session Endpoints ==========

@router.get("/sessions", response_model=List[schemas.SessionListResponse])
def list_sessions(
    skip: int = 0,
    limit: int = 100,
    query: str | None = None,
    db: Session = Depends(get_db)
):
    """Get all chat sessions."""
    return crud.get_sessions(db, skip=skip, limit=limit, query=query)


@router.get("/sessions/{session_id}", response_model=schemas.SessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific chat session with messages."""
    session = crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions", response_model=schemas.SessionResponse, status_code=201)
def create_session(
    session: schemas.SessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new chat session."""
    return crud.create_session(db, session)


@router.put("/sessions/{session_id}", response_model=schemas.SessionResponse)
def update_session(
    session_id: int,
    session: schemas.SessionUpdate,
    db: Session = Depends(get_db)
):
    """Update a chat session title."""
    updated = crud.update_session(db, session_id, session)
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return updated


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Delete a chat session and all its messages."""
    success = crud.delete_session(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}


# ========== Message Endpoints ==========

@router.get("/sessions/{session_id}/messages", response_model=List[schemas.MessageResponse])
def get_messages(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get all messages for a session."""
    session = crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return crud.get_messages_by_session(db, session_id)


@router.post(
    "/research/tasks",
    response_model=schemas.ResearchTaskResponse,
)
async def run_research_task(
    task: schemas.ResearchTaskCreate,
    db: Session = Depends(get_db),
):
    """Run a minimal deep research workflow and return structured results."""
    query = task.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Research query cannot be empty")

    if task.session_id is not None and crud.get_session(db, task.session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")

    max_sources = max(1, min(task.max_sources, 5))
    document = None
    if task.document is not None:
        try:
            document = parse_research_document(
                filename=task.document.filename,
                content_base64=task.document.content_base64,
                mime_type=task.document.mime_type,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    orchestrator = get_research_orchestrator()
    if document is None:
        result = await orchestrator.run(query=query, max_sources=max_sources)
    else:
        result = await orchestrator.run(
            query=query,
            max_sources=max_sources,
            document=document,
        )
    db_task = crud.create_research_task(
        db,
        session_id=task.session_id,
        result=result,
    )
    return _serialize_research_task(db_task)


@router.get(
    "/sessions/{session_id}/research-tasks",
    response_model=list[schemas.ResearchTaskResponse],
)
def list_research_tasks(
    session_id: int,
    db: Session = Depends(get_db),
):
    """List persisted research tasks for one session."""
    session = crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return [_serialize_research_task(task) for task in crud.get_research_tasks_by_session(db, session_id)]


@router.get(
    "/research/tasks/{task_id}",
    response_model=schemas.ResearchTaskResponse,
)
def get_research_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    """Get one persisted research task."""
    task = crud.get_research_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")
    return _serialize_research_task(task)


@router.put(
    "/research/tasks/{task_id}",
    response_model=schemas.ResearchTaskResponse,
)
def update_research_task(
    task_id: int,
    payload: schemas.ResearchTaskUpdate,
    db: Session = Depends(get_db),
):
    """Rename a persisted research task."""
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Research query cannot be empty")

    task = crud.update_research_task(
        db,
        task_id,
        query=query,
        report_filename=_slugify_report_filename(query),
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")
    return _serialize_research_task(task)


@router.post(
    "/research/tasks/{task_id}/rerun",
    response_model=schemas.ResearchTaskResponse,
)
async def rerun_research_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    """Rerun a persisted research task and refresh its stored result."""
    task = crud.get_research_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    max_sources = max(1, min(len(json.loads(task.sources_json)) or 3, 5))
    orchestrator = get_research_orchestrator()
    document = _extract_document_from_task(task)
    if document is None:
        result = await orchestrator.run(query=task.query, max_sources=max_sources)
    else:
        result = await orchestrator.run(
            query=task.query,
            max_sources=max_sources,
            document=document,
        )
    updated_task = crud.refresh_research_task(
        db,
        task_id,
        result=result,
    )
    if updated_task is None:
        raise HTTPException(status_code=404, detail="Research task not found")
    return _serialize_research_task(updated_task)


@router.post(
    "/research/tasks/{task_id}/rerun-as-new",
    response_model=schemas.ResearchTaskResponse,
    status_code=201,
)
async def rerun_research_task_as_new(
    task_id: int,
    db: Session = Depends(get_db),
):
    """Rerun a persisted research task and store the result as a new history item."""
    task = crud.get_research_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    max_sources = max(1, min(len(json.loads(task.sources_json)) or 3, 5))
    orchestrator = get_research_orchestrator()
    document = _extract_document_from_task(task)
    if document is None:
        result = await orchestrator.run(query=task.query, max_sources=max_sources)
    else:
        result = await orchestrator.run(
            query=task.query,
            max_sources=max_sources,
            document=document,
        )
    new_task = crud.create_research_task(
        db,
        session_id=task.session_id,
        result=result,
    )
    return _serialize_research_task(new_task)


@router.get(
    "/research/tasks/{task_id}/report",
    response_model=schemas.SessionExportResponse,
)
def export_research_task_report(
    task_id: int,
    db: Session = Depends(get_db),
):
    """Return the persisted research report as a JSON export payload."""
    task = crud.get_research_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")
    return schemas.SessionExportResponse(filename=task.report_filename, content=task.report_markdown)


@router.get("/research/tasks/{task_id}/report/raw")
def export_research_task_report_raw(
    task_id: int,
    db: Session = Depends(get_db),
):
    """Download the persisted research report as raw markdown."""
    task = crud.get_research_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")
    return _build_raw_markdown_response(task.report_filename, task.report_markdown)


@router.post(
    "/research/tasks/{task_id}/share-to-session",
    response_model=schemas.MessageResponse,
    status_code=201,
)
def share_research_task_to_session(
    task_id: int,
    payload: schemas.ResearchShareRequest,
    db: Session = Depends(get_db),
):
    """Append a research brief into its associated session as an assistant message."""
    task = crud.get_research_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")
    if task.session_id is None:
        raise HTTPException(status_code=400, detail="Research task is not associated with a session")

    session = crud.get_session(db, task.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return crud.create_message_direct(
        db,
        session_id=task.session_id,
        role="assistant",
        content=_build_research_message_content(task, mode=payload.mode),
    )


@router.delete("/research/tasks/{task_id}")
def delete_research_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    """Delete one persisted research task."""
    deleted = crud.delete_research_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Research task not found")
    return {"message": "Research task deleted successfully"}


def _slugify_title(title: str) -> str:
    """Generate a stable filename from a session title."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return slug or "session"


def _render_markdown_export(session: schemas.SessionResponse | object, messages: list[object]) -> str:
    """Render a session and its messages as Markdown."""
    lines = [f"# {session.title}", ""]

    for message in messages:
        role = str(message.role).upper()
        lines.append(f"## {role}")
        lines.append("")
        lines.append(message.content)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


@router.get(
    "/sessions/{session_id}/export",
    response_model=schemas.SessionExportResponse,
)
def export_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    """Export a session as Markdown content."""
    session = crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = crud.get_messages_by_session(db, session_id)
    filename = f"{_slugify_title(session.title)}.md"
    return {
        "filename": filename,
        "content": _render_markdown_export(session, messages),
    }


@router.get(
    "/sessions/{session_id}/export/raw",
    response_class=PlainTextResponse,
)
def export_session_raw(
    session_id: int,
    db: Session = Depends(get_db),
):
    """Export a session as downloadable raw Markdown."""
    session = crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    markdown = _render_markdown_export(session, crud.get_messages_by_session(db, session_id))
    filename = f"{_slugify_title(session.title)}.md"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return PlainTextResponse(markdown, headers=headers)


@router.post(
    "/sessions/{session_id}/messages/{message_id}/retry",
    response_model=schemas.MessageResponse,
)
async def retry_message(
    session_id: int,
    message_id: int,
    db: Session = Depends(get_db),
):
    """Retry the latest assistant message in a session."""
    session = crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = crud.get_messages_by_session(db, session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Message not found")

    target_message = next((msg for msg in messages if msg.id == message_id), None)
    if target_message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if target_message.role != "assistant":
        raise HTTPException(status_code=400, detail="Only assistant messages can be retried")
    if messages[-1].id != message_id:
        raise HTTPException(status_code=400, detail="Only the latest assistant message can be retried")

    target_index = next(index for index, msg in enumerate(messages) if msg.id == message_id)
    if target_index == 0:
        raise HTTPException(status_code=400, detail="Retry requires a previous user message")

    prompt_message = messages[target_index - 1]
    if prompt_message.role != "user":
        raise HTTPException(status_code=400, detail="Retry requires a previous user message")

    history = [
        {"role": str(msg.role), "content": msg.content}
        for msg in messages[: target_index - 1]
    ]

    try:
        agent = get_agent()
        updated_content = await agent.ainvoke(prompt_message.content, history)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(exc)}") from exc

    updated_message = crud.update_message_content(db, session_id, message_id, updated_content)
    if updated_message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return updated_message


@router.post("/messages", response_model=schemas.MessageResponse, status_code=201)
def create_message(
    message: schemas.MessageCreate,
    db: Session = Depends(get_db)
):
    """Create a new message."""
    session = crud.get_session(db, message.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return crud.create_message(db, message)


# ========== WebSocket Endpoint ==========

class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, session_id: int, websocket: WebSocket):
        """Accept a new connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: int):
        """Remove a connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, session_id: int, message: dict):
        """Send a message to a specific session."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for streaming chat.

    Protocol:
    - Client sends: {"content": "user message"}
    - Server sends: {"type": "chunk", "content": "response chunk"}
    - Server sends: {"type": "done", "message_id": int, "content": "full response"}
    - Server sends: {"type": "error", "message": "error description"}
    """
    await manager.connect(session_id, websocket)

    try:
        # Verify session exists
        session = crud.get_session(db, session_id)
        if session is None:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            manager.disconnect(session_id)
            await websocket.close()
            return

        while True:
            # Receive message from client
            data = await websocket.receive_json()
            user_content = data.get("content", "")

            if not user_content.strip():
                continue

            # Save user message
            user_msg = crud.create_message_direct(
                db, session_id, "user", user_content
            )

            # Send user message confirmation
            await websocket.send_json({
                "type": "user_message",
                "message_id": user_msg.id,
                "content": user_content
            })

            # Get conversation history
            messages = crud.get_messages_by_session(db, session_id)
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in messages[:-1]  # Exclude the just-added message
            ]

            # Stream agent response
            try:
                agent = get_agent()
                full_response = []

                async for chunk in agent.astream(user_content, history):
                    if chunk:
                        full_response.append(chunk)
                        await websocket.send_json({
                            "type": "chunk",
                            "content": chunk
                        })

                # Save assistant message
                assistant_content = "".join(full_response)
                assistant_msg = crud.create_message_direct(
                    db, session_id, "assistant", assistant_content
                )

                # Send completion
                await websocket.send_json({
                    "type": "done",
                    "message_id": assistant_msg.id,
                    "content": assistant_content
                })

            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Agent error: {str(e)}"
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": f"Server error: {str(e)}"
        })
        manager.disconnect(session_id)
