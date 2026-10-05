"""Vector store: save and search chunk embeddings in ChromaDB."""

import chromadb

from .config import CHROMA_PATH, COLLECTION_NAME, DEFAULT_TOP_K

_client = None


def _get_collection():
    """Get or create the ChromaDB collection using a persistent client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def reset_collection() -> None:
    """Delete old data so a newly uploaded PDF starts fresh."""
    _get_collection()
    try:
        _client.delete_collection(name=COLLECTION_NAME)
    except (ValueError, Exception):
        pass
    _get_collection()


def store_chunks(chunks: list[dict], vectors: list[list[float]]) -> None:
    """
    Save chunk text, vector and metadata (page number) in ChromaDB.

    Args:
        chunks: [{"text": "...", "page": 1}, ...]
        vectors: embeddings, same order as `chunks`.
    """
    if len(chunks) != len(vectors):
        raise ValueError(
            f"Mismatch between number of chunks ({len(chunks)}) and vectors ({len(vectors)})."
        )
    if not chunks:
        return

    collection = _get_collection()
    ids = [f"chunk-{i}" for i in range(len(chunks))]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [{"page": int(chunk["page"])} for chunk in chunks]

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=vectors,
        metadatas=metadatas,
    )


def search(query_vector: list[float], top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    Find the chunks most similar to the query vector.

    Returns:
        [{"text": "...", "page": 3}, ...] ordered from most to least similar.
    """
    collection = _get_collection()
    count = collection.count()
    if count == 0 or top_k <= 0:
        return []

    actual_k = min(top_k, count)
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=actual_k,
        include=["documents", "metadatas"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    output: list[dict] = []
    for doc, meta in zip(documents, metadatas):
        output.append({
            "text": doc,
            "page": int(meta["page"]) if (meta and "page" in meta) else 0,
        })

    return output


def get_chunk_count() -> int:
    """
    Return the number of stored chunks in the collection, or 0 if empty.
    """
    try:
        collection = _get_collection()
        return collection.count()
    except Exception:
        return 0