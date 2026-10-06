"""Vector store: save and search chunk embeddings in ChromaDB."""

import logging

import chromadb
from chromadb.errors import NotFoundError

from .config import (
    CHROMA_PATH,
    COLLECTION_NAME,
    DEFAULT_TOP_K,
    QUIZ_MAX_CHUNKS,
)

logger = logging.getLogger(__name__)

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
    except NotFoundError:
        pass
    except Exception as err:
        logger.exception("Failed to delete Chroma collection '%s': %s", COLLECTION_NAME, err)
        raise
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
    Return the number of stored chunks in the collection.
    """
    collection = _get_collection()
    return collection.count()


def _parse_chunk_id(cid: str) -> int | None:
    """Extract numeric suffix from chunk id formatted as 'chunk-<number>'."""
    parts = cid.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return int(parts[1])
    logger.warning("Invalid chunk ID format '%s'; skipping chunk.", cid)
    return None


def get_quiz_chunks(max_chunks: int = QUIZ_MAX_CHUNKS) -> list[dict]:
    """
    Retrieve stored chunks in document order, evenly sampled if count > max_chunks.

    Args:
        max_chunks: Maximum number of chunks to return.

    Returns:
        List of chunk dicts [{"text": str, "page": int}, ...].
    """
    if max_chunks <= 0:
        return []

    collection = _get_collection()

    # Step 1: Read only IDs without loading documents/metadatas into memory
    res = collection.get(include=[])
    ids = res.get("ids") or []
    if not ids:
        return []

    parsed_items = []
    for cid in ids:
        pid = _parse_chunk_id(cid)
        if pid is not None:
            parsed_items.append((pid, cid))

    if not parsed_items:
        return []

    parsed_items.sort(key=lambda item: item[0])
    total = len(parsed_items)

    if total <= max_chunks:
        chosen_items = parsed_items
    elif max_chunks == 1:
        chosen_items = [parsed_items[0]]
    else:
        indices = [round(i * (total - 1) / (max_chunks - 1)) for i in range(max_chunks)]
        chosen_items = [parsed_items[idx] for idx in indices]

    chosen_ids = [item[1] for item in chosen_items]

    # Step 2: Retrieve only the chosen chunks by ID
    res = collection.get(ids=chosen_ids, include=["documents", "metadatas"])
    res_ids = res.get("ids") or []
    documents = res.get("documents") or []
    metadatas = res.get("metadatas") or []

    data_by_id: dict[str, dict] = {}
    for cid, doc, meta in zip(res_ids, documents, metadatas):
        page = int(meta["page"]) if (meta and "page" in meta) else 0
        data_by_id[cid] = {"text": doc, "page": page}

    # Return in document order matching chosen_ids
    return [data_by_id[cid] for cid in chosen_ids if cid in data_by_id]