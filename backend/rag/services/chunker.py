"""Chunking: split page text into small overlapping chunks (LangChain splitter)."""

from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from .config import CHUNK_SIZE, CHUNK_OVERLAP
except ImportError:
    from config import CHUNK_SIZE, CHUNK_OVERLAP

# Create splitter once at module level using configuration from config.py
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)


def split_into_chunks(pages: list[dict]) -> list[dict]:
    """
    Split page texts into chunks, keeping the page number for each chunk.

    Args:
        pages: output of pdf_loader.extract_pages().

    Returns:
        A list like [{"text": "...", "page": 1}, ...].
    """
    chunks: list[dict] = []
    for page in pages:
        page_num = page.get("page")
        text = page.get("text", "")
        if not text:
            continue

        for chunk_text in _splitter.split_text(text):
            cleaned_chunk = chunk_text.strip()
            if cleaned_chunk:
                chunks.append({"text": cleaned_chunk, "page": page_num})

    return chunks