# AI Candidate Screening & Shortlisting System

An end-to-end AI-powered hiring platform that automates CV screening, semantic candidate matching, and AI-driven interviews.

---

## What It Does

- **Admin** posts jobs, runs AI screening, views match scores, shortlists or rejects candidates
- **Candidate** browses jobs, applies with a CV, automatically receives an AI interview, tracks status
- **AI Pipeline** runs fully automatically after every application — no manual trigger needed

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React, Tailwind CSS |
| Backend | FastAPI, Python 3.11 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Vector DB | Pinecone |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | Groq API (llama3-8b-8192) |
| Speech-to-Text | OpenAI Whisper |
| Text-to-Speech | gTTS |

---

## Project Structure

```
ai-candidate-screening/
├── backend/
│   ├── api/              # Route handlers (jobs, candidates, applications, interview, voice)
│   ├── models/           # SQLAlchemy ORM tables
│   ├── schemas/          # Pydantic request/response validation
│   ├── services/         # Business logic + AI pipeline
│   ├── utils/            # PDF processing, skill extraction, audio utilities
│   ├── database/         # SQLAlchemy engine + session
│   ├── uploads/          # Uploaded CVs stored here
│   ├── audio/            # TTS question audio + voice recordings
│   ├── main.py           # FastAPI entry point
│   └── requirements.txt
└── frontend/
    ├── pages/
    │   ├── index.js              # Admin dashboard
    │   ├── jobs/                 # Job management
    │   ├── candidates/           # Candidate results + screening
    │   ├── careers/              # Public job listings
    │   ├── apply/                # Application form
    │   ├── applications/status   # Candidate status tracker
    │   └── interview/            # AI interview interface
    ├── components/       # Reusable UI components
    └── services/api.js   # All Axios API calls
```

---

## Automatic AI Pipeline

When a candidate submits an application the following runs automatically in the background:

```
CV Uploaded → Resume Text Extracted → Candidate Embedding Generated
→ Job Embedding Generated → Semantic Matching (score + recommendation)
→ Interview Questions Generated (Groq LLM)
→ Interview Session Available on Status Page (~60 seconds)
```

---

## Getting Started

### Requirements
- Python 3.11+
- Node.js 18+
- Pinecone account (free) — https://app.pinecone.io
- Groq account (free) — https://console.groq.com

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt

cp .env.example .env
# Fill in PINECONE_API_KEY and GROQ_API_KEY

uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install

# Create .env.local and add:
# NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
```

---

## Environment Variables

```env
DATABASE_URL=sqlite:///./screening.db
PINECONE_API_KEY=your_key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=job-embeddings
GROQ_API_KEY=your_key
GROQ_MODEL=llama3-8b-8192
EMBEDDING_MODEL=all-MiniLM-L6-v2
WHISPER_MODEL=base
CORS_ORIGINS=http://localhost:3000
```

---

## Scoring Formula

```
After Matching:   Final = (CV Similarity × 0.4) + (Skill Match × 0.4) + (Experience × 0.2)
After Interview:  Final = (CV Similarity × 0.3) + (Skill Match × 0.4) + (Interview × 0.3)

80%+  → Highly Recommended
60%+  → Recommended
40%+  → Needs Improvement
<40%  → Not Recommended
```

---

## Deployment

| Service | Platform |
|---------|---------|
| Frontend | Vercel |
| Backend + Database | Render |

For production, set `DATABASE_URL` to a PostgreSQL connection string in Railway's environment variables. No code changes needed — SQLAlchemy handles the switch automatically.

---

## API Overview

| Prefix | Description |
|--------|-------------|
| `/api/*` | Admin — jobs, candidates, dashboard |
| `/portal/*` | Candidate — apply, status, job listings |
| `/resume/*` | CV processing |
| `/embeddings/*` | Pinecone sync |
| `/matching/*` | Semantic scoring |
| `/interview/*` | AI interview sessions |
| `/voice/*` | TTS + speech-to-text |