# /handoff — Pre-Study Agent Backend

---

## Project Overview
AI-powered pre-study agent for university students supporting before, during, and after class. Agent assesses students against teacher-defined criteria, helps prepare for lectures, catches up students who get lost, and gives teachers detailed insight tracked to semester goals.

---

## Team Structure
```
Chakphong   →  Backend + partially Frontend
Teammate 1  →  Frontend
Teammate 2  →  AI / Model
```

---

## How To Run
```bash
cd backend
docker-compose up -d    # start PostgreSQL, Redis, Qdrant
npm run dev             # start Next.js dev server
```

---

## Critical Next.js 16 Rules — NEVER FORGET

**1. Dynamic params must be awaited:**
```typescript
// WRONG — params resolves as undefined → 500 error
{ params }: { params: { sessionId: string } }
const { sessionId } = params

// CORRECT
{ params }: { params: Promise<{ sessionId: string }> }
const { sessionId } = await params
```

**2. Use proxy.ts not middleware.ts:**
```typescript
// WRONG
src/middleware.ts
export function middleware() {}

// CORRECT
src/proxy.ts
export function proxy() {}
```

---

## Environment Variables
```bash
DATABASE_URL="postgresql://admin:password@localhost:5432/prestudy"
REDIS_URL="redis://localhost:6379"
NEXTAUTH_SECRET="your-secret-key"
NEXTAUTH_URL="http://localhost:3000"
AI_SERVICE_URL="http://localhost:8000"
QDRANT_URL="http://localhost:6333"
UPLOAD_PATH="./uploads"
```

---

## Auth System
JWT stored in httpOnly cookie + Bearer token in Authorization header.

**Reading user in any route:**
```typescript
const userId       = request.headers.get("x-user-id")
const userRole     = request.headers.get("x-user-role")
const userName     = request.headers.get("x-user-name")
const userLanguage = request.headers.get("x-user-language")
const userEmail    = request.headers.get("x-user-email")
```

---

## AI Integration Contract

**Chat:**
```typescript
POST http://localhost:8000/chat
// Send
{
  phase: "before" | "during" | "after",
  language: "th" | "en",
  studentMessage: string,
  recentMessages: Message[],
  summary: string,
  sessionCriteria: Criteria[],
  teacherMaterial: string
}
// Receive
{
  response: string,
  confidence: number,           // below 0.7 = used external API
  usedExternalAPI: boolean,
  externalSource: "gemini" | "deepseek" | null,
  flaggedCriteria: string[],
  detectedLanguage: "th" | "en"
}
```

**Image Analysis:**
```typescript
POST http://localhost:8000/analyze-image
// Send
{
  imageUrl: string,
  sessionId: string,
  availableMaterials: Material[]
}
// Receive
{
  materialId: string | null,
  pageNumber: number | null,
  confidence: number,
  description: string
}
```

**Report Insight:**
```typescript
POST http://localhost:8000/insight
// Send
{
  criteriaResults: CriteriaResult[],
  duringClassLogs: DuringClassLog[],
  caughtUpCount: number,
  totalStudents: number
}
// Receive
{
  insight: string
}
```

**Mock responses active in `src/lib/ai.ts`** — uncomment real calls on integration day.

---

## Database — 18 Tables
```
1.  Users
2.  Subjects
3.  SemesterCriteria
4.  ClassSessions
5.  SessionCriteria
6.  Materials            ← isProcessed flag tracks if chunked to Qdrant
7.  Conversations        ← one per student per phase per session
8.  Messages
9.  ConversationSummary  ← updated every 6 messages
10. Quizzes
11. QuizQuestions        ← tagged to SessionCriteria internally
12. CriteriaResults      ← MET / PARTIAL / NOT_MET per criteria
13. DuringClassLogs
14. SessionReports
15. StudentReports
16. TrainingData         ← external API answers for fine-tuning
17. WeeklySummaries
18. ChatImageLogs        ← images sent in chat + material/page reference
```

**Qdrant** stores material chunk embeddings — NOT in PostgreSQL.

---

## Valid Session Phase Transitions
```
UPCOMING + BEFORE  →  ACTIVE + BEFORE
ACTIVE + BEFORE    →  ACTIVE + DURING
ACTIVE + DURING    →  ACTIVE + AFTER
ACTIVE + AFTER     →  COMPLETED + AFTER
```

---

## What's Done ✅
```
Auth
├── POST /api/v1/auth/register
├── POST /api/v1/auth/login        ← returns token in body
├── GET  /api/v1/auth/session
└── POST /api/v1/auth/logout

Subjects
├── GET/POST /api/v1/subjects
├── GET/PATCH/DELETE /api/v1/subjects/[subjectId]
├── GET/POST /api/v1/subjects/[subjectId]/semester-criteria
└── PATCH/DELETE /api/v1/subjects/[subjectId]/semester-criteria/[criteriaId]

Sessions
├── GET/POST /api/v1/sessions
├── GET/PATCH/DELETE /api/v1/sessions/[sessionId]
├── PATCH /api/v1/sessions/[sessionId]/status
├── GET/POST /api/v1/sessions/[sessionId]/criteria
├── PATCH/DELETE /api/v1/sessions/[sessionId]/criteria/[criteriaId]
├── GET/POST /api/v1/sessions/[sessionId]/materials
└── DELETE /api/v1/sessions/[sessionId]/materials/[materialId]
```

---

## What's NOT Done ❌ — Build These Next

### Priority 1 — Users
```
GET/PATCH /api/v1/users/me
```

### Priority 2 — Chat (most important)
```
POST /api/v1/chat
GET  /api/v1/chat/history/[sessionId]
POST /api/v1/chat/upload
POST /api/v1/chat/image-log          ← internal, backend calls automatically
```

### Priority 3 — Quiz
```
POST /api/v1/quiz/generate
POST /api/v1/quiz/submit
GET  /api/v1/quiz/history/[sessionId]
```

### Priority 4 — Reports
```
POST /api/v1/reports/trigger/[sessionId]
GET  /api/v1/reports/session/[sessionId]
GET  /api/v1/reports/student/[studentId]
POST /api/v1/reports/weekly/generate
GET  /api/v1/reports/weekly/[subjectId]
GET  /api/v1/reports/materials/[sessionId]
```

### Priority 5 — Training
```
POST /api/v1/training/store          ← internal, backend calls automatically
```

---

## What Each Unbuilt Route Does

**POST /api/v1/chat**
- Main agent bridge
- Pull conversation context from Redis
- Package context + send to AI teammate at `localhost:8000/chat`
- Store message in PostgreSQL
- Update Redis cache
- Trigger summary every 6 messages
- If AI used external API → store in TrainingData table

**POST /api/v1/chat/upload**
- Student uploads image or file in chat
- Store file in `/uploads/chat/[sessionId]/[studentId]/`
- Send image to AI teammate for analysis
- AI returns materialId + pageNumber
- Store in ChatImageLog
- Return AI response + fileUrl to frontend

**POST /api/v1/quiz/generate**
- Request quiz questions from AI teammate
- Store quiz + questions in DB
- Tag each question to a SessionCriteria
- Never send criteriaId or correctConcept to frontend

**POST /api/v1/quiz/submit**
- Receive student answers
- Send each answer to AI for scoring (separate AI call)
- Store CriteriaResults
- Calculate readiness verdict
- Return score + feedback per criteria

**POST /api/v1/reports/trigger/[sessionId]**
- Check session is COMPLETED
- Aggregate all quiz scores per criteria
- Aggregate during class logs
- Check who completed after class
- Send to AI for insight
- Store SessionReport + StudentReports

**POST /api/v1/reports/weekly/generate**
- Aggregate all sessions in the week
- Calculate avg readiness + semester progress
- Send to AI for natural language summary
- Store WeeklySummary

**GET /api/v1/reports/materials/[sessionId]**
- Aggregate ChatImageLogs for session
- Group by materialId + pageNumber
- Return most referenced materials and pages

---

## Redis — Conversation Cache Structure
```javascript
Key:    "conversation:{studentId}:{sessionId}"
Value:  {
  recentMessages: [...],   // last 5-6 messages only
  summary: "...",          // running summary
  phase: "before",
  language: "th"
}
Expiry: 24 hours
Summary trigger: every 6 messages → summarize → update Redis + save to DB
```

---

## Proxy Route Protection
```typescript
const teacherOnlyRoutes = [
  "/api/v1/subjects",
  "/api/v1/sessions",
  "/api/v1/reports/trigger",
  "/api/v1/reports/session",
  "/api/v1/reports/weekly",
  "/api/v1/reports/materials"
]

const studentOnlyRoutes = [
  "/api/v1/chat",
  "/api/v1/quiz"
]
```

---

## Important Notes
- **Mock AI responses active** in `src/lib/ai.ts` — uncomment real calls on integration day
- **MaterialChunks NOT in PostgreSQL** — lives in Qdrant, linked via `materialId` in payload
- **Session criteria + correctConcept never sent to frontend** — backend only
- **File storage is local** `/uploads` — swap to cloud later, no schema change needed
- **Rate limiting needed on `/api/v1/chat`** — use Upstash Redis or ioredis counter
- **Report generation is manual trigger** — no Cron Job needed for demo
- **Confidence threshold is 0.7** — below this triggers external API fallback
- **Thai + English supported** — AI auto detects language from student message
- **One conversation per student per phase per session** — BEFORE DURING AFTER separate

---
