"""Configuration and environment settings for RAG services."""

from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

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

# Embedding settings
EMBEDDING_BATCH_SIZE = 100


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    """Return a cached google-genai Client instance created with GEMINI_API_KEY."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in backend/.env")
    return genai.Client(api_key=GEMINI_API_KEY)
