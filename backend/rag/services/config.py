"""Configuration and environment settings for RAG services."""

from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# Chunking settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Upload settings
MAX_UPLOAD_SIZE_MB = 10


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


class _LazyModel(str):
    """Lazy string proxy that validates model configuration at first use."""

    def __new__(cls, env_var: str):
        instance = super().__new__(cls, "")
        instance._env_var = env_var
        return instance

    def _resolve(self) -> str:
        val = os.getenv(self._env_var)
        if not val:
            raise RuntimeError(f"{self._env_var} is not set in backend/.env")
        return val

    def __str__(self) -> str:
        return self._resolve()

    def __repr__(self) -> str:
        return repr(self._resolve())

    def __contains__(self, item: object) -> bool:
        return item in self._resolve()

    def __eq__(self, other: object) -> bool:
        return self._resolve() == other

    def __hash__(self) -> int:
        return hash(self._resolve())

    def __len__(self) -> int:
        return len(self._resolve())

    def __bool__(self) -> bool:
        return bool(self._resolve())


def get_embedding_model() -> str:
    """Return GEMINI_EMBEDDING_MODEL or raise RuntimeError if missing."""
    model = os.getenv("GEMINI_EMBEDDING_MODEL")
    if not model:
        raise RuntimeError("GEMINI_EMBEDDING_MODEL is not set in backend/.env")
    return model


def get_generation_model() -> str:
    """Return GEMINI_GENERATION_MODEL or raise RuntimeError if missing."""
    model = os.getenv("GEMINI_GENERATION_MODEL")
    if not model:
        raise RuntimeError("GEMINI_GENERATION_MODEL is not set in backend/.env")
    return model


GEMINI_EMBEDDING_MODEL = _LazyModel("GEMINI_EMBEDDING_MODEL")
GEMINI_GENERATION_MODEL = _LazyModel("GEMINI_GENERATION_MODEL")

# Embedding settings
EMBEDDING_BATCH_SIZE = 100

# Vector store settings
CHROMA_PATH = Path(__file__).resolve().parent.parent.parent / "chroma_db"
COLLECTION_NAME = "pdf_chunks"
DEFAULT_TOP_K = 4

# Generation settings
NOT_FOUND_MESSAGE = "I could not find this in the PDF."

# API retry settings
RETRY_DELAYS = (1.0, 2.0, 4.0)

# Quiz settings
QUIZ_DEFAULT_QUESTIONS = 5
QUIZ_MAX_QUESTIONS = 10
QUIZ_MAX_CHUNKS = 12


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    """Return a cached google-genai Client instance created with GEMINI_API_KEY."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in backend/.env")
    return genai.Client(api_key=GEMINI_API_KEY)
