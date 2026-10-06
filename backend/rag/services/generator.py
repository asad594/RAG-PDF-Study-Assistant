"""Answer generation: build a grounded prompt and ask Gemini Flash."""

import re

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


def _extract_cited_pages(text: str) -> set[int]:
    """Parse page numbers cited like '(Page 6)', '(Pages 2, 3)', '(Pages 2-3)', or '(Pages 2 to 4)'."""
    cited: set[int] = set()
    matches = re.findall(r"\(pages?\s+([^)]+)\)", text, flags=re.IGNORECASE)
    for match in matches:
        for m in re.finditer(r"(\d+)\s*(?:[-–—]|\bto\b)\s*(\d+)|(\d+)", match, flags=re.IGNORECASE):
            if m.group(1) is not None and m.group(2) is not None:
                start = int(m.group(1))
                end = int(m.group(2))
                if start <= end:
                    count = min(end - start + 1, 50)
                    for p in range(start, start + count):
                        cited.add(p)
                else:
                    cited.add(start)
                    cited.add(end)
            elif m.group(3) is not None:
                cited.add(int(m.group(3)))
    return cited


def generate_answer(
    question: str,
    chunks: list[dict] | None = None,
) -> dict:
    """
    Answer the question using ONLY the retrieved chunks.

    Args:
        question: The user's question.
        chunks: List of chunk dicts ({"text": str, "page": int}).

    Returns:
        Dict with "answer" (str) and "sources" (list of chunk dicts).
    """
    if not chunks or not question or not question.strip():
        return {
            "answer": NOT_FOUND_MESSAGE,
            "sources": [],
        }

    prompt = build_prompt(question, chunks)
    response_text = generate_text(prompt)
    answer = response_text.strip()

    if answer.strip('"\'') == NOT_FOUND_MESSAGE:
        return {
            "answer": NOT_FOUND_MESSAGE,
            "sources": [],
        }

    seen = set()
    all_sources = []
    for chunk in chunks:
        page = int(chunk.get("page", 0))
        text = chunk.get("text", "")
        key = (page, text)
        if key not in seen:
            seen.add(key)
            all_sources.append({"page": page, "text": text})

    cited_pages = _extract_cited_pages(answer)
    filtered_sources = [s for s in all_sources if s["page"] in cited_pages]
    sources = filtered_sources if filtered_sources else all_sources

    return {
        "answer": answer,
        "sources": sources,
    }