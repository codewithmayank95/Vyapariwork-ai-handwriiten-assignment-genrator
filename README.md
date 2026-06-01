# AI Handwritten Assignment PDF Generator

Full-stack MVP that generates a handwritten-style assignment PDF using:
- Frontend: HTML/CSS/JS (no framework) — deployable on Cloudflare Pages
- Backend: FastAPI + Pillow (Gemini/Supabase/Firebase optional)

## Features
- Select template: OIST / OCT / Default
- Preview blank sessional page
- Enter student details
- Provide questions manually OR upload an assignment PDF
- Choose answer length (short/medium/long)
- Generate and download final PDF

## Project Structure
```
ai handwritten assignment genrator/
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── blank-sessional/
│       ├── oist.png
│       ├── oct.png
│       └── default.png
└── backend/
    ├── main.py
    ├── config.py
    ├── ai_answer.py
    ├── generator.py
    ├── extract_questions.py
    ├── database.py
    ├── auth.py
    ├── requirements.txt
    ├── .env.example
    ├── templates/
    │   ├── oist.png
    │   ├── oct.png
    │   └── default.png
    ├── fonts/
    │   ├── README.txt
    │   └── Kalam-Regular.ttf  (optional)
    ├── uploads/
    ├── outputs/
    └── temp/
```

## Backend Setup (FastAPI)
1) Open a terminal:
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Notes:
- On Python 3.14, `supabase` is skipped by default in `requirements.txt` to avoid native build tool issues. Use Python 3.11–3.13 (recommended) if you want Supabase support.

2) Configure env:
```bash
copy .env.example .env
```
Add keys as needed (Gemini/Supabase/Firebase are optional).

3) Run:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:
- `GET http://127.0.0.1:8000/health`

Outputs:
- PDFs are served from `http://127.0.0.1:8000/outputs/...`

## Frontend Run
- Open `frontend/index.html` in a browser
- Or deploy the `frontend/` folder to Cloudflare Pages

## Templates (Important)
- Frontend preview images: `frontend/blank-sessional/*.png`
- Backend render templates: `backend/templates/*.png`

Replace these placeholder templates with your real college sessional page images for best results.

## Font (Optional but Recommended)
Put the handwritten font at:
- `backend/fonts/Kalam-Regular.ttf`

If the font is missing, the backend still works using a default font.

## PDF Question Extraction Notes
The backend tries:
1) Text extraction with `pdfplumber` (best for text PDFs)
2) Text extraction with `pymupdf` (fallback)
3) OCR with `pdf2image` + `pytesseract` (for scanned PDFs)

OCR may require system dependencies:
- Windows: install Tesseract OCR and Poppler, then ensure they are on PATH.

## Deployment Guide

### Cloudflare Pages (Frontend)
1) Push the repo to GitHub
2) Create a Cloudflare Pages project
3) Set **Build output directory** to `frontend`
4) No build command needed (static site)

Update `frontend/script.js` `BACKEND_URL` to your deployed backend URL.

### Render (Backend)
1) Create a new Web Service on Render from your repo
2) Set root directory to `backend`
3) Build command:
```bash
pip install -r requirements.txt
```
4) Start command:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
5) Add env vars in Render (optional):
- `GEMINI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `FRONTEND_URL`
- `FIREBASE_CREDENTIALS_PATH`

## Supabase SQL (Optional)
Run this in Supabase SQL editor:
```sql
CREATE TABLE pdf_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text,
    name text,
    roll_number text,
    subject text,
    college text,
    questions text,
    status text,
    pdf_url text,
    pages integer,
    created_at timestamp DEFAULT now()
);
```
