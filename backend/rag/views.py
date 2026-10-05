"""API views for the RAG PDF Study Assistant."""

import logging

from google.genai import errors
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services.chunker import split_into_chunks
from .services.embeddings import embed_query, embed_texts
from .services.generator import generate_answer
from .services.pdf_loader import extract_pages
from .services.vector_store import reset_collection, search, store_chunks

logger = logging.getLogger(__name__)


def handle_service_error(exc: Exception) -> Response:
    """Log the exception and return a clean error Response without sensitive details."""
    logger.exception("Service error occurred: %s", exc)
    if isinstance(exc, (RuntimeError, errors.APIError)):
        return Response(
            {"error": "The AI service is busy. Please try again in a few minutes."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(
        {"error": "Something went wrong on the server."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@api_view(["POST"])
def upload_pdf(request):
    """
    Upload and process a PDF file into chunks and vector store.

    Expects:
        Multipart form data with 'file' field containing a .pdf file.
    """
    if "file" not in request.FILES:
        return Response(
            {"error": "No file uploaded."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    uploaded_file = request.FILES["file"]
    if not (uploaded_file.name and uploaded_file.name.lower().endswith(".pdf")):
        return Response(
            {"error": "Only PDF files are allowed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        pages = extract_pages(uploaded_file)
        chunks = split_into_chunks(pages)
    except ValueError as exc:
        logger.warning("No readable text in PDF: %s", exc)
        return Response(
            {"error": "No readable text found in this PDF."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not chunks:
        return Response(
            {"error": "No readable text found in this PDF."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        texts = [chunk["text"] for chunk in chunks]
        vectors = embed_texts(texts)
        reset_collection()
        store_chunks(chunks, vectors)
    except Exception as exc:
        return handle_service_error(exc)

    return Response(
        {
            "message": "PDF processed successfully.",
            "pages": len(pages),
            "chunks": len(chunks),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def ask_question(request):
    """
    Answer a question using the stored PDF context.

    Expects:
        JSON body: {"question": "..."}
    """
    question = request.data.get("question") if request.data else None
    if not question or not str(question).strip():
        return Response(
            {"error": "Question is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cleaned_question = str(question).strip()
    try:
        query_vector = embed_query(cleaned_question)
        chunks = search(query_vector)
        if not chunks:
            return Response(
                {"error": "Please upload a PDF first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer_data = generate_answer(cleaned_question, chunks)
        return Response(answer_data, status=status.HTTP_200_OK)
    except Exception as exc:
        return handle_service_error(exc)


@api_view(["POST"])
def generate_quiz_view(request):
    # TODO: retrieve chunks -> generate MCQs
    return Response({"message": "quiz endpoint - not implemented yet"}, status=501)