"""Embeddings: convert text into vectors using the Gemini embedding model."""

EMBEDDING_MODEL = "..."  # TODO: set from Google AI Studio docs
BATCH_SIZE = 20          # send chunks in small batches (free API rate limits)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Create one embedding vector per chunk text.

    Args:
        texts: list of chunk texts.

    Returns:
        A list of vectors, in the same order as `texts`.
    """
    # TODO: call Gemini embeddings API in batches of BATCH_SIZE
    raise NotImplementedError


def embed_query(question: str) -> list[float]:
    """
    Create an embedding vector for the user's question.
    Must use the SAME model as embed_texts().
    """
    # TODO: call Gemini embeddings API for a single question
    raise NotImplementedError