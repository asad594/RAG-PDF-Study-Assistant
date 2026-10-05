"""Answer generation: build a grounded prompt and ask Gemini Flash."""

from .config import NOT_FOUND_MESSAGE
from .llm import format_context, generate_text


def build_prompt(question: str, chunks: list[dict]) -> str:
    """
    Build the prompt combining instructions, formatted context, and the question.

    Args:
        question: User's question.
        chunks: List of chunk dicts containing 'page' and 'text'.

    Returns:
        Formatted prompt string.
    """
    context = format_context(chunks)
    return (
        "Answer only from the context below. Do not use outside knowledge.\n"
        f'If the context does not contain the answer, reply with exactly: "{NOT_FOUND_MESSAGE}"\n'
        "Mention the page number(s) in the answer like (Page 2).\n"
        "Answer in the same language as the question.\n"
        "Keep the answer short and clear.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question.strip()}\n"
    )


def generate_answer(
    question: str,
    chunks: list[dict] | None = None,
    context_chunks: list[dict] | None = None,
) -> dict:
    """
    Answer the question using ONLY the retrieved chunks.

    Args:
        question: The user's question.
        chunks: List of chunk dicts ({"text": str, "page": int}).
        context_chunks: Optional alias for chunks.

    Returns:
        Dict with "answer" (str) and "sources" (list of chunk dicts).
    """
    input_chunks = chunks if chunks is not None else context_chunks
    if not input_chunks or not question or not question.strip():
        return {
            "answer": NOT_FOUND_MESSAGE,
            "sources": [],
        }

    prompt = build_prompt(question, input_chunks)
    response_text = generate_text(prompt)
    answer = response_text.strip()

    if answer == NOT_FOUND_MESSAGE or answer.strip('"\'') == NOT_FOUND_MESSAGE:
        return {
            "answer": NOT_FOUND_MESSAGE,
            "sources": [],
        }

    seen = set()
    unique_sources = []
    for chunk in input_chunks:
        page = int(chunk.get("page", 0))
        text = chunk.get("text", "")
        key = (page, text)
        if key not in seen:
            seen.add(key)
            unique_sources.append({"page": page, "text": text})

    return {
        "answer": answer,
        "sources": unique_sources,
    }