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
Skeleton only. Implementation in progress.

## Backend setup
1. `cd backend`
2. `python -m venv venv` and activate it
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and add your Gemini API key
5. `python manage.py runserver`

## Run everything
From the project root:
1. `npm install`
2. `npm --prefix frontend install`
3. Set up the backend (see above)
4. `npm run dev`

Backend: http://127.0.0.1:8000 | Frontend: http://localhost:5173
