"""Vector store: save and search chunk embeddings in ChromaDB."""

from .config import CHROMA_PATH, COLLECTION_NAME, DEFAULT_TOP_K


def reset_collection() -> None:
    """Delete old data so a newly uploaded PDF starts fresh."""
    # TODO: delete and recreate the Chroma collection
    raise NotImplementedError


def store_chunks(chunks: list[dict], vectors: list[list[float]]) -> None:
    """
    Save chunk text, vector and metadata (page number) in ChromaDB.

    Args:
        chunks: [{"text": "...", "page": 1}, ...]
        vectors: embeddings, same order as `chunks`.
    """
    # TODO: collection.add(ids=..., documents=..., embeddings=..., metadatas=...)
    raise NotImplementedError


def search(query_vector: list[float], top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    Find the chunks most similar to the query vector.

    Returns:
        [{"text": "...", "page": 3}, ...] ordered from most to least similar.
    """
    # TODO: collection.query(query_embeddings=[query_vector], n_results=top_k)
    raise NotImplementedError