# Academic Q&A Agent

A full-stack application for academic paper research and Q&A, powered by LangChain and DeepSeek LLM.

## Features

- Multi-session chat interface for organizing research conversations
- Built-in Chinese and English UI toggle with persisted locale preference
- Research task workflow with plan, sources, synthesis, and report output
- Research history per session with rerun-in-place, rerun-as-new, rename, share-to-chat, and report export
- Session title search for quickly filtering conversations
- Session export to Markdown for note taking and sharing
- Assistant answer retry for regenerating the latest response in place
- Real-time streaming responses via WebSocket
- arXiv paper search integration
- Modern Vue3 + ElementPlus frontend
- FastAPI backend with SQLAlchemy ORM
- Docker deployment support

## Current Status

- Core chat flow is complete across frontend and backend
- Research task flow is implemented across backend persistence and frontend panels
- Search, export, and retry enhancements are implemented
- Frontend component tests: `24` passing
- Backend API tests: `25` passing
- Retry semantics are intentionally limited to the latest assistant message
- Research answers now enforce stable inline source markers such as `[S1]`

See also:
- [API reference](docs/api.md)
- [Retry decision note](docs/retry-decision.md)

## Architecture

```
├── app/                    # Backend (FastAPI)
│   ├── database.py        # SQLite connection
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic validation
│   ├── crud.py            # Database operations
│   ├── api.py             # REST + WebSocket endpoints
│   ├── main.py            # FastAPI application
│   └── services/          # LangChain agent
│       ├── agent.py       # Academic agent with DeepSeek
│       └── tools.py       # arXiv search tool
├── frontend/              # Frontend (Vue3)
│   └── src/
│       ├── api/           # REST/WebSocket clients
│       ├── stores/        # Pinia state management
│       ├── components/    # Vue components
│       └── views/         # Page views
└── docker-compose.yml     # Docker orchestration
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- DeepSeek API key

### Local Development

1. Clone the repository

```bash
git clone <repo-url>
cd research_agent_learn
```

2. Set up environment

```bash
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY
```

3. Install backend dependencies

```bash
pip install -r requirements.txt
```

4. Install frontend dependencies

```bash
cd frontend
npm install
```

5. One-command startup

```bash
bash scripts/dev-up.sh
```

This command starts:
- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:4173`

6. Manual startup, if needed

```bash
conda run -n agent-dev uvicorn app.main:app --host 127.0.0.1 --port 8000

cd frontend
npm run dev -- --host 127.0.0.1 --port 4173
```

The frontend development server default is also configured to use port `4173`, so `npm run dev` and `bash scripts/dev-up.sh` stay aligned.

7. Open http://127.0.0.1:4173 in browser

### Docker Deployment

1. Set up environment

```bash
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY
```

2. Build and start containers

```bash
docker-compose up -d
```

3. Open http://localhost in browser

4. Stop containers

```bash
docker-compose down
```

## API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/sessions | List all sessions, optional `query` filters by title |
| POST | /api/sessions | Create new session |
| GET | /api/sessions/{id} | Get session with messages |
| PUT | /api/sessions/{id} | Update session title |
| DELETE | /api/sessions/{id} | Delete session |
| GET | /api/sessions/{id}/messages | Get session messages |
| GET | /api/sessions/{id}/export | Export session as Markdown payload |
| GET | /api/sessions/{id}/export/raw | Download raw Markdown content |
| POST | /api/sessions/{id}/messages/{message_id}/retry | Regenerate the latest assistant message |
| POST | /api/messages | Create message |
| POST | /api/research/tasks | Run a persisted research workflow |
| GET | /api/sessions/{id}/research-tasks | List research task history for a session |
| GET | /api/research/tasks/{id} | Get one research task |
| GET | /api/research/tasks/{id}/report | Export research report as JSON payload |
| GET | /api/research/tasks/{id}/report/raw | Download raw Markdown report |
| POST | /api/research/tasks/{id}/share-to-session | Inject research summary or full report into chat |
| DELETE | /api/research/tasks/{id} | Delete one persisted research task |

### Key Product Rules

- Session search only matches session titles
- Export keeps message order and role sections in Markdown
- Retry only applies to the latest assistant message in a session
- Retry updates the existing assistant message instead of creating a new record
- Research tasks persist `plan`, `sources`, `answer`, and `report_markdown`
- Research answers should reference evidence with inline markers like `[S1]`
- Research reports can be exported as JSON payloads or raw Markdown downloads

### WebSocket

- Endpoint: `/api/ws/chat/{session_id}`
- Protocol:
  - Client sends: `{"content": "user message"}`
  - Server sends: `{"type": "chunk", "content": "response chunk"}`
  - Server sends: `{"type": "done", "content": "full response"}`

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| DEEPSEEK_API_KEY | DeepSeek API key | Yes |
| DATABASE_URL | SQLite database URL | No |

### DeepSeek API

Get your API key from [DeepSeek Platform](https://platform.deepseek.com/).

## Development

### Backend

```bash
# Run with auto-reload
uvicorn app.main:app --reload

# Run tests
pytest

# Or use the local Conda environment
/Users/syj/miniconda3/bin/conda run -n agent-dev python -m pytest -q
```

### Frontend

```bash
cd frontend

# Development
npm run dev

# Build
npm run build

# Preview build
npm run preview

# Run tests
npm test
```

## License

MIT License
