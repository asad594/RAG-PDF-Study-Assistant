# Deployment Guide: RAG PDF Study Assistant

This guide outlines the exact, step-by-step instructions to deploy the backend to **Railway** and the frontend to **Vercel**.

---

## Deployment Order Overview

1. **Deploy Backend first on Railway** to obtain its public URL.
2. **Deploy Frontend on Vercel**, pointing `VITE_API_URL` to your Railway public URL.
3. **Update Railway environment variables** with the Vercel frontend URL in `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`, then redeploy the backend.

---

## Step 1: Deploy Backend to Railway

1. **Create New Project**:
   - Go to [Railway Dashboard](https://railway.com) and click **New Project** > **Deploy from GitHub repo**.
   - Select the `RAG-PDF-Study-Assistant` repository.

2. **Configure Root Directory & Settings**:
   - In the service **Settings** tab:
     - Set **Root Directory** to `backend`.
     - Verify the build automatically detects Python from `requirements.txt`.
     - In **Deploy**, Railway will pick up the `Procfile` (`web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`) automatically. If setting a manual start command, use:
       ```bash
       gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
       ```

3. **Set Environment Variables**:
   - Go to the **Variables** tab and add the following:
     - `SECRET_KEY`: *A strong random secret string*
     - `DEBUG`: `False`
     - `ALLOWED_HOSTS`: `localhost,127.0.0.1,.railway.app`
     - `GEMINI_API_KEY`: *Your Google Gemini API key*
     - `GEMINI_EMBEDDING_MODEL`: `gemini-embedding-001`
     - `GEMINI_GENERATION_MODEL`: `gemini-3.5-flash`
     - *(Optional)* `CORS_ALLOWED_ORIGINS`: `http://localhost:5173` *(we will add Vercel's URL in Step 3)*
     - *(Optional)* `CSRF_TRUSTED_ORIGINS`: `http://localhost:5173`

4. **Generate Public Domain**:
   - Under **Networking** / **Public Networking**, click **Generate Domain** (e.g., `https://rag-pdf-backend.up.railway.app`).
   - Test the health check endpoint in your browser:
     ```
     https://<your-railway-domain>/health/
     ```
     You should see `{"status": "ok"}`.
   - Copy this URL (without trailing slash) for the next step.

---

## Step 2: Deploy Frontend to Vercel

1. **Import Project**:
   - Go to [Vercel Dashboard](https://vercel.com) and click **Add New...** > **Project**.
   - Select the `RAG-PDF-Study-Assistant` repository.

2. **Configure Project Settings**:
   - **Framework Preset**: Vite
   - **Root Directory**: Click edit and select `frontend`.

3. **Set Environment Variable**:
   - Under **Environment Variables**, add:
     - `VITE_API_URL`: Your Railway backend domain from Step 1 (e.g. `https://rag-pdf-backend.up.railway.app`)

4. **Deploy**:
   - Click **Deploy**.
   - Once deployed, copy your public Vercel frontend URL (e.g. `https://rag-pdf-frontend.vercel.app`).

---

## Step 3: Link Vercel to Railway (CORS & CSRF)

1. Return to your **Railway Backend service** > **Variables** tab.
2. Update `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to include your Vercel URL:
   - `CORS_ALLOWED_ORIGINS`: `https://<your-vercel-domain>.vercel.app,http://localhost:5173`
   - `CSRF_TRUSTED_ORIGINS`: `https://<your-vercel-domain>.vercel.app,http://localhost:5173`
3. Railway will automatically redeploy the backend with the new variables.
4. Visit your Vercel URL and test uploading a PDF, asking a question, or generating a quiz.
