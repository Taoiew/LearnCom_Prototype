# Learning Companion Prototype

Learning Companion is a prototype learning support system for teachers and students. It combines a model service, a Next.js backend API, and a Next.js frontend. The current integrated app supports course and session management, materials, chat, attendance check-in, quizzes, student progress, and teacher session summaries.

## Project Structure

```text
model/
|-- configs/                 # Model and runtime configuration notes
|-- data/                    # Local generated data, ignored by git
|-- docs/                    # Mermaid system flow and dataflow diagrams
|-- integrated/
|   |-- backend/             # Next.js API backend, Prisma, auth, uploads
|   |   |-- prisma/          # Prisma schema and seed script
|   |   |-- public/          # Backend public assets
|   |   |-- src/app/api/v1/  # REST API routes
|   |   |-- src/lib/         # Auth, Prisma, AI service helpers
|   |   `-- uploads/         # Runtime uploaded files, ignored by git
|   `-- frontend/            # Next.js frontend application
|       |-- app/             # App Router pages for teacher/student flows
|       |-- components/      # UI components
|       `-- lib/             # Frontend API client and helpers
|-- prompts/                 # Prompt templates
|-- schemas/                 # Model/data schemas
|-- scripts/                 # Utility scripts
|-- src/                     # Python model service source
|-- tests/                   # Python tests
|-- requirements.txt         # Python dependencies
`-- README.md                # This file
```

## Requirements

- Node.js 24.x or compatible current Node.js
- npm
- Python 3.11+
- PostgreSQL running locally or through Docker
- Optional: Docker Desktop for the backend `docker-compose.yml`
- Gemini API key if you want to use AI chat, vision, quiz generation, or quiz grading

## Environment Files

Create local env files from the examples:

```powershell
Copy-Item integrated\backend\.env.example integrated\backend\.env
Copy-Item integrated\frontend\.env.example integrated\frontend\.env.local
Copy-Item .env.example .env
```

Backend `.env` needs at least:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prestudy
NEXTAUTH_SECRET=replace-with-a-long-random-secret
NEXTAUTH_URL=http://localhost:3000
AI_SERVICE_URL=http://127.0.0.1:8000
GEMINI_API_KEY=your-gemini-key
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_TEXT_MODEL=gemini-3.6-flash
UPLOAD_PATH=uploads
```

Frontend `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:3000
NEXT_PUBLIC_MODEL_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEFAULT_SESSION_ID=
NEXT_PUBLIC_DEFAULT_SUBJECT_ID=
```

Do not commit `.env`, `.env.local`, uploaded files, generated data, `.next`, or `node_modules`.

## Install Dependencies

Install backend dependencies:

```powershell
cd integrated\backend
npm install
```

Install frontend dependencies:

```powershell
cd ..\frontend
npm install
```

Install Python model service dependencies from the root `model/` directory:

```powershell
cd ..\..
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Database Setup

Start PostgreSQL. If Docker Desktop is running, from `integrated/backend`:

```powershell
docker-compose up -d
```

Then push the Prisma schema and seed the demo users:

```powershell
cd integrated\backend
npx prisma db push
npm run seed
```

Seed users:

```text
Teacher: teacher@learning.com / teacher1234
Student: student@learning.com / student1234
```

## Run The App

Terminal 1, start the model service from the root `model/` directory:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn src.service.api:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2, start the backend API:

```powershell
cd integrated\backend
npm run dev
```

Backend URL:

```text
http://127.0.0.1:3000
```

Terminal 3, start the frontend:

```powershell
cd integrated\frontend
npm run dev -- -p 3001
```

Frontend URL:

```text
http://127.0.0.1:3001
```

Open:

```text
http://127.0.0.1:3001/login
```

## Common Flows To Test

Teacher flow:

1. Log in as `teacher@learning.com`.
2. Create a course.
3. Create a session with date, start time, and end time.
4. Upload material and rubric files from `Materials & prompts`.
5. Open the session summary page.
6. Check question feed, attendance, chat images, topic ranking, quiz overview, and next-class readiness.
7. Delete test sessions if needed.

Student flow:

1. Log in as `student@learning.com`.
2. Open an active session.
3. Use the chat box to ask material-based questions.
4. Upload an image in chat when needed.
5. Wait for the attendance slot countdown, then check in with a photo.
6. Take the pre-class and after-class quizzes.
7. Review quiz history and progress dashboard.

AI-credit-sensitive flows:

- Material processing
- Chat answers that require Gemini fallback or vision
- Quiz generation
- Quiz grading
- Next-class readiness analysis

Use these carefully when testing because they may consume Gemini credits.

## Validation Commands

Backend:

```powershell
cd integrated\backend
npm run lint
npm run build
.\node_modules\.bin\tsc.cmd --noEmit
```

Frontend:

```powershell
cd integrated\frontend
npm run lint
npm run build
.\node_modules\.bin\tsc.cmd --noEmit
```

Python model service:

```powershell
cd ..\..
pytest
```

## Documentation

System diagrams are in:

```text
docs/project-flow.md
docs/system-dataflow.md
```

These files use Mermaid diagrams. You can view them in GitHub, VS Code Mermaid preview extensions, Mermaid Live Editor, or Markdown tools that support Mermaid.

## Notes

- The backend uses Prisma with PostgreSQL.
- Uploaded materials, attendance images, and chat images are runtime files and should not be committed.
- The frontend is intentionally kept visually close to the original prototype design.
- Some lint warnings may remain in the frontend, but the app should build successfully.
