"""
Application package initialization.
Loads environment variables from the project .env file on import.
"""
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")
