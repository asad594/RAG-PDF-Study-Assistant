"""PDF loading: extract raw text from an uploaded PDF or file path (pypdf)."""

import logging
from pathlib import Path
import re
from typing import Any, BinaryIO, Union

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class NoTextError(ValueError):
    """Raised when a PDF contains no extractable text."""


def _clean_text(text: str) -> str:
    """
    Normalize whitespace, strip, and fix simple hyphenated line breaks.

    Args:
        text: Raw extracted text string.

    Returns:
        Cleaned text string.
    """
    if not text:
        return ""
    # Standardize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Fix hyphenated line breaks (e.g. "exam-\nple" -> "example")
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    # Normalize horizontal whitespace within lines
    text = re.sub(r"[ \t]+", " ", text)
    # Strip whitespace around newlines
    text = re.sub(r" ?\n ?", "\n", text)
    # Normalize excessive blank lines (keep paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pages(source: Union[str, Path, BinaryIO, Any]) -> list[dict]:
    """
    Extract text page by page from an uploaded PDF or file path.

    Args:
        source: File path (str or Path) or binary file-like object (Django UploadedFile).

    Returns:
        A list of dicts: [{"page": int (1-based), "text": str}, ...].

    Raises:
        NoTextError: If no page has extractable text.
        ValueError: If the file is encrypted, invalid, or corrupted.
    """
    # Reset stream position if source is a file-like object
    if hasattr(source, "seek"):
        source.seek(0)

    try:
        try:
            reader = PdfReader(source)
            if reader.is_encrypted:
                raise ValueError("PDF is encrypted and password protected.")
            pages = reader.pages
            total_pages = len(pages)
        except ValueError:
            raise
        except Exception as err:
            logger.exception("Failed to open PDF file: %s", err)
            raise ValueError(f"Could not read PDF: {err}") from err

        if total_pages == 0:
            raise ValueError("The PDF contains no pages.")

        extracted_pages: list[dict] = []
        for page_num, page in enumerate(pages, start=1):
            try:
                raw_text = page.extract_text() or ""
            except Exception as err:
                logger.exception("Failed to read page %d of PDF: %s", page_num, err)
                raise ValueError(f"Failed to read page {page_num} of PDF: {err}") from err

            cleaned = _clean_text(raw_text)
            if cleaned:
                extracted_pages.append({"page": page_num, "text": cleaned})

        if not extracted_pages:
            raise NoTextError("No extractable text found in the PDF (pages may be scanned or empty).")

        return extracted_pages
    except (NoTextError, ValueError):
        raise
    except Exception as err:
        logger.exception("Unexpected error while processing PDF: %s", err)
        raise ValueError(f"Could not read PDF: {err}") from err