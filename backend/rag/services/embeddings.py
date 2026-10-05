"""Embeddings: convert text into vectors using the Gemini embedding model."""

from google.genai import types

from .config import (
    EMBEDDING_BATCH_SIZE,
    GEMINI_EMBEDDING_MODEL,
    get_gemini_client,
)
from .llm import call_with_retry


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    """
    Private helper to embed texts in batches using call_with_retry.

    Args:
        texts: List of strings to embed.
        task_type: Embedding task type ("RETRIEVAL_DOCUMENT" or "RETRIEVAL_QUERY").

    Returns:
        List of embedding vectors (list of float), matching the order of input texts.
    """
    if not texts:
        return []

    client = get_gemini_client()
    all_vectors: list[list[float]] = []

    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]

        response = call_with_retry(
            lambda: client.models.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(task_type=task_type),
            )
        )

        if response is None or not response.embeddings or len(response.embeddings) != len(batch):
            received = len(response.embeddings) if (response and response.embeddings) else 0
            raise RuntimeError(
                f"Embedding count mismatch: expected {len(batch)} vectors, got {received}."
            )

        for emb in response.embeddings:
            all_vectors.append(emb.values)

    if len(all_vectors) != len(texts):
        raise RuntimeError(
            f"Total embedding count mismatch: expected {len(texts)} vectors, got {len(all_vectors)}."
        )

    return all_vectors


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed document chunks using Gemini embedding model with task_type='RETRIEVAL_DOCUMENT'.

    Args:
        texts: List of chunk texts.

    Returns:
        A list of vectors, in the same order as `texts`.
    """
    return _embed(texts, task_type="RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    """
    Create an embedding vector for a single query with task_type='RETRIEVAL_QUERY'.

    Args:
        text: Query or question string.

    Returns:
        A list of floats representing the embedding vector.
    """
    vectors = _embed([text], task_type="RETRIEVAL_QUERY")
    if not vectors:
        raise RuntimeError("No embedding returned for query.")
    return vectors[0]