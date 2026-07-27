# LearnCom Prototype

Learning Companion Prototype is an integrated teacher-student learning support system. It combines a Next.js frontend, a Next.js API backend, PostgreSQL/Prisma storage, optional Redis/Qdrant services, and a Python model service for material ingestion, RAG answers, quiz support, and multimodal attachment handling.

## What Is Included

- Teacher dashboard for courses, sessions, materials, rubrics, attendance, and session summaries.
- Student session chat with persistent chat history and optional image attachments.
- Material upload and download flow for session files.
- RAG-based answers from uploaded course materials, with answer references.
- Readiness quiz flow split into pre-class and post-class use cases.
- Quiz scoring against session criteria/rubrics, with per-student review feedback.
- Attendance check-in using uploaded photos, scheduled across a session time window.
- Teacher session summary with question feed, attendance photos, chat images, quiz overview, and most asked topics linked to material references.

## Repository Layout

```text
model/
  src/                         Python model, RAG, ingestion, multimodal agents
  tests/                       Python tests
  configs/                     Model/runtime configuration
  prompts/                     Prompt templates
  schemas/                     Data schemas
  integrated/
    backend/                   Next.js API backend, Prisma schema, seed script
    frontend/                  Next.js frontend UI
```

## Prerequisites

- Node.js 20 or newer
- npm
- Python 3.11
- PostgreSQL 15 or Docker Desktop
- Optional: Redis and Qdrant if you want the full local stack
- Gemini API key for paid AI answers and multimodal processing

## Environment Setup

Create backend environment file:

```powershell
cd model\integrated\backend
Copy-Item .env.example .env
```

A typical local backend `.env` looks like this:

```env
DATABASE_URL="postgresql://admin:password@localhost:5432/prestudy"
REDIS_URL="redis://localhost:6379"
NEXTAUTH_SECRET="change-this-secret"
NEXTAUTH_URL="http://localhost:3000"
AI_SERVICE_URL="http://127.0.0.1:8000"
GEMINI_API_KEY="your-gemini-api-key"
GEMINI_API_BASE_URL="https://generativelanguage.googleapis.com/v1beta"
GEMINI_TEXT_MODEL="gemini-3.6-flash"
QDRANT_URL="http://localhost:6333"
UPLOAD_PATH=""
```

Create frontend environment file:

```powershell
cd model\integrated\frontend
Copy-Item .env.example .env.local
```

Typical frontend `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:3000
NEXT_PUBLIC_MODEL_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_SESSION_ID=
NEXT_PUBLIC_DEFAULT_SUBJECT_ID=
```

For the Python model service, copy `model/.env.example` to `model/.env` and fill in the Gemini or external LLM settings you want to use.

## Database Setup

If Docker Desktop is available, start PostgreSQL, Redis, and Qdrant from the backend folder:

```powershell
cd model\integrated\backend
docker compose up -d
```

If Docker is not available, start PostgreSQL manually and create a database named `prestudy` that matches `DATABASE_URL`.

Push the Prisma schema and seed users:

```powershell
cd model\integrated\backend
npm install
npx prisma db push
npm run seed
```

Seed users include teacher and student test accounts. Check `model/integrated/backend/prisma/seed.js` for the exact email/password values.

## Running Locally

Run the Python model API:

```powershell
cd model
pip install -r requirements.txt
python -m uvicorn src.service.api:app --reload --host 127.0.0.1 --port 8000
```

Run the backend API:

```powershell
cd model\integrated\backend
npm run dev
```

Run the frontend:

```powershell
cd model\integrated\frontend
npm install
npm run dev
```

Default local URLs:

- Frontend: `http://localhost:3001`
- Backend: `http://localhost:3000`
- Model API docs: `http://127.0.0.1:8000/docs`

If a port is already in use, Next.js may choose another port. Use the URL shown in the terminal.

## Suggested End-to-End Test Flow

1. Log in as a teacher.
2. Create a course.
3. Create a session with date, start time, and end time.
4. Upload materials and rubrics for the target session.
5. Log in as a student.
6. Open the active session.
7. Ask a text question and an image-attached question.
8. Wait for or trigger the attendance window, upload a check-in photo, and confirm the checked-in state.
9. Take the pre-class readiness quiz.
10. Take the post-class quiz and confirm rubric-based feedback.
11. Return to the teacher session summary and check questions, attendance photos, chat images, quiz overview, and most asked topics.

## Useful Commands

Backend build:

```powershell
cd model\integrated\backend
npm run build
```

Frontend build:

```powershell
cd model\integrated\frontend
npm run build
```

Python tests:

```powershell
cd model
pytest
```

Reset local database data:

```powershell
cd model\integrated\backend
npx prisma db push --force-reset
npm run seed
```

## Notes

- Do not commit real `.env` files or API keys.
- Gemini quota and billing affect AI answer generation and multimodal image analysis.
- Text-only RAG answers can still work when vision quota is unavailable, depending on configured providers and uploaded material coverage.
- Material and attendance uploads are stored locally during development.
- Some Turbopack warnings can appear around dynamic file download routes; verify downloads after build when changing those routes.

## GitHub

Repository: https://github.com/Taoiew/LearnCom_Prototype
