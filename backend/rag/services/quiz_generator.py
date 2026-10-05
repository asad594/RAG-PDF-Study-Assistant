"""Quiz generation: create multiple-choice questions from retrieved chunks."""

# TODO: use llm.generate_text and llm.format_context for generation

QUIZ_PROMPT_TEMPLATE = """Using ONLY the context below, create {num_questions}
multiple-choice questions. Return ONLY valid JSON in this format:
[{"question": "...", "options": ["A", "B", "C", "D"],
   "correct_index": 0, "explanation": "..."}]

Context:
{context}
"""


def generate_quiz(context_chunks: list[dict], num_questions: int = 5) -> list[dict]:
    """
    Generate MCQs from the retrieved chunks.

    Returns:
        [{"question": str, "options": list[str],
          "correct_index": int, "explanation": str}, ...]
    """
    # TODO: fill QUIZ_PROMPT_TEMPLATE -> Gemini Flash (JSON output) -> parse JSON
    raise NotImplementedError