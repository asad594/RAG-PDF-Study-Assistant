"""Quiz generation: create multiple-choice questions from retrieved chunks."""

import json
import logging

from .config import QUIZ_DEFAULT_QUESTIONS
from .llm import format_context, generate_text

logger = logging.getLogger(__name__)


class QuizGenerationError(ValueError):
    """Raised when quiz questions cannot be generated or parsed."""


QUIZ_PROMPT_TEMPLATE = """Using ONLY the context below, create {num_questions} multiple-choice questions.

Requirements:
- Use ONLY facts directly mentioned in the context. Do not invent or assume any facts.
- Each question must have exactly 4 options.
- Exactly one option must be correct.
- correct_index must be an integer (0, 1, 2, or 3) indicating the position of the correct option in options.
- Options must NOT start with labels like "A)", "B)", "1.", "2.", or similar prefixes.
- Provide a short explanation citing the page number where the information is found, e.g. (Page 2).
- Write in the same language as the context.
- Return ONLY valid JSON matching this schema:
[
  {
    "question": "Question text here?",
    "options": ["First option", "Second option", "Third option", "Fourth option"],
    "correct_index": 0,
    "explanation": "Short explanation (Page X)."
  }
]

Context:
{context}
"""


def _clean_json_text(text: str) -> str:
    """Strip markdown code fences and whitespace from raw text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def generate_quiz(
    context_chunks: list[dict],
    num_questions: int = QUIZ_DEFAULT_QUESTIONS,
) -> list[dict]:
    """
    Generate MCQs from the retrieved chunks.

    Args:
        context_chunks: List of chunk dicts [{"text": str, "page": int}, ...].
        num_questions: Number of questions to generate.

    Returns:
        List of dicts [{"question": str, "options": [4 strings],
                        "correct_index": int, "explanation": str}, ...]

    Raises:
        QuizGenerationError: If the output cannot be parsed or yields no valid items.
    """
    context = format_context(context_chunks)
    prompt = (
        QUIZ_PROMPT_TEMPLATE
        .replace("{num_questions}", str(num_questions))
        .replace("{context}", context)
    )

    raw_text = generate_text(prompt, json_mode=True)
    cleaned = _clean_json_text(raw_text)

    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse quiz response as JSON: %s", exc)
        raise QuizGenerationError(f"Model response is not valid JSON: {exc}") from exc

    if isinstance(parsed, list):
        raw_items = parsed
    elif isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
        raw_items = parsed["questions"]
    else:
        logger.warning("Quiz JSON is neither a list nor a dict with 'questions' list.")
        raise QuizGenerationError("Invalid quiz JSON structure: expected list or object with 'questions'.")

    valid_questions: list[dict] = []
    for idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            logger.warning("Quiz item %d dropped: item is not a dict.", idx)
            continue

        question = item.get("question")
        if not isinstance(question, str) or not question.strip():
            logger.warning("Quiz item %d dropped: question is not a non-blank string.", idx)
            continue

        options = item.get("options")
        if not isinstance(options, list) or len(options) != 4:
            logger.warning("Quiz item %d dropped: options list does not have exactly 4 elements.", idx)
            continue
        if not all(isinstance(opt, str) and opt.strip() for opt in options):
            logger.warning("Quiz item %d dropped: one or more options are not non-blank strings.", idx)
            continue

        correct_index = item.get("correct_index")
        if type(correct_index) is not int or correct_index not in (0, 1, 2, 3):
            logger.warning("Quiz item %d dropped: correct_index must be int in 0..3 (got %r).", idx, correct_index)
            continue

        explanation = item.get("explanation")
        if not isinstance(explanation, str):
            logger.warning("Quiz item %d dropped: explanation is not a string.", idx)
            continue

        valid_questions.append({
            "question": question.strip(),
            "options": [opt.strip() for opt in options],
            "correct_index": correct_index,
            "explanation": explanation.strip(),
        })

    if not valid_questions:
        logger.warning("No valid quiz items remained after validation.")
        raise QuizGenerationError("No valid quiz questions could be extracted from response.")

    return valid_questions[:num_questions]