"""Answer generation: build a grounded prompt and ask Gemini Flash."""

# TODO: use llm.generate_text and llm.format_context for generation

PROMPT_TEMPLATE = """Answer the question using ONLY the context below.
If the answer is not in the context, say: "I could not find this in the PDF."

Context:
{context}

Question: {question}
"""


def build_prompt(question: str, context_chunks: list[dict]) -> str:
    """Combine the question and retrieved chunks into one prompt."""
    # TODO: join chunk texts and fill PROMPT_TEMPLATE
    raise NotImplementedError


def generate_answer(question: str, context_chunks: list[dict]) -> str:
    """
    Generate the final answer from the retrieved chunks.

    Args:
        question: the user's question.
        context_chunks: output of vector_store.search().
    """
    # TODO: build_prompt(...) -> send to Gemini Flash -> return response text
    raise NotImplementedError