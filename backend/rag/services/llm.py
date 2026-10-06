"""Shared Gemini LLM helpers, retry logic, and prompt formatting."""

import time
from typing import Any, Callable

from google.genai import types

from .config import (
    RETRY_DELAYS,
    get_gemini_client,
    get_generation_model,
)


class GeminiBusyError(RuntimeError):
    """Raised when Gemini API retries are exhausted due to transient errors."""


class GeminiQuotaError(GeminiBusyError):
    """Raised when Gemini API daily quota limit is reached."""


def _is_per_day_quota_error(err: Exception) -> bool:
    """Check if error is a 429 daily quota error."""
    code = getattr(err, "code", None) or getattr(
        getattr(err, "response", None), "status_code", None
    )
    status = getattr(err, "status", None)
    is_429 = code == 429 or status == "RESOURCE_EXHAUSTED"
    err_str = f"{err} {getattr(err, 'message', '')}"
    return is_429 and "PerDay" in err_str


def is_transient_error(err: Exception) -> bool:
    """Check if error is transient based strictly on structured fields."""
    return (
        getattr(err, "code", None) in (429, 503)
        or getattr(getattr(err, "response", None), "status_code", None) in (429, 503)
        or getattr(err, "status", None) in ("RESOURCE_EXHAUSTED", "UNAVAILABLE")
    )


def call_with_retry(fn: Callable[[], Any]) -> Any:
    """
    Call a zero-argument callable with exponential backoff on transient errors.

    Args:
        fn: Zero-argument callable to execute.

    Returns:
        The result of fn().

    Raises:
        GeminiQuotaError: Immediately on daily quota 429 error without retry.
        GeminiBusyError: If all retries are exhausted on transient errors.
        Exception: Re-raises any non-transient error immediately.
    """
    max_retries = len(RETRY_DELAYS)
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as err:
            if _is_per_day_quota_error(err):
                raise GeminiQuotaError(
                    "Gemini API daily quota limit reached."
                ) from err
            if not is_transient_error(err):
                raise
            if attempt == max_retries:
                raise GeminiBusyError(
                    f"Gemini API failed after {max_retries} retries: {err}"
                ) from err
            time.sleep(RETRY_DELAYS[attempt])


def generate_text(prompt: str, json_mode: bool = False) -> str:
    """
    Generate text using Gemini model with optional JSON mode.

    Args:
        prompt: Input text prompt.
        json_mode: Whether to enforce application/json response MIME type.

    Returns:
        Generated text string.

    Raises:
        RuntimeError: If the model returns an empty or None response.
    """
    client = get_gemini_client()
    model = get_generation_model()
    config = (
        types.GenerateContentConfig(response_mime_type="application/json")
        if json_mode
        else None
    )

    def _call():
        if config is not None:
            return client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
        return client.models.generate_content(
            model=model,
            contents=prompt,
        )

    response = call_with_retry(_call)
    text = response.text if response else None
    if not text:
        raise RuntimeError("Empty response from Gemini")
    return text


def format_context(chunks: list[dict]) -> str:
    """
    Format a list of chunk dicts into a single context string separated by blank lines.

    Args:
        chunks: List of chunk dicts with 'page' and 'text'.

    Returns:
        Formatted context string.
    """
    formatted = [f"[Page {chunk['page']}] {chunk['text']}" for chunk in chunks if chunk.get("text")]
    return "\n\n".join(formatted)
