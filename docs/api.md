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
  "session_id": 1,
  "document": {
    "filename": "notes.md",
    "mime_type": "text/markdown",
    "content_base64": "RG9jdW1lbnQgYm9keS4uLg=="
  }
}
```

- `document` is optional.
- Supported document types:
  - `TXT`
  - `MD` / `Markdown`
  - `PDF` when the optional `pypdf` dependency is available in the runtime
- Local documents are injected as a first-class research source and persisted with the task so that reruns keep the same local context.

- Returns one `ResearchTaskResponse` with:
  - `id`
  - `session_id`
  - `query`
  - `status`
  - `generated_at`
  - `report_filename`
  - `plan`
  - `phase_statuses`
  - `sources`
  - `evidence_map`
  - `answer`
  - `report_markdown`

Constraints:

- `query` cannot be empty.
- `max_sources` is clamped to `1..5`.
- `session_id`, when provided, must exist.
- Unsupported or unreadable document payloads return `400`.

`GET /api/sessions/{session_id}/research-tasks`

- Lists persisted research tasks for one session, newest first.

`GET /api/research/tasks/{task_id}`

- Returns one persisted research task.

`PUT /api/research/tasks/{task_id}`

- Renames one persisted research task by updating its `query`.
- Keeps `report_filename` aligned with the new task name.

Example:

```json
{
  "query": "molecular graph learning"
}
```

`POST /api/research/tasks/{task_id}/rerun`

- Re-executes one persisted research task using its current query.
- Refreshes the stored `plan`, `sources`, `answer`, and `report_markdown` in place.

`POST /api/research/tasks/{task_id}/rerun-as-new`

- Re-executes one persisted research task using its current query.
- Stores the result as a new research history item, keeping the original task unchanged.

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
- Unknown citations are stripped when they do not map to the current source set.
- Claim segments without citations are backfilled with fallback source markers so each answer segment remains source-backed.
- `evidence_map` provides a structured list of claims, citation labels, and source titles for UI rendering.
- `phase_statuses` provides completed workflow phase summaries for planning, retrieval, synthesis, and final completion.

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
