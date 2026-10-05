# RAG PDF Study Assistant

Upload a PDF, ask questions about it, and generate quizzes from its content.

## Stack
Python, Django + Django REST Framework, pypdf, LangChain text splitter,
Gemini embeddings and Gemini Flash, ChromaDB, React.

## How it works
1. **Indexing:** PDF -> text -> chunks -> Gemini embeddings -> ChromaDB
2. **Q&A:** question -> embedding -> similar chunks -> Gemini Flash -> answer
3. **Quiz:** retrieved chunks -> Gemini Flash -> multiple-choice questions

## Status
Backend is complete (upload, ask, quiz). React UI is in progress (Step 7).

## API

### 1. Upload PDF
- **Method:** `POST`
- **URL:** `/api/upload/`
- **Request:** Multipart form-data with `file` field (.pdf only, maximum size 10 MB).
- **Success (200 OK):**
```json
{
  "message": "PDF processed successfully.",
  "pages": 4,
  "chunks": 11
}
```

### 2. Ask Question
- **Method:** `POST`
- **URL:** `/api/ask/`
- **Request:** JSON
```json
{
  "question": "What is the class size limit?"
}
```
- **Success (200 OK):**
```json
{
  "answer": "Class sizes are capped at 18 students.",
  "sources": [
    {
      "page": 1,
      "text": "Class size is capped at 18 students..."
    }
  ]
}
```

### 3. Generate Quiz
- **Method:** `POST`
- **URL:** `/api/quiz/`
- **Request:** Optional JSON (`num_questions` between 1 and 10, default is 5)
```json
{
  "num_questions": 3
}
```
- **Success (200 OK):**
```json
{
  "questions": [
    {
      "question": "What is the maximum class size?",
      "options": ["12", "15", "18", "40"],
      "correct_index": 2,
      "explanation": "Class size is capped at 18 students. (Page 1)"
    }
  ]
}
```

### Common Error Codes
- **400 Bad Request:** Invalid input, missing question, invalid question count, or please upload a PDF first.
- **500 Internal Server Error:** Server error or quiz generation could not produce valid questions.
- **503 Service Unavailable:** AI service is busy or rate-limited.

## Known Limitations
- **Single global collection:** Uploading a new PDF replaces the previous document.
- **No user accounts:** No authentication or per-user session isolation.
- **No OCR:** Scanned or image-only PDFs with no readable text are not supported.
- **Development settings only:** Uses `DEBUG = True` and a hardcoded secret key; `DEBUG` and `SECRET_KEY` must come from `.env` before production deployment.

## Backend setup
1. `cd backend`
2. `python -m venv venv` and activate it
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and set the required variables (placeholders only, never commit real keys):
   - `GEMINI_API_KEY=your_key_here`
   - `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`
   - `GEMINI_GENERATION_MODEL=gemini-3.5-flash`
5. `python manage.py runserver`

## Run everything
From the project root:
1. `npm install`
2. `npm --prefix frontend install`
3. Set up the backend (see above)
4. `npm run dev`

Backend: http://127.0.0.1:8000 | Frontend: http://localhost:5173
