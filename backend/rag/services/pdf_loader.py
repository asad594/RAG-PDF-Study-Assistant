"""PDF loading: extract raw text from an uploaded PDF (pypdf)."""


def extract_pages(pdf_file) -> list[dict]:
    """
    Extract text page by page from an uploaded PDF.

    Args:
        pdf_file: uploaded file object (request.FILES["file"]).

    Returns:
        A list like [{"page": 1, "text": "..."}, {"page": 2, "text": "..."}].
    """
    # TODO: use pypdf.PdfReader, loop over pages, skip empty pages
    raise NotImplementedError