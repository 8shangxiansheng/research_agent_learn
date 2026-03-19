"""
FastAPI main application for Academic Q&A Agent.
Configures middleware, routes, and startup events.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_tables
from app.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup: Create database tables
    create_tables()
    yield
    # Shutdown: Clean up resources (if needed)
    pass


# Create FastAPI application
app = FastAPI(
    title="Academic Q&A Agent",
    description="Multi-session academic Q&A system with LangChain and DeepSeek",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "academic-qa-agent"}


# Root endpoint
@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Academic Q&A Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
