"""
Database connection module for Academic Q&A Agent application.
Provides SQLAlchemy engine, session factory, and declarative base.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./academic_qa.db")

# Create SQLAlchemy engine
# check_same_thread=False is needed for SQLite in multi-threaded FastAPI
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency injection generator for database sessions.
    
    Yields a database session and ensures it is closed after use.
    
    Usage in FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables defined in models.
    Call this at application startup.
    """
    # Import models to register them with Base
    from app import models  # noqa: F401
    
    Base.metadata.create_all(bind=engine)
