"""Chunking: split page text into small overlapping chunks (LangChain splitter)."""

CHUNK_SIZE = 500      # characters per chunk
CHUNK_OVERLAP = 50    # characters shared between neighbouring chunks


def split_into_chunks(pages: list[dict]) -> list[dict]:
    """
    Split page texts into chunks, keeping the page number for each chunk.

    Args:
        pages: output of pdf_loader.extract_pages().

    Returns:
        A list like [{"text": "...", "page": 1}, ...].
    """
    # TODO: use RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE,
    #       chunk_overlap=CHUNK_OVERLAP) on each page's text
    raise NotImplementedError