from base64 import b64encode
from collections.abc import Generator
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.websockets import WebSocketDisconnect

import app.api as api_module
from app.database import Base, get_db
from app.main import app
from app.services.research.orchestrator import ResearchOrchestrator
from app.services.tools import _dedupe_and_sort_sources


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    app.router.lifespan_context = noop_lifespan

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "academic-qa-agent",
    }


def test_session_crud_flow(client: TestClient) -> None:
    create_response = client.post("/api/sessions", json={"title": "Test Session"})

    assert create_response.status_code == 201
    created_session = create_response.json()
    session_id = created_session["id"]
    assert created_session["title"] == "Test Session"
    assert created_session["messages"] == []

    list_response = client.get("/api/sessions")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.put(
        f"/api/sessions/{session_id}",
        json={"title": "Renamed Session"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Renamed Session"

    delete_response = client.delete(f"/api/sessions/{session_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Session deleted successfully"}

    missing_response = client.get(f"/api/sessions/{session_id}")
    assert missing_response.status_code == 404


def test_list_sessions_supports_title_query(client: TestClient) -> None:
    client.post("/api/sessions", json={"title": "Transformers Overview"})
    client.post("/api/sessions", json={"title": "Graph Theory Notes"})

    response = client.get("/api/sessions", params={"query": "transform"})

    assert response.status_code == 200
    assert [session["title"] for session in response.json()] == ["Transformers Overview"]


def test_create_and_list_messages(client: TestClient) -> None:
    session_response = client.post("/api/sessions", json={"title": "Messages"})
    session_id = session_response.json()["id"]

    create_message_response = client.post(
        "/api/messages",
        json={
            "session_id": session_id,
            "role": "user",
            "content": "hello",
        },
    )

    assert create_message_response.status_code == 201
    created_message = create_message_response.json()
    assert created_message["role"] == "user"
    assert created_message["content"] == "hello"

    list_message_response = client.get(f"/api/sessions/{session_id}/messages")
    assert list_message_response.status_code == 200
    assert len(list_message_response.json()) == 1
    assert list_message_response.json()[0]["content"] == "hello"


def test_export_session_returns_markdown_payload(client: TestClient) -> None:
    session_response = client.post("/api/sessions", json={"title": "Export Session"})
    session_id = session_response.json()["id"]
    client.post(
        "/api/messages",
        json={
            "session_id": session_id,
            "role": "user",
            "content": "Summarize this paper",
        },
    )
    client.post(
        "/api/messages",
        json={
            "session_id": session_id,
            "role": "assistant",
            "content": "This paper explores transformers.",
        },
    )

    response = client.get(f"/api/sessions/{session_id}/export")

    assert response.status_code == 200
    assert response.json()["filename"] == "export-session.md"
    assert "# Export Session" in response.json()["content"]
    assert "## USER" in response.json()["content"]
    assert "## ASSISTANT" in response.json()["content"]


def test_create_message_for_missing_session_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/messages",
        json={
            "session_id": 9999,
            "role": "user",
            "content": "hello",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}


def test_websocket_chat_streams_and_persists_messages(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAgent:
        async def astream(self, query: str, history=None):
            assert query == "Explain transformers"
            assert history == []
            yield "Hello"
            yield " world"

    monkeypatch.setattr(api_module, "get_agent", lambda: FakeAgent())

    session_response = client.post("/api/sessions", json={"title": "Streaming"})
    session_id = session_response.json()["id"]

    with client.websocket_connect(f"/api/ws/chat/{session_id}") as websocket:
        websocket.send_json({"content": "Explain transformers"})

        user_message = websocket.receive_json()
        first_chunk = websocket.receive_json()
        second_chunk = websocket.receive_json()
        done_message = websocket.receive_json()

    assert user_message["type"] == "user_message"
    assert user_message["content"] == "Explain transformers"
    assert first_chunk == {"type": "chunk", "content": "Hello"}
    assert second_chunk == {"type": "chunk", "content": " world"}
    assert done_message["type"] == "done"
    assert done_message["content"] == "Hello world"

    messages_response = client.get(f"/api/sessions/{session_id}/messages")
    assert messages_response.status_code == 200
    assert messages_response.json() == [
        {
            "id": 1,
            "session_id": session_id,
            "role": "user",
            "content": "Explain transformers",
            "created_at": messages_response.json()[0]["created_at"],
        },
        {
            "id": 2,
            "session_id": session_id,
            "role": "assistant",
            "content": "Hello world",
            "created_at": messages_response.json()[1]["created_at"],
        },
    ]


def test_websocket_missing_session_returns_error_and_closes(client: TestClient) -> None:
    with client.websocket_connect("/api/ws/chat/9999") as websocket:
        error_message = websocket.receive_json()

        assert error_message == {"type": "error", "message": "Session not found"}

        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_websocket_agent_error_returns_error_and_keeps_user_message(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingAgent:
        async def astream(self, query: str, history=None):
            raise RuntimeError("mock failure")
            yield query  # pragma: no cover

    monkeypatch.setattr(api_module, "get_agent", lambda: FailingAgent())

    session_response = client.post("/api/sessions", json={"title": "Streaming error"})
    session_id = session_response.json()["id"]

    with client.websocket_connect(f"/api/ws/chat/{session_id}") as websocket:
        websocket.send_json({"content": "Trigger error"})

        user_message = websocket.receive_json()
        error_message = websocket.receive_json()

    assert user_message["type"] == "user_message"
    assert user_message["content"] == "Trigger error"
    assert error_message == {
        "type": "error",
        "message": "Agent error: mock failure",
    }

    messages_response = client.get(f"/api/sessions/{session_id}/messages")
    assert messages_response.status_code == 200
    assert len(messages_response.json()) == 1
    assert messages_response.json()[0]["role"] == "user"
    assert messages_response.json()[0]["content"] == "Trigger error"


def test_websocket_uses_display_content_for_persisted_user_message(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_prompt = "Use research context\n\nFollow-up question: What changed after 2024?"

    class FakeAgent:
        async def astream(self, query: str, history=None):
            assert query == expected_prompt
            assert history == []
            yield "Context-aware"
            yield " answer"

    monkeypatch.setattr(api_module, "get_agent", lambda: FakeAgent())

    session_response = client.post("/api/sessions", json={"title": "Research follow-up"})
    session_id = session_response.json()["id"]

    with client.websocket_connect(f"/api/ws/chat/{session_id}") as websocket:
        websocket.send_json({
            "content": expected_prompt,
            "display_content": "What changed after 2024?",
        })

        user_message = websocket.receive_json()
        first_chunk = websocket.receive_json()
        second_chunk = websocket.receive_json()
        done_message = websocket.receive_json()

    assert user_message == {
        "type": "user_message",
        "message_id": 1,
        "content": "What changed after 2024?",
    }
    assert first_chunk == {"type": "chunk", "content": "Context-aware"}
    assert second_chunk == {"type": "chunk", "content": " answer"}
    assert done_message["type"] == "done"
    assert done_message["content"] == "Context-aware answer"

    messages_response = client.get(f"/api/sessions/{session_id}/messages")
    assert messages_response.status_code == 200
    assert messages_response.json()[0]["content"] == "What changed after 2024?"
    assert messages_response.json()[1]["content"] == "Context-aware answer"


def test_retry_latest_assistant_message_updates_content(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAgent:
        async def ainvoke(self, query: str, history=None):
            assert query == "Original prompt"
            assert history == []
            return "Retried answer"

    monkeypatch.setattr(api_module, "get_agent", lambda: FakeAgent())

    session_response = client.post("/api/sessions", json={"title": "Retry Session"})
    session_id = session_response.json()["id"]
    client.post(
        "/api/messages",
        json={
            "session_id": session_id,
            "role": "user",
            "content": "Original prompt",
        },
    )
    assistant_response = client.post(
        "/api/messages",
        json={
            "session_id": session_id,
            "role": "assistant",
            "content": "Original answer",
        },
    )
    assistant_id = assistant_response.json()["id"]

    retry_response = client.post(f"/api/sessions/{session_id}/messages/{assistant_id}/retry")

    assert retry_response.status_code == 200
    assert retry_response.json()["content"] == "Retried answer"

    messages_response = client.get(f"/api/sessions/{session_id}/messages")
    assert messages_response.status_code == 200
    assert messages_response.json()[1]["content"] == "Retried answer"


def test_retry_rejects_non_latest_assistant_message(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAgent:
        async def ainvoke(self, query: str, history=None):
            return "Should not be used"

    monkeypatch.setattr(api_module, "get_agent", lambda: FakeAgent())

    session_response = client.post("/api/sessions", json={"title": "Retry Guard"})
    session_id = session_response.json()["id"]
    client.post(
        "/api/messages",
        json={
            "session_id": session_id,
            "role": "user",
            "content": "First prompt",
        },
    )
    first_assistant = client.post(
        "/api/messages",
        json={
            "session_id": session_id,
            "role": "assistant",
            "content": "First answer",
        },
    )
    client.post(
        "/api/messages",
        json={
            "session_id": session_id,
            "role": "user",
            "content": "Second prompt",
        },
    )
    client.post(
        "/api/messages",
        json={
            "session_id": session_id,
            "role": "assistant",
            "content": "Second answer",
        },
    )

    retry_response = client.post(
        f"/api/sessions/{session_id}/messages/{first_assistant.json()['id']}/retry"
    )

    assert retry_response.status_code == 400
    assert retry_response.json()["detail"] == "Only the latest assistant message can be retried"


def test_research_task_returns_structured_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResearchOrchestrator:
        async def run(self, query: str, max_sources: int = 3):
            return {
                "query": query,
                "status": "completed",
                "generated_at": "2026-03-19T10:00:00Z",
                "report_filename": "research-brief-graph-neural-networks.md",
                "plan": ["Understand the topic", "Retrieve papers", "Write brief"],
                "sources": [
                    {
                        "source_id": "arxiv-1",
                        "citation_label": "S1",
                        "title": "Graph Neural Networks",
                        "authors": ["Author A", "Author B"],
                        "abstract": "A paper about graph neural networks.",
                        "published_at": "2024-01-01T00:00:00Z",
                        "url": "https://arxiv.org/abs/1234.5678",
                        "pdf_url": "https://arxiv.org/pdf/1234.5678.pdf",
                        "source_type": "arxiv",
                        "score": max_sources,
                    },
                    {
                        "source_id": "crossref-1",
                        "citation_label": "S2",
                        "title": "Metadata Record",
                        "authors": ["Curator A"],
                        "abstract": "A Crossref metadata record for the same topic.",
                        "published_at": "2023-02-01T00:00:00Z",
                        "url": "https://doi.org/10.1000/metadata",
                        "pdf_url": None,
                        "journal_ref": "Metadata Journal",
                        "doi": "10.1000/metadata",
                        "source_type": "crossref",
                        "score": 1,
                    }
                ],
                "answer": "This field summarizes the research topic.",
                "report_markdown": "# Research Brief\n",
            }

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    session_response = client.post("/api/sessions", json={"title": "Research Session"})
    session_id = session_response.json()["id"]

    response = client.post(
        "/api/research/tasks",
        json={"query": "graph neural networks", "max_sources": 2, "session_id": session_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] > 0
    assert payload["session_id"] == session_id
    assert payload["query"] == "graph neural networks"
    assert payload["status"] == "completed"
    assert payload["report_filename"] == "research-brief-graph-neural-networks.md"
    assert payload["plan"] == ["Understand the topic", "Retrieve papers", "Write brief"]
    assert payload["phase_statuses"][0]["phase"] == "planning"
    assert payload["phase_statuses"][-1]["phase"] == "completed"
    assert payload["sources"][0]["citation_label"] == "S1"
    assert payload["sources"][0]["title"] == "Graph Neural Networks"
    assert payload["sources"][1]["source_type"] == "crossref"
    assert payload["answer"] == "This field summarizes the research topic."

    list_response = client.get(f"/api/sessions/{session_id}/research-tasks")
    assert list_response.status_code == 200
    tasks = list_response.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == payload["id"]
    assert tasks[0]["query"] == "graph neural networks"

    detail_response = client.get(f"/api/research/tasks/{payload['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["session_id"] == session_id


def test_research_task_accepts_local_document_context(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_document: dict[str, str] = {}

    class FakeResearchOrchestrator:
        async def run(
            self,
            query: str,
            max_sources: int = 3,
            document: dict[str, str] | None = None,
        ):
            assert query == "summarize the uploaded notes"
            assert max_sources == 2
            assert document is not None
            seen_document.update(document)
            return {
                "query": query,
                "status": "completed",
                "generated_at": "2026-03-19T10:00:00Z",
                "report_filename": "uploaded-notes.md",
                "plan": ["Read the local document", "Retrieve supporting papers", "Write brief"],
                "sources": [
                    {
                        "source_id": "local-document-1",
                        "citation_label": "S1",
                        "title": "notes.md",
                        "authors": [],
                        "abstract": "Document body.",
                        "published_at": "2026-03-19T10:00:00Z",
                        "url": "local://notes.md",
                        "source_type": "local_document",
                        "score": 100,
                        "document_text": "Document body.",
                        "document_filename": "notes.md",
                    }
                ],
                "answer": "The uploaded notes focus on local evidence. [S1]",
                "report_markdown": "# Research Brief\n\nThe uploaded notes focus on local evidence. [S1]\n",
            }

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    response = client.post(
        "/api/research/tasks",
        json={
            "query": "summarize the uploaded notes",
            "max_sources": 2,
            "document": {
                "filename": "notes.md",
                "mime_type": "text/markdown",
                "content_base64": b64encode(b"Document body.").decode("ascii"),
            },
        },
    )

    assert response.status_code == 200
    assert seen_document["filename"] == "notes.md"
    assert seen_document["text"] == "Document body."
    assert response.json()["sources"][0]["source_type"] == "local_document"
    assert response.json()["sources"][0]["title"] == "notes.md"


def test_research_task_rejects_unsupported_document_type(client: TestClient) -> None:
    response = client.post(
        "/api/research/tasks",
        json={
            "query": "summarize spreadsheet",
            "document": {
                "filename": "notes.csv",
                "mime_type": "text/csv",
                "content_base64": b64encode(b"col1,col2").decode("ascii"),
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported document type. Please upload TXT, MD, or PDF"


def test_research_task_rejects_empty_query(client: TestClient) -> None:
    response = client.post(
        "/api/research/tasks",
        json={"query": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Research query cannot be empty"


def test_research_task_rejects_unknown_session(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResearchOrchestrator:
        async def run(self, query: str, max_sources: int = 3):
            raise AssertionError("should not be called")

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    response = client.post(
        "/api/research/tasks",
        json={"query": "transformers", "session_id": 9999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_research_task_returns_structured_failure_detail(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResearchOrchestrator:
        async def run(self, query: str, max_sources: int = 3):
            raise RuntimeError("upstream timeout")

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    response = client.post(
        "/api/research/tasks",
        json={"query": "transformer interpretability"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == {
        "code": "research_execution_failed",
        "message": "Research task execution failed",
        "reason": "RuntimeError",
        "recovery_hint": "retry_or_adjust_query",
        "retryable": True,
        "operation": "run",
        "query": "transformer interpretability",
    }


def test_update_research_task_renames_query_and_report_filename(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResearchOrchestrator:
        async def run(self, query: str, max_sources: int = 3):
            return {
                "query": query,
                "status": "completed",
                "generated_at": "2026-03-19T10:00:00Z",
                "report_filename": "research-brief-graph-neural-networks.md",
                "plan": ["Understand the topic"],
                "sources": [],
                "answer": "Structured answer. [S1]",
                "report_markdown": "# Research Brief\n",
            }

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    session_response = client.post("/api/sessions", json={"title": "Research Session"})
    session_id = session_response.json()["id"]
    task_response = client.post(
        "/api/research/tasks",
        json={"query": "graph neural networks", "session_id": session_id},
    )
    task_id = task_response.json()["id"]

    update_response = client.put(
        f"/api/research/tasks/{task_id}",
        json={"query": "molecular graph learning"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["query"] == "molecular graph learning"
    assert update_response.json()["report_filename"] == "research-brief-molecular-graph-learning.md"

    detail_response = client.get(f"/api/research/tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["query"] == "molecular graph learning"


def test_update_research_task_rejects_empty_query(client: TestClient) -> None:
    response = client.put("/api/research/tasks/1", json={"query": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Research query cannot be empty"


def test_rerun_research_task_refreshes_persisted_result(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_max_sources = iter([3, 1])
    answers = iter([
        {
            "query": "graph neural networks",
            "status": "completed",
            "generated_at": "2026-03-19T10:00:00Z",
            "report_filename": "research-brief-graph-neural-networks.md",
            "plan": ["Understand the topic"],
            "sources": [
                {
                    "source_id": "arxiv-1",
                    "citation_label": "S1",
                    "title": "Graph Neural Networks",
                    "authors": ["Author A"],
                    "abstract": "Initial abstract.",
                    "published_at": "2024-01-01T00:00:00Z",
                    "url": "https://arxiv.org/abs/1234.5678",
                    "pdf_url": "https://arxiv.org/pdf/1234.5678.pdf",
                    "source_type": "arxiv",
                    "score": 3,
                }
            ],
            "answer": "Initial answer. [S1]",
            "report_markdown": "# Research Brief: graph neural networks\n\nInitial answer. [S1]\n",
        },
        {
            "query": "graph neural networks",
            "status": "completed",
            "generated_at": "2026-03-19T10:05:00Z",
            "report_filename": "research-brief-graph-neural-networks.md",
            "plan": ["Refresh the topic"],
            "sources": [
                {
                    "source_id": "arxiv-2",
                    "citation_label": "S1",
                    "title": "Updated Graph Neural Networks",
                    "authors": ["Author B"],
                    "abstract": "Updated abstract.",
                    "published_at": "2025-01-01T00:00:00Z",
                    "url": "https://arxiv.org/abs/2345.6789",
                    "pdf_url": "https://arxiv.org/pdf/2345.6789.pdf",
                    "source_type": "arxiv",
                    "score": 3,
                }
            ],
            "answer": "Updated answer. [S1]",
            "report_markdown": "# Research Brief: graph neural networks\n\nUpdated answer. [S1]\n",
        },
    ])

    class FakeResearchOrchestrator:
        async def run(self, query: str, max_sources: int = 3):
            assert query == "graph neural networks"
            assert max_sources == next(expected_max_sources)
            return next(answers)

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    session_response = client.post("/api/sessions", json={"title": "Research Session"})
    session_id = session_response.json()["id"]
    task_response = client.post(
        "/api/research/tasks",
        json={"query": "graph neural networks", "session_id": session_id},
    )
    task_id = task_response.json()["id"]

    rerun_response = client.post(f"/api/research/tasks/{task_id}/rerun")

    assert rerun_response.status_code == 200
    assert rerun_response.json()["id"] == task_id
    assert rerun_response.json()["answer"] == "Updated answer. [S1]"
    assert rerun_response.json()["plan"] == ["Refresh the topic"]
    assert rerun_response.json()["sources"][0]["title"] == "Updated Graph Neural Networks"


def test_rerun_research_task_preserves_local_document_context(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_documents: list[dict[str, str] | None] = []
    answers = iter([
        {
            "query": "uploaded research",
            "status": "completed",
            "generated_at": "2026-03-19T10:00:00Z",
            "report_filename": "uploaded-research.md",
            "plan": ["Read local document"],
            "sources": [
                {
                    "source_id": "local-document-1",
                    "citation_label": "S1",
                    "title": "notes.md",
                    "authors": [],
                    "abstract": "Initial local text.",
                    "published_at": "2026-03-19T10:00:00Z",
                    "url": "local://notes.md",
                    "source_type": "local_document",
                    "score": 100,
                    "document_text": "Initial local text.",
                    "document_filename": "notes.md",
                }
            ],
            "answer": "Initial local answer. [S1]",
            "report_markdown": "# Research Brief: uploaded research\n\nInitial local answer. [S1]\n",
        },
        {
            "query": "uploaded research",
            "status": "completed",
            "generated_at": "2026-03-19T10:05:00Z",
            "report_filename": "uploaded-research.md",
            "plan": ["Re-read local document"],
            "sources": [
                {
                    "source_id": "local-document-1",
                    "citation_label": "S1",
                    "title": "notes.md",
                    "authors": [],
                    "abstract": "Updated local text.",
                    "published_at": "2026-03-19T10:05:00Z",
                    "url": "local://notes.md",
                    "source_type": "local_document",
                    "score": 100,
                    "document_text": "Initial local text.",
                    "document_filename": "notes.md",
                }
            ],
            "answer": "Updated local answer. [S1]",
            "report_markdown": "# Research Brief: uploaded research\n\nUpdated local answer. [S1]\n",
        },
    ])

    class FakeResearchOrchestrator:
        async def run(
            self,
            query: str,
            max_sources: int = 3,
            document: dict[str, str] | None = None,
        ):
            seen_documents.append(document)
            return next(answers)

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    task_response = client.post(
        "/api/research/tasks",
        json={
            "query": "uploaded research",
            "document": {
                "filename": "notes.md",
                "mime_type": "text/markdown",
                "content_base64": b64encode(b"Initial local text.").decode("ascii"),
            },
        },
    )
    task_id = task_response.json()["id"]

    rerun_response = client.post(f"/api/research/tasks/{task_id}/rerun")

    assert rerun_response.status_code == 200
    assert seen_documents[0]["filename"] == "notes.md"
    assert seen_documents[1]["text"] == "Initial local text."
    assert rerun_response.json()["answer"] == "Updated local answer. [S1]"


def test_rerun_research_task_as_new_creates_new_history_item(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter([
        {
            "query": "graph neural networks",
            "status": "completed",
            "generated_at": "2026-03-19T10:00:00Z",
            "report_filename": "research-brief-graph-neural-networks.md",
            "plan": ["Understand the topic"],
            "sources": [
                {
                    "source_id": "arxiv-1",
                    "citation_label": "S1",
                    "title": "Graph Neural Networks",
                    "authors": ["Author A"],
                    "abstract": "Initial abstract.",
                    "published_at": "2024-01-01T00:00:00Z",
                    "url": "https://arxiv.org/abs/1234.5678",
                    "pdf_url": "https://arxiv.org/pdf/1234.5678.pdf",
                    "source_type": "arxiv",
                    "score": 3,
                }
            ],
            "answer": "Initial answer. [S1]",
            "report_markdown": "# Research Brief: graph neural networks\n\nInitial answer. [S1]\n",
        },
        {
            "query": "graph neural networks",
            "status": "completed",
            "generated_at": "2026-03-19T10:10:00Z",
            "report_filename": "research-brief-graph-neural-networks.md",
            "plan": ["Explore more recent papers"],
            "sources": [
                {
                    "source_id": "arxiv-3",
                    "citation_label": "S1",
                    "title": "Fresh Graph Neural Networks",
                    "authors": ["Author C"],
                    "abstract": "Fresh abstract.",
                    "published_at": "2026-01-01T00:00:00Z",
                    "url": "https://arxiv.org/abs/3456.7890",
                    "pdf_url": "https://arxiv.org/pdf/3456.7890.pdf",
                    "source_type": "arxiv",
                    "score": 3,
                }
            ],
            "answer": "Fresh answer. [S1]",
            "report_markdown": "# Research Brief: graph neural networks\n\nFresh answer. [S1]\n",
        },
    ])
    expected_max_sources = iter([3, 1])

    class FakeResearchOrchestrator:
        async def run(self, query: str, max_sources: int = 3):
            assert query == "graph neural networks"
            assert max_sources == next(expected_max_sources)
            return next(answers)

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    session_response = client.post("/api/sessions", json={"title": "Research Session"})
    session_id = session_response.json()["id"]
    task_response = client.post(
        "/api/research/tasks",
        json={"query": "graph neural networks", "session_id": session_id},
    )
    original_task_id = task_response.json()["id"]

    rerun_response = client.post(f"/api/research/tasks/{original_task_id}/rerun-as-new")

    assert rerun_response.status_code == 201
    assert rerun_response.json()["id"] != original_task_id
    assert rerun_response.json()["answer"] == "Fresh answer. [S1]"

    history_response = client.get(f"/api/sessions/{session_id}/research-tasks")
    assert history_response.status_code == 200
    assert len(history_response.json()) == 2


def test_share_research_task_to_session_creates_assistant_message(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResearchOrchestrator:
        async def run(self, query: str, max_sources: int = 3):
            return {
                "query": query,
                "status": "completed",
                "generated_at": "2026-03-19T10:00:00Z",
                "report_filename": "transformers.md",
                "plan": ["Collect sources"],
                "sources": [
                    {
                        "source_id": "arxiv-1",
                        "citation_label": "S1",
                        "title": "Attention Is All You Need",
                        "authors": ["Author A"],
                        "abstract": "Transformer paper.",
                        "published_at": "2017-06-01T00:00:00Z",
                        "url": "https://arxiv.org/abs/1706.03762",
                        "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
                        "source_type": "arxiv",
                        "score": max_sources,
                    }
                ],
                "answer": "Transformers improve sequence modeling. [S1]",
                "report_markdown": "# Research Brief\n",
            }

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    session_response = client.post("/api/sessions", json={"title": "Research Session"})
    session_id = session_response.json()["id"]
    task_response = client.post(
        "/api/research/tasks",
        json={"query": "transformers", "session_id": session_id},
    )
    task_id = task_response.json()["id"]

    share_response = client.post(
        f"/api/research/tasks/{task_id}/share-to-session",
        json={"mode": "summary"},
    )

    assert share_response.status_code == 201
    payload = share_response.json()
    assert payload["session_id"] == session_id
    assert payload["role"] == "assistant"
    assert "Research Brief: transformers" in payload["content"]
    assert "[S1] Attention Is All You Need" in payload["content"]

    full_share_response = client.post(
        f"/api/research/tasks/{task_id}/share-to-session",
        json={"mode": "full"},
    )
    assert full_share_response.status_code == 201
    assert full_share_response.json()["content"] == "# Research Brief"


def test_export_research_task_report_returns_json_and_raw_markdown(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResearchOrchestrator:
        async def run(self, query: str, max_sources: int = 3):
            return {
                "query": query,
                "status": "completed",
                "generated_at": "2026-03-19T10:00:00Z",
                "report_filename": "research-brief-graph-neural-networks.md",
                "plan": ["Understand the topic"],
                "sources": [
                    {
                        "source_id": "arxiv-1",
                        "citation_label": "S1",
                        "title": "Graph Neural Networks",
                        "authors": ["Author A"],
                        "abstract": "A paper about graph neural networks.",
                        "published_at": "2024-01-01T00:00:00Z",
                        "url": "https://arxiv.org/abs/1234.5678",
                        "pdf_url": "https://arxiv.org/pdf/1234.5678.pdf",
                        "source_type": "arxiv",
                        "score": max_sources,
                    }
                ],
                "answer": "Graph neural networks improve graph representation learning. [S1]",
                "report_markdown": (
                    "# Research Brief: graph neural networks\n\n"
                    "## Report Snapshot\n\n"
                    "- Generated: 2026-03-19 10:00 UTC\n"
                    "- Research Question: graph neural networks\n"
                    "- Grounding Mode: External research sources only\n"
                    "- Total Sources: 1\n"
                    "- Evidence-Linked Claims: 1\n\n"
                    "## Key Takeaways\n\n"
                    "- Graph neural networks improve graph representation learning. [S1]\n\n"
                    "## Research Plan\n\n"
                    "1. Understand the topic\n\n"
                    "## Source Catalogue\n\n"
                    "### [S1] Graph Neural Networks\n\n"
                    "- Authors: Author A\n"
                    "- Published: 2024-01-01\n"
                    "- Citation: N/A\n"
                    "- Source Type: arxiv\n"
                    "- arXiv ID: N/A\n"
                    "- Primary Category: N/A\n"
                    "- Categories: N/A\n"
                    "- Journal Ref: N/A\n"
                    "- DOI: N/A\n"
                    "- URL: https://arxiv.org/abs/1234.5678\n"
                    "- PDF: https://arxiv.org/pdf/1234.5678.pdf\n\n"
                    "A paper about graph neural networks.\n\n"
                    "## Evidence Map\n\n"
                    "- Graph neural networks improve graph representation learning. [S1]\n\n"
                    "## Full Synthesis\n\n"
                    "Graph neural networks improve graph representation learning. [S1]\n"
                ),
            }

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    session_response = client.post("/api/sessions", json={"title": "Research Session"})
    session_id = session_response.json()["id"]
    task_response = client.post(
        "/api/research/tasks",
        json={"query": "graph neural networks", "session_id": session_id},
    )
    task_id = task_response.json()["id"]

    export_response = client.get(f"/api/research/tasks/{task_id}/report")
    assert export_response.status_code == 200
    assert export_response.json()["filename"] == "research-brief-graph-neural-networks.md"
    assert "[S1]" in export_response.json()["content"]
    assert "## Report Snapshot" in export_response.json()["content"]
    assert "## Key Takeaways" in export_response.json()["content"]
    assert "## Source Catalogue" in export_response.json()["content"]

    raw_export_response = client.get(f"/api/research/tasks/{task_id}/report/raw")
    assert raw_export_response.status_code == 200
    assert raw_export_response.text.startswith("# Research Brief: graph neural networks")
    assert "## Full Synthesis" in raw_export_response.text
    assert raw_export_response.headers["content-disposition"] == (
        'attachment; filename="research-brief-graph-neural-networks.md"'
    )


def test_export_research_task_report_returns_404_for_unknown_task(client: TestClient) -> None:
    response = client.get("/api/research/tasks/9999/report")

    assert response.status_code == 404
    assert response.json()["detail"] == "Research task not found"


def test_delete_research_task_removes_persisted_record(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResearchOrchestrator:
        async def run(self, query: str, max_sources: int = 3):
            return {
                "query": query,
                "status": "completed",
                "generated_at": "2026-03-19T10:00:00Z",
                "report_filename": "history.md",
                "plan": ["Collect sources"],
                "sources": [],
                "answer": "History payload",
                "report_markdown": "# Research Brief",
            }

    monkeypatch.setattr(api_module, "get_research_orchestrator", lambda: FakeResearchOrchestrator())

    session_response = client.post("/api/sessions", json={"title": "Research Session"})
    session_id = session_response.json()["id"]
    task_response = client.post(
        "/api/research/tasks",
        json={"query": "history cleanup", "session_id": session_id},
    )
    task_id = task_response.json()["id"]

    delete_response = client.delete(f"/api/research/tasks/{task_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Research task deleted successfully"

    detail_response = client.get(f"/api/research/tasks/{task_id}")
    assert detail_response.status_code == 404


def test_source_dedup_and_sort_prefers_high_score_and_recent_date() -> None:
    deduped = _dedupe_and_sort_sources(
        [
            {
                "source_id": "arxiv-1",
                "arxiv_id": "2401.00001",
                "title": "Same Paper",
                "published_at": "2024-01-01T00:00:00Z",
                "score": 2,
            },
            {
                "source_id": "arxiv-2",
                "arxiv_id": "2401.00001",
                "title": "Same Paper",
                "published_at": "2024-02-01T00:00:00Z",
                "score": 3,
            },
            {
                "source_id": "arxiv-3",
                "arxiv_id": "2402.00002",
                "title": "Another Paper",
                "published_at": "2023-12-01T00:00:00Z",
                "score": 1,
            },
        ]
    )

    assert len(deduped) == 2
    assert deduped[0]["source_id"] == "arxiv-2"
    assert deduped[1]["source_id"] == "arxiv-3"


def test_research_orchestrator_normalizes_inline_citations() -> None:
    orchestrator = ResearchOrchestrator()

    normalized = orchestrator._ensure_source_citations(
        "The method improves retrieval quality with S1 and [ S2 ].",
        [
            {"citation_label": "S1"},
            {"citation_label": "S2"},
        ],
    )

    assert normalized == "The method improves retrieval quality with [S1] and [S2]."


def test_research_orchestrator_appends_fallback_citations_when_missing() -> None:
    orchestrator = ResearchOrchestrator()

    normalized = orchestrator._ensure_source_citations(
        "The papers consistently show improved graph representation learning.",
        [
            {"citation_label": "S1"},
            {"citation_label": "S2"},
        ],
    )

    assert normalized == "The papers consistently show improved graph representation learning. [S1] [S2]"


def test_research_orchestrator_removes_unknown_citations() -> None:
    orchestrator = ResearchOrchestrator()

    normalized = orchestrator._ensure_source_citations(
        "The evidence favors sparse routing [S9].",
        [
            {"citation_label": "S1"},
            {"citation_label": "S2"},
        ],
    )

    assert "[S9]" not in normalized
    assert "[S1]" in normalized


def test_research_orchestrator_enforces_claim_level_citations() -> None:
    orchestrator = ResearchOrchestrator()

    normalized = orchestrator._ensure_source_citations(
        "Graph methods improve reasoning. Transformer methods scale well.",
        [
            {"citation_label": "S1"},
            {"citation_label": "S2"},
        ],
    )

    assert "Graph methods improve reasoning. [S1] [S2]" in normalized
    assert "Transformer methods scale well. [S1] [S2]" in normalized


def test_research_orchestrator_builds_evidence_map_from_answer() -> None:
    orchestrator = ResearchOrchestrator()

    evidence_map = orchestrator.build_evidence_map(
        "Graph methods improve reasoning [S1]. Transformer methods scale well [S2].",
        [
            {"citation_label": "S1", "title": "Graph Paper"},
            {"citation_label": "S2", "title": "Transformer Paper"},
        ],
    )

    assert evidence_map == [
        {
            "claim": "Graph methods improve reasoning",
            "citation_labels": ["S1"],
            "source_titles": ["Graph Paper"],
        },
        {
            "claim": "Transformer methods scale well",
            "citation_labels": ["S2"],
            "source_titles": ["Transformer Paper"],
        },
    ]


def test_research_orchestrator_retrieves_mixed_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orchestrator = ResearchOrchestrator()

    monkeypatch.setattr(
        "app.services.research.orchestrator.search_arxiv_papers",
        lambda query, max_results=5: [
            {
                "source_id": "arxiv-1",
                "title": "Graph Neural Networks",
                "authors": ["Author A"],
                "abstract": "Primary paper.",
                "published_at": "2024-01-01T00:00:00Z",
                "url": "https://arxiv.org/abs/1234.5678",
                "pdf_url": "https://arxiv.org/pdf/1234.5678.pdf",
                "source_type": "arxiv",
                "score": max_results,
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.research.orchestrator.search_crossref_records",
        lambda query, max_results=2: [
            {
                "source_id": "crossref-1",
                "title": "Metadata Record",
                "authors": ["Curator A"],
                "abstract": "Supplementary metadata.",
                "published_at": "2023-02-01T00:00:00Z",
                "url": "https://doi.org/10.1000/metadata",
                "pdf_url": None,
                "journal_ref": "Metadata Journal",
                "doi": "10.1000/metadata",
                "source_type": "crossref",
                "score": max_results,
            }
        ],
    )

    sources = orchestrator.retrieve_sources("graph neural networks", max_sources=3)

    assert len(sources) == 2
    assert any(source["source_type"] == "arxiv" for source in sources)
    assert any(source["source_type"] == "crossref" for source in sources)
