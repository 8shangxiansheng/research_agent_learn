# Academic Q&A Agent

A full-stack application for academic paper research and Q&A, powered by LangChain and DeepSeek LLM.

## Features

- Multi-session chat interface for organizing research conversations
- Real-time streaming responses via WebSocket
- arXiv paper search integration
- Modern Vue3 + ElementPlus frontend
- FastAPI backend with SQLAlchemy ORM
- Docker deployment support

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
| GET | /api/sessions | List all sessions |
| POST | /api/sessions | Create new session |
| GET | /api/sessions/{id} | Get session with messages |
| PUT | /api/sessions/{id} | Update session title |
| DELETE | /api/sessions/{id} | Delete session |
| GET | /api/sessions/{id}/messages | Get session messages |
| POST | /api/messages | Create message |

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
```

## License

MIT License
