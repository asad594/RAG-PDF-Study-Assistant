"""Configuration and environment settings for RAG services."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Chunking settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def _load_env() -> None:
    """Load backend/.env once without side effects."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()


# Load environment variables on module import
_load_env()

# Gemini API settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL")
GEMINI_GENERATION_MODEL = os.getenv("GEMINI_GENERATION_MODEL")
