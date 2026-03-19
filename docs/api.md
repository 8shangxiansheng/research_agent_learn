# API Reference

This project exposes a REST API for session management, research tasks, message management, and a WebSocket endpoint for streaming assistant responses.

## REST Endpoints

### Sessions

`GET /api/sessions`

- Lists sessions ordered by recency.
- Supports an optional `query` parameter for case-insensitive title filtering.
- Existing callers remain compatible when `query` is omitted.

Example:

```http
GET /api/sessions?query=transform
```

`POST /api/sessions`

- Creates a new session.

`GET /api/sessions/{session_id}`

- Returns one session with its messages.

`PUT /api/sessions/{session_id}`

- Renames a session.

`DELETE /api/sessions/{session_id}`

- Deletes the session and its messages.

### Messages

`GET /api/sessions/{session_id}/messages`

- Lists all messages for one session.

`POST /api/messages`

- Creates a new persisted message.

### Markdown Export

`GET /api/sessions/{session_id}/export`

- Returns a JSON payload:

```json
{
  "filename": "example-session.md",
  "content": "# Example Session\n\n## USER\n\n..."
}
```

`GET /api/sessions/{session_id}/export/raw`

- Returns plain text Markdown with a download-friendly `Content-Disposition` header.

### Retry

`POST /api/sessions/{session_id}/messages/{message_id}/retry`

- Re-generates the target assistant message using the preceding user message and earlier history.
- Updates the existing assistant message content in place.

Constraints:

- The target message must exist.
- The target message must be an `assistant` message.
- The target message must be the latest assistant message in the session.

Possible error cases:

- `404 Session not found`
- `404 Message not found`
- `400 Only assistant messages can be retried`
- `400 Only the latest assistant message can be retried`
- `400 Retry requires a previous user message`
- `500 Retry failed: ...`

### Research Tasks

`POST /api/research/tasks`

- Runs the persisted research workflow for one query.
- Stores the resulting `plan`, `sources`, `answer`, and `report_markdown`.
- Accepts:

```json
{
  "query": "graph neural networks for molecules",
  "max_sources": 3,
  "session_id": 1
}
```

- Returns one `ResearchTaskResponse` with:
  - `id`
  - `session_id`
  - `query`
  - `status`
  - `generated_at`
  - `report_filename`
  - `plan`
  - `sources`
  - `answer`
  - `report_markdown`

Constraints:

- `query` cannot be empty.
- `max_sources` is clamped to `1..5`.
- `session_id`, when provided, must exist.

`GET /api/sessions/{session_id}/research-tasks`

- Lists persisted research tasks for one session, newest first.

`GET /api/research/tasks/{task_id}`

- Returns one persisted research task.

`GET /api/research/tasks/{task_id}/report`

- Returns a JSON payload:

```json
{
  "filename": "graph-neural-networks.md",
  "content": "# Research Brief: graph neural networks\n..."
}
```

`GET /api/research/tasks/{task_id}/report/raw`

- Returns plain text Markdown with a download-friendly `Content-Disposition` header.

`POST /api/research/tasks/{task_id}/share-to-session`

- Appends the persisted research result into its associated chat session as an `assistant` message.
- Accepts:

```json
{
  "mode": "summary"
}
```

- `mode` supports:
  - `summary`: injects the synthesized answer plus top sources
  - `full`: injects the full `report_markdown`

Possible error cases:

- `404 Research task not found`
- `400 Research task is not associated with a session`
- `404 Session not found`

`DELETE /api/research/tasks/{task_id}`

- Deletes one persisted research task.

### Research Output Rules

- Source entries include stable labels such as `S1`, `S2`, and `S3`.
- Research answers should cite claims inline using `[S1]` style markers.
- When the model omits citations, the backend appends an `Evidence basis:` fallback line to preserve source traceability.

## WebSocket

`/api/ws/chat/{session_id}`

Client payload:

```json
{ "content": "user message" }
```

Server event sequence:

1. `user_message`
2. one or more `chunk`
3. `done`

Error payload:

```json
{ "type": "error", "message": "Agent error: ..." }
```
