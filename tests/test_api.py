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
