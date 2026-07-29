# Learning Companion Prototype

Learning Companion is a full-stack learning support prototype for teacher-led sessions. It includes a Python model service, a Next.js API backend, and a Next.js frontend for teachers and students.

Current flows include:

- Teacher course and session management
- Material and rubric upload
- Student chat with RAG/model answers
- Chat history
- Photo attendance check-in with randomized student check-in windows
- Pre-class and after-class quizzes
- Student progress dashboard
- Teacher session summary with attendance, questions, images, topics, quiz overview, and next-class readiness

## Quick Start

Run these from the repository folder:

```powershell
cd D:\Korakot\Learning-Companion-upload\model
```

Create env files:

```powershell
Copy-Item .env.example .env
Copy-Item integrated\backend\.env.example integrated\backend\.env
Copy-Item integrated\frontend\.env.example integrated\frontend\.env.local
```

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cd integrated\backend
npm install

cd ..\frontend
npm install

cd ..\..
```

Start PostgreSQL/Redis/Qdrant with Docker Desktop:

```powershell
cd integrated\backend
docker-compose up -d
```

Set this in `integrated/backend/.env` if using the included Docker database:

```env
DATABASE_URL=postgresql://admin:password@localhost:5432/prestudy
REDIS_URL=redis://localhost:6379
NEXTAUTH_SECRET=replace-with-a-long-random-secret
NEXTAUTH_URL=http://localhost:3000
AI_SERVICE_URL=http://127.0.0.1:8000
GEMINI_API_KEY=your-gemini-api-key
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_TEXT_MODEL=gemini-3.6-flash
QDRANT_URL=http://127.0.0.1:6333
UPLOAD_PATH=uploads
```

Push the schema and seed demo users:

```powershell
npx prisma db push
npm run seed
```

Start all services in three terminals.

Terminal 1, model service:

```powershell
cd D:\Korakot\Learning-Companion-upload\model
.\.venv\Scripts\Activate.ps1
python -m uvicorn src.service.api:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2, backend API:

```powershell
cd D:\Korakot\Learning-Companion-upload\model\integrated\backend
npm run dev
```

Terminal 3, frontend:

```powershell
cd D:\Korakot\Learning-Companion-upload\model\integrated\frontend
npm run dev -- -p 3001
```

Open the app:

```text
http://127.0.0.1:3001/login
```

Demo accounts:

```text
Teacher: teacher@learning.com / teacher1234
Student: student@learning.com / student1234
```

## Environment Setup

### Model Service `.env`

File:

```text
model/.env
```

Use this for the Python model service and multimodal/RAG pipeline:

```env
EXTERNAL_LLM_BASE_URL=
EXTERNAL_LLM_API_KEY=
EXTERNAL_LLM_MODEL=

LOCAL_LLM_BASE_URL=http://127.0.0.1:8000/v1
LOCAL_LLM_API_KEY=local
LOCAL_LLM_MODEL=

LLM_TIMEOUT_SECONDS=60

GEMINI_API_KEY=your-gemini-api-key
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_VISION_MODEL=gemini-3.6-flash
GEMINI_VISION_TIMEOUT_SECONDS=90
GEMINI_VISION_MAX_RETRIES=3
GEMINI_VISION_TEMPERATURE=0.1
GEMINI_VISION_MAX_OUTPUT_TOKENS=8192

MATERIAL_MULTIMODAL_AGENT=external
CHAT_ATTACHMENT_MULTIMODAL_AGENT=external
```

Notes:

- `GEMINI_API_KEY` is required for Gemini-backed material processing, vision chat, quiz generation, and grading.
- `MATERIAL_MULTIMODAL_AGENT=external` sends material processing to the configured external provider.
- `CHAT_ATTACHMENT_MULTIMODAL_AGENT=external` sends image-based chat questions to the external provider.

### Backend `.env`

File:

```text
model/integrated/backend/.env
```

Recommended local config:

```env
DATABASE_URL=postgresql://admin:password@localhost:5432/prestudy
REDIS_URL=redis://localhost:6379
NEXTAUTH_SECRET=replace-with-a-long-random-secret
NEXTAUTH_URL=http://localhost:3000
AI_SERVICE_URL=http://127.0.0.1:8000
GEMINI_API_KEY=your-gemini-api-key
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_TEXT_MODEL=gemini-3.6-flash
QDRANT_URL=http://127.0.0.1:6333
UPLOAD_PATH=uploads
```

### Frontend `.env.local`

File:

```text
model/integrated/frontend/.env.local
```

Recommended local config:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:3000
NEXT_PUBLIC_MODEL_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_SESSION_ID=
NEXT_PUBLIC_DEFAULT_SUBJECT_ID=
```

## Project Structure

```text
model/
|-- README.md
|-- .env.example
|-- requirements.txt
|-- configs/
|-- data/                         # Runtime/generated model data, ignored by git
|-- docs/
|   |-- project-flow.md
|   `-- system-dataflow.md
|-- prompts/
|-- schemas/
|-- scripts/
|-- src/                          # Python model service
|   |-- agents/
|   |-- evaluation/
|   |-- ingestion/
|   |-- retrieval/
|   |-- routing/
|   `-- service/
|-- tests/
`-- integrated/
    |-- backend/
    |   |-- .env.example
    |   |-- docker-compose.yml
    |   |-- package.json
    |   |-- prisma/
    |   |   |-- schema.prisma
    |   |   `-- seed.js
    |   |-- src/
    |   |   |-- app/api/v1/        # REST API routes
    |   |   `-- lib/               # Auth, Prisma, AI, upload helpers
    |   `-- uploads/               # Runtime uploaded files, ignored by git
    `-- frontend/
        |-- .env.example
        |-- package.json
        |-- app/                   # Next.js App Router pages
        |-- components/
        `-- lib/
```

## Main URLs

Backend:

```text
http://127.0.0.1:3000
```

Backend Swagger-like route docs are available through the backend app if enabled by the project routes.

Frontend:

```text
http://127.0.0.1:3001
```

Model API:

```text
http://127.0.0.1:8000
```

## Main User Flows

### Teacher

1. Log in as `teacher@learning.com`.
2. Create or select a course from the course selector.
3. Create a session with date, start time, and end time.
4. Upload materials and rubrics in `Materials & prompts`.
5. Open a session summary from the session card.
6. Review:
   - Student attendance and check-in images
   - Student chat questions
   - Uploaded chat images
   - Most asked topics and material references
   - Pre-class and after-class quiz overview
   - Next-class readiness preview and responses
7. Delete test sessions from the session card delete button when needed.

### Student

1. Log in as `student@learning.com`.
2. Open an active session from the student dashboard.
3. Ask questions in chat.
4. Attach images when asking about a slide or screenshot.
5. Wait for the attendance countdown, then check in with a photo.
6. Take the pre-class quiz before class.
7. Take the after-class quiz after class.
8. Review quiz history and weak/strong areas in the progress page.

## AI and Credit Usage

These flows can call Gemini or another external model:

- Material processing after upload
- Chat answers when RAG needs an external answer
- Image-based chat
- Pre-class quiz generation
- After-class quiz generation
- Quiz grading
- Next-class readiness analysis

For cheap smoke testing, avoid these actions and only test auth, course creation, session creation, attendance, history, and summary routes.

## Validation Commands

Backend:

```powershell
cd integrated\backend
.\node_modules\.bin\tsc.cmd --noEmit
npm run lint
npm run build
```

Frontend:

```powershell
cd integrated\frontend
.\node_modules\.bin\tsc.cmd --noEmit
npm run lint
npm run build
```

Model service:

```powershell
cd D:\Korakot\Learning-Companion-upload\model
.\.venv\Scripts\Activate.ps1
pytest
```

## Troubleshooting

### `P1001: Can't reach database server at localhost:5432`

PostgreSQL is not running. Start Docker Desktop, then run:

```powershell
cd integrated\backend
docker-compose up -d
```

Check the port:

```powershell
Test-NetConnection 127.0.0.1 -Port 5432
```

### `DATABASE_URL is required to seed users`

Create `integrated/backend/.env` and set `DATABASE_URL`.

### Login says backend is not ready

Check:

- PostgreSQL is running
- `integrated/backend/.env` exists
- `DATABASE_URL` matches your database user/password
- `npx prisma db push` has been run
- `npm run seed` has been run

### `Invalid or expired token`

Log out and log in again. If you changed `NEXTAUTH_SECRET`, old tokens are invalid.

### Gemini `429` or prepaid credit error

The app reached Gemini quota or billing limits. Wait for quota reset or add billing/credits in Google AI Studio.

### Material download route Turbopack warning

The backend may show a Turbopack/NFT warning around `uploads/[...filePath]/route.ts`. The app can still build and run. It is a tracing warning for dynamic upload file serving, not a direct runtime failure by itself.

## Git Hygiene

The following are local-only and should not be committed:

- `.env`
- `.env.local`
- `.venv/`
- `node_modules/`
- `.next/`
- `data/`
- `integrated/backend/uploads/`
- test PDFs or private course files

## Documentation

Mermaid diagrams:

```text
docs/project-flow.md
docs/system-dataflow.md
```

You can render them with:

- GitHub Markdown preview
- VS Code Mermaid preview extensions
- Mermaid Live Editor
- Markdown tools that support Mermaid
