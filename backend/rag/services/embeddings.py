"""Embeddings: convert text into vectors using the Gemini embedding model."""

import time
from google.genai import types

from .config import (
    EMBEDDING_BATCH_SIZE,
    GEMINI_EMBEDDING_MODEL,
    get_gemini_client,
)


def _is_transient_error(err: Exception) -> bool:
    """Check if error is transient based strictly on structured fields."""
    return (
        getattr(err, "code", None) in (429, 503)
        or getattr(getattr(err, "response", None), "status_code", None) in (429, 503)
        or getattr(err, "status", None) in ("RESOURCE_EXHAUSTED", "UNAVAILABLE")
    )



def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    """
    Private helper to embed texts in batches with retries and exponential backoff.

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
    delays = [1.0, 2.0, 4.0]
    max_retries = 3

    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        response = None

        for attempt in range(max_retries + 1):
            try:
                response = client.models.embed_content(
                    model=GEMINI_EMBEDDING_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(task_type=task_type),
                )
                break
            except Exception as err:
                if not _is_transient_error(err):
                    raise
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Gemini embedding API failed after {max_retries} retries: {err}"
                    ) from err
                time.sleep(delays[attempt])

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