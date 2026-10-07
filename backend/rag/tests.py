"""Offline unit and integration tests for RAG services and endpoints."""

import io
import logging
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from pypdf import PdfWriter
from rest_framework import status
from rest_framework.test import APIClient

from rag.services import vector_store
from rag.services.config import (
    NOT_FOUND_MESSAGE,
    QUIZ_DEFAULT_QUESTIONS,
    get_embedding_model,
    get_generation_model,
)
from rag.services.embeddings import _embed
from rag.services.generator import _extract_cited_pages, generate_answer
from rag.services.llm import (
    GeminiBusyError,
    GeminiQuotaError,
    call_with_retry,
)
from rag.services.pdf_loader import ExtractedPages, extract_pages
from rag.services.quiz_generator import QuizGenerationError


# Global isolation: ensure ChromaDB never writes to backend/chroma_db during tests
_module_temp_chroma = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
_orig_chroma_path = vector_store.CHROMA_PATH
vector_store.CHROMA_PATH = Path(_module_temp_chroma.name)
vector_store._client = None


def tearDownModule():
    """Restore ChromaDB path and clean up temporary directory after all tests."""
    vector_store._client = None
    vector_store.CHROMA_PATH = _orig_chroma_path
    try:
        _module_temp_chroma.cleanup()
    except Exception:
        pass


class SilentTestCase(TestCase):
    """Base test case that silences logging to keep test output clean."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)
        super().tearDownClass()


def _create_dummy_pdf(num_pages: int = 1) -> io.BytesIO:
    """Create an unencrypted PDF with blank pages in memory."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf


def _create_encrypted_pdf(password: str = "secret") -> io.BytesIO:
    """Create a password-encrypted PDF in memory using pypdf."""
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf


class MethodNotAllowedTests(SilentTestCase):
    """Verify that GET requests to POST-only API endpoints return HTTP 405."""

    def setUp(self):
        self.client = APIClient()

    def test_get_upload_returns_405(self):
        response = self.client.get("/api/upload/")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_ask_returns_405(self):
        response = self.client.get("/api/ask/")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_quiz_returns_405(self):
        response = self.client.get("/api/quiz/")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class UploadEndpointTests(SilentTestCase):
    """Test POST /api/upload/ endpoint."""

    def setUp(self):
        self.client = APIClient()

    def test_upload_no_file(self):
        response = self.client.post("/api/upload/", {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": "No file uploaded."})

    def test_upload_non_pdf_file(self):
        file = SimpleUploadedFile("notes.txt", b"plain text", content_type="text/plain")
        response = self.client.post("/api/upload/", {"file": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": "Only PDF files are allowed."})

    def test_upload_file_too_large(self):
        big_content = b"x" * (11 * 1024 * 1024)
        file = SimpleUploadedFile("big.pdf", big_content, content_type="application/pdf")
        response = self.client.post("/api/upload/", {"file": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("File is too large", response.data.get("error", ""))

    def test_upload_encrypted_pdf_built_with_pypdf(self):
        enc_buf = _create_encrypted_pdf("my_secret_pass")
        file = SimpleUploadedFile("locked.pdf", enc_buf.getvalue(), content_type="application/pdf")
        response = self.client.post("/api/upload/", {"file": file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"error": "Could not read this PDF. It may be corrupted or password protected."},
        )

    def test_upload_empty_chunks(self):
        pages = ExtractedPages([{"page": 1, "text": "Some text"}], total_pages=1)
        with patch("rag.views.extract_pages", return_value=pages), \
             patch("rag.views.split_into_chunks", return_value=[]):
            file = SimpleUploadedFile("doc.pdf", b"%PDF-dummy", content_type="application/pdf")
            response = self.client.post("/api/upload/", {"file": file}, format="multipart")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data, {"error": "No readable text found in this PDF."})

    def test_upload_success_and_call_order(self):
        call_order = []

        def mock_embed(texts):
            call_order.append("embed_texts")
            return [[0.1, 0.2]] * len(texts)

        def mock_reset():
            call_order.append("reset_collection")

        pages = ExtractedPages([{"page": 1, "text": "Page one text"}], total_pages=5)
        chunks = [{"page": 1, "text": "Chunk text"}]

        with patch("rag.views.extract_pages", return_value=pages), \
             patch("rag.views.split_into_chunks", return_value=chunks), \
             patch("rag.views.embed_texts", side_effect=mock_embed), \
             patch("rag.views.reset_collection", side_effect=mock_reset), \
             patch("rag.views.store_chunks") as mock_store:
            file = SimpleUploadedFile("doc.pdf", b"%PDF-dummy", content_type="application/pdf")
            response = self.client.post("/api/upload/", {"file": file}, format="multipart")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["pages"], 5)
            self.assertEqual(response.data["chunks"], 1)
            self.assertEqual(call_order, ["embed_texts", "reset_collection"])
            mock_store.assert_called_once()

    def test_upload_embed_failure_does_not_reset_collection(self):
        pages = ExtractedPages([{"page": 1, "text": "Text"}], total_pages=3)
        chunks = [{"page": 1, "text": "Chunk text"}]

        with patch("rag.views.extract_pages", return_value=pages), \
             patch("rag.views.split_into_chunks", return_value=chunks), \
             patch("rag.views.embed_texts", side_effect=GeminiBusyError("busy")), \
             patch("rag.views.reset_collection") as mock_reset:
            file = SimpleUploadedFile("doc.pdf", b"%PDF-dummy", content_type="application/pdf")
            response = self.client.post("/api/upload/", {"file": file}, format="multipart")
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            mock_reset.assert_not_called()

        with patch("rag.views.extract_pages", return_value=pages), \
             patch("rag.views.split_into_chunks", return_value=chunks), \
             patch("rag.views.embed_texts", side_effect=RuntimeError("unknown error")), \
             patch("rag.views.reset_collection") as mock_reset:
            file = SimpleUploadedFile("doc.pdf", b"%PDF-dummy", content_type="application/pdf")
            response = self.client.post("/api/upload/", {"file": file}, format="multipart")
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            mock_reset.assert_not_called()

    def test_simultaneous_uploads_never_interleave_reset_and_store(self):
        events = []
        lock_check = []
        active_critical_section = False
        cs_lock = threading.Lock()

        def mock_embed(texts):
            return [[0.1, 0.2]] * len(texts)

        def mock_reset():
            nonlocal active_critical_section
            with cs_lock:
                if active_critical_section:
                    lock_check.append("INTERLEAVED")
                active_critical_section = True
            events.append(("reset", threading.get_ident()))
            time.sleep(0.02)

        def mock_store(chunks, vectors):
            nonlocal active_critical_section
            events.append(("store", threading.get_ident()))
            time.sleep(0.02)
            with cs_lock:
                active_critical_section = False

        pages = ExtractedPages([{"page": 1, "text": "Text"}], total_pages=1)
        chunks = [{"page": 1, "text": "Text"}]

        with patch("rag.views.extract_pages", return_value=pages), \
             patch("rag.views.split_into_chunks", return_value=chunks), \
             patch("rag.views.embed_texts", side_effect=mock_embed), \
             patch("rag.views.reset_collection", side_effect=mock_reset), \
             patch("rag.views.store_chunks", side_effect=mock_store):

            def run_upload():
                client = APIClient()
                file = SimpleUploadedFile("doc.pdf", b"%PDF-dummy", content_type="application/pdf")
                resp = client.post("/api/upload/", {"file": file}, format="multipart")
                self.assertEqual(resp.status_code, status.HTTP_200_OK)

            t1 = threading.Thread(target=run_upload)
            t2 = threading.Thread(target=run_upload)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        self.assertEqual(lock_check, [], "Upload critical sections interleaved!")
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0][0], "reset")
        self.assertEqual(events[1][0], "store")
        self.assertEqual(events[0][1], events[1][1])
        self.assertEqual(events[2][0], "reset")
        self.assertEqual(events[3][0], "store")
        self.assertEqual(events[2][1], events[3][1])


class AskEndpointTests(SilentTestCase):
    """Test POST /api/ask/ endpoint."""

    def setUp(self):
        self.client = APIClient()

    def test_ask_blank_question(self):
        response = self.client.post("/api/ask/", {"question": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": "Question is required."})

    def test_ask_list_body(self):
        response = self.client.post("/api/ask/", ["not a dict"], format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": "Question is required."})

    def test_ask_int_question(self):
        response = self.client.post("/api/ask/", {"question": 12345}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": "Question is required."})

    def test_ask_empty_store_does_not_call_embed_query(self):
        with patch("rag.views.get_chunk_count", return_value=0), \
             patch("rag.views.embed_query") as mock_embed:
            response = self.client.post("/api/ask/", {"question": "What is RAG?"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data, {"error": "Please upload a PDF first."})
            mock_embed.assert_not_called()

    def test_ask_success(self):
        with patch("rag.views.get_chunk_count", return_value=3), \
             patch("rag.views.embed_query", return_value=[0.1]), \
             patch("rag.views.search", return_value=[{"page": 1, "text": "Found"}]), \
             patch("rag.views.generate_answer", return_value={"answer": "Yes (Page 1)", "sources": [{"page": 1, "text": "Found"}]}):
            response = self.client.post("/api/ask/", {"question": "Valid question?"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["answer"], "Yes (Page 1)")
            self.assertEqual(len(response.data["sources"]), 1)

    def test_ask_gemini_busy_error(self):
        with patch("rag.views.get_chunk_count", return_value=1), \
             patch("rag.views.embed_query", side_effect=GeminiBusyError("busy")):
            response = self.client.post("/api/ask/", {"question": "Question?"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(
                response.data,
                {"error": "The AI service is busy. Please try again in a few minutes."},
            )

    def test_ask_gemini_quota_error(self):
        with patch("rag.views.get_chunk_count", return_value=1), \
             patch("rag.views.embed_query", side_effect=GeminiQuotaError("daily limit")):
            response = self.client.post("/api/ask/", {"question": "Question?"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(
                response.data,
                {"error": "Daily AI limit reached. Please try again later."},
            )

    def test_ask_runtime_error(self):
        with patch("rag.views.get_chunk_count", return_value=1), \
             patch("rag.views.embed_query", side_effect=RuntimeError("unexpected")):
            response = self.client.post("/api/ask/", {"question": "Question?"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(response.data, {"error": "Something went wrong on the server."})

    def test_ask_get_chunk_count_error(self):
        with patch("rag.views.get_chunk_count", side_effect=Exception("Database error")):
            response = self.client.post("/api/ask/", {"question": "Question?"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(response.data, {"error": "Something went wrong on the server."})


class QuizEndpointTests(SilentTestCase):
    """Test POST /api/quiz/ endpoint."""

    def setUp(self):
        self.client = APIClient()

    def test_quiz_default_count(self):
        sample_questions = [
            {"question": "Q1", "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "(Page 1)"}
        ]
        with patch("rag.views.get_quiz_chunks", return_value=[{"page": 1, "text": "t"}]), \
             patch("rag.views.generate_quiz", return_value=sample_questions) as mock_gen:
            response = self.client.post("/api/quiz/", {}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_gen.assert_called_once_with([{"page": 1, "text": "t"}], QUIZ_DEFAULT_QUESTIONS)

    def test_quiz_invalid_counts_do_not_call_generate_quiz(self):
        invalid_values = [0, 11, "5", True, [5]]
        for val in invalid_values:
            with patch("rag.views.generate_quiz") as mock_gen:
                response = self.client.post("/api/quiz/", {"num_questions": val}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    response.data,
                    {"error": "Number of questions must be between 1 and 10."},
                )
                mock_gen.assert_not_called()

    def test_quiz_non_dict_body(self):
        response = self.client.post("/api/quiz/", ["not-dict"], format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"error": "Number of questions must be between 1 and 10."},
        )

    def test_quiz_empty_store(self):
        with patch("rag.views.get_quiz_chunks", return_value=[]):
            response = self.client.post("/api/quiz/", {"num_questions": 3}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data, {"error": "Please upload a PDF first."})

    def test_quiz_generation_error(self):
        with patch("rag.views.get_quiz_chunks", return_value=[{"page": 1, "text": "t"}]), \
             patch("rag.views.generate_quiz", side_effect=QuizGenerationError("parse error")):
            response = self.client.post("/api/quiz/", {"num_questions": 3}, format="json")
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertEqual(response.data, {"error": "Could not generate a valid quiz. Please try again."})

    def test_quiz_success(self):
        sample = [{"question": "Q1", "options": ["a", "b", "c", "d"], "correct_index": 1, "explanation": "(Page 2)"}]
        with patch("rag.views.get_quiz_chunks", return_value=[{"page": 2, "text": "t"}]), \
             patch("rag.views.generate_quiz", return_value=sample):
            response = self.client.post("/api/quiz/", {"num_questions": 1}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, {"questions": sample})


class GeneratorSourceFilteringTests(SilentTestCase):
    """Test source citation filtering in generate_answer."""

    def setUp(self):
        self.chunks = [
            {"page": 1, "text": "Page one details."},
            {"page": 2, "text": "Page two details."},
            {"page": 3, "text": "Page three details."},
        ]

    def test_single_cited_page(self):
        with patch("rag.services.generator.generate_text", return_value="The answer is 42 (Page 2)."):
            result = generate_answer("What is the answer?", self.chunks)
            self.assertEqual(result["answer"], "The answer is 42 (Page 2).")
            self.assertEqual(len(result["sources"]), 1)
            self.assertEqual(result["sources"][0]["page"], 2)

    def test_multiple_cited_pages(self):
        with patch("rag.services.generator.generate_text", return_value="Found in (Pages 1, 3)."):
            result = generate_answer("What is the answer?", self.chunks)
            self.assertEqual(len(result["sources"]), 2)
            pages = {s["page"] for s in result["sources"]}
            self.assertEqual(pages, {1, 3})

    def test_range_citation_expansion_hyphen(self):
        with patch("rag.services.generator.generate_text", return_value="Summary in (Pages 2-3)."):
            result = generate_answer("What is the answer?", self.chunks)
            self.assertEqual(len(result["sources"]), 2)
            pages = {s["page"] for s in result["sources"]}
            self.assertEqual(pages, {2, 3})

    def test_range_citation_expansion_to(self):
        with patch("rag.services.generator.generate_text", return_value="Details in (Pages 1 to 3)."):
            result = generate_answer("What is the answer?", self.chunks)
            self.assertEqual(len(result["sources"]), 3)
            pages = {s["page"] for s in result["sources"]}
            self.assertEqual(pages, {1, 2, 3})

    def test_range_citation_cap_at_50_pages(self):
        cited = _extract_cited_pages("Refer to (Pages 1 to 100).")
        self.assertEqual(len(cited), 50)
        self.assertEqual(min(cited), 1)
        self.assertEqual(max(cited), 50)

    def test_range_citation_hyphen_with_spaces(self):
        cited = _extract_cited_pages("Found in (Pages 2 - 4).")
        self.assertEqual(cited, {2, 3, 4})

    def test_no_citation_fallback_returns_all_chunks(self):
        with patch("rag.services.generator.generate_text", return_value="The answer is clear with no pages."):
            result = generate_answer("What is the answer?", self.chunks)
            self.assertEqual(len(result["sources"]), 3)

    def test_not_found_returns_empty_sources(self):
        with patch("rag.services.generator.generate_text", return_value=NOT_FOUND_MESSAGE):
            result = generate_answer("What is the answer?", self.chunks)
            self.assertEqual(result["answer"], NOT_FOUND_MESSAGE)
            self.assertEqual(result["sources"], [])

        with patch("rag.services.generator.generate_text", return_value=f'"{NOT_FOUND_MESSAGE}"'):
            result = generate_answer("What is the answer?", self.chunks)
            self.assertEqual(result["answer"], NOT_FOUND_MESSAGE)
            self.assertEqual(result["sources"], [])


class CallWithRetryTests(SilentTestCase):
    """Test retry behavior in call_with_retry."""

    def test_per_day_quota_error_raises_immediately_without_retry_or_sleep(self):
        err = Exception("GenerateRequestsPerDayPerProjectPerModel quota reached")
        err.code = 429
        mock_fn = MagicMock(side_effect=err)

        with patch("time.sleep") as mock_sleep:
            with self.assertRaises(GeminiQuotaError):
                call_with_retry(mock_fn)
            self.assertEqual(mock_fn.call_count, 1)
            mock_sleep.assert_not_called()

    def test_normal_429_retries_and_raises_busy_error(self):
        err = Exception("Rate limit exceeded")
        err.code = 429
        mock_fn = MagicMock(side_effect=err)

        with patch("time.sleep") as mock_sleep:
            with self.assertRaises(GeminiBusyError):
                call_with_retry(mock_fn)
            self.assertEqual(mock_fn.call_count, 4)
            self.assertEqual(mock_sleep.call_count, 3)

    def test_unstructured_429_string_not_treated_as_per_day_quota(self):
        err = ValueError("Error with 429 and PerDay in message")
        mock_fn = MagicMock(side_effect=err)

        with patch("time.sleep") as mock_sleep:
            with self.assertRaises(ValueError):
                call_with_retry(mock_fn)
            self.assertEqual(mock_fn.call_count, 1)
            mock_sleep.assert_not_called()

    def test_transient_error_retries_and_raises_busy_error(self):
        err = Exception("Temporary backend glitch")
        err.code = 503
        mock_fn = MagicMock(side_effect=err)

        with patch("time.sleep") as mock_sleep:
            with self.assertRaises(GeminiBusyError):
                call_with_retry(mock_fn)
            self.assertEqual(mock_fn.call_count, 4)
            self.assertEqual(mock_sleep.call_count, 3)


class VectorStoreIsolatedTests(SilentTestCase):
    """Test vector store chunk ordering, sampling, and reset using a temporary directory."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.orig_chroma_path = vector_store.CHROMA_PATH
        self.orig_client = vector_store._client

        vector_store.CHROMA_PATH = Path(self.temp_dir.name)
        vector_store._client = None

    def tearDown(self):
        vector_store._client = None
        vector_store.CHROMA_PATH = self.orig_chroma_path
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_parse_chunk_id_invalid_logs_warning_and_returns_none(self):
        logging.disable(logging.NOTSET)
        try:
            with self.assertLogs("rag.services.vector_store", level="WARNING") as cm:
                result = vector_store._parse_chunk_id("invalid-format")
                self.assertIsNone(result)
                self.assertTrue(any("Invalid chunk ID format" in msg for msg in cm.output))
        finally:
            logging.disable(logging.CRITICAL)

    def test_get_quiz_chunks_ordering_sampling_and_reset(self):
        chunks = [{"page": i + 1, "text": f"Chunk text {i}"} for i in range(20)]
        vectors = [[float(i) * 0.05] * 4 for i in range(20)]

        vector_store.store_chunks(chunks, vectors)
        self.assertEqual(vector_store.get_chunk_count(), 20)

        quiz_chunks = vector_store.get_quiz_chunks(max_chunks=5)
        self.assertEqual(len(quiz_chunks), 5)
        pages = [c["page"] for c in quiz_chunks]
        self.assertEqual(pages, sorted(pages))
        self.assertEqual(pages[0], 1)
        self.assertEqual(pages[-1], 20)

        vector_store.reset_collection()
        self.assertEqual(vector_store.get_chunk_count(), 0)
        self.assertEqual(vector_store.get_quiz_chunks(), [])

    def test_get_quiz_chunks_large_collection_2000(self):
        total_chunks = 2000
        max_chunks = 12
        chunks = [{"page": i + 1, "text": f"Chunk text {i}"} for i in range(total_chunks)]
        vectors = [[0.01, 0.02, 0.03, 0.04] for _ in range(total_chunks)]

        vector_store.store_chunks(chunks, vectors)
        self.assertEqual(vector_store.get_chunk_count(), total_chunks)

        quiz_chunks = vector_store.get_quiz_chunks(max_chunks=max_chunks)
        self.assertEqual(len(quiz_chunks), max_chunks)
        pages = [c["page"] for c in quiz_chunks]
        self.assertEqual(pages, sorted(pages))
        self.assertEqual(pages[0], 1)
        self.assertEqual(pages[-1], 2000)
        self.assertEqual(quiz_chunks[0]["text"], "Chunk text 0")
        self.assertEqual(quiz_chunks[-1]["text"], "Chunk text 1999")


class ConfigModelTests(SilentTestCase):
    """Test model retrieval helpers in config."""

    def test_missing_generation_model_raises_runtime_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError) as cm:
                get_generation_model()
            self.assertIn("GEMINI_GENERATION_MODEL", str(cm.exception))

    def test_missing_embedding_model_raises_runtime_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError) as cm:
                get_embedding_model()
            self.assertIn("GEMINI_EMBEDDING_MODEL", str(cm.exception))

    def test_get_embedding_model_returns_exact_str(self):
        with patch.dict("os.environ", {"GEMINI_EMBEDDING_MODEL": "text-embedding-004"}):
            model = get_embedding_model()
            self.assertEqual(model, "text-embedding-004")
            self.assertIs(type(model), str)

    def test_embed_passes_non_empty_str_model_to_client(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_emb = MagicMock()
        mock_emb.values = [0.1, 0.2]
        mock_response.embeddings = [mock_emb]
        mock_client.models.embed_content.return_value = mock_response

        with patch("rag.services.embeddings.get_gemini_client", return_value=mock_client), \
             patch("rag.services.embeddings.get_embedding_model", return_value="text-embedding-004"):
            vectors = _embed(["sample text"], task_type="RETRIEVAL_DOCUMENT")
            self.assertEqual(vectors, [[0.1, 0.2]])
            mock_client.models.embed_content.assert_called_once()
            _, kwargs = mock_client.models.embed_content.call_args
            model_arg = kwargs.get("model")
            self.assertIs(type(model_arg), str)
            self.assertTrue(len(model_arg) > 0)
            self.assertEqual(model_arg, "text-embedding-004")


class HealthCheckTests(TestCase):
    def test_health_check_endpoint(self):
        client = APIClient()
        response = client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_api_health_check_endpoint(self):
        client = APIClient()
        response = client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
