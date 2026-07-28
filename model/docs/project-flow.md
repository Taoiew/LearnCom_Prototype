# Learning Companion Project Flow

This document summarizes the main runtime flows in the current Learning Companion prototype.
The diagrams use Mermaid so they can be rendered directly in GitHub, VS Code, Notion, or Mermaid Live Editor.

## 1. System Overview

```mermaid
flowchart LR
  Teacher[Teacher UI] --> Frontend[Next.js Frontend]
  Student[Student UI] --> Frontend

  Frontend --> Backend[Next.js API Backend]
  Backend --> DB[(PostgreSQL via Prisma)]
  Backend --> Uploads[(Local uploads folder)]
  Backend --> ModelAPI[Python Model API]

  ModelAPI --> RAG[RAG / KB Retrieval]
  ModelAPI --> Gemini[Gemini Text / Vision]
  ModelAPI --> KB[(Verified KB files)]

  RAG --> KB
  Gemini --> ModelAPI
  ModelAPI --> Backend
  Backend --> Frontend
```

## 2. Teacher Course And Session Setup

```mermaid
sequenceDiagram
  actor Teacher
  participant FE as Frontend
  participant BE as Backend API
  participant DB as PostgreSQL

  Teacher->>FE: Log in as teacher
  FE->>BE: POST /api/v1/auth/login
  BE->>DB: Find teacher user
  DB-->>BE: User record
  BE-->>FE: JWT + user profile

  Teacher->>FE: Create course
  FE->>BE: POST /api/v1/subjects
  BE->>DB: Create Subject
  DB-->>BE: Subject
  BE-->>FE: Updated course list

  Teacher->>FE: Create session with date/start/end time
  FE->>BE: POST /api/v1/sessions
  BE->>DB: Create ClassSession + default criteria
  DB-->>BE: Session
  BE-->>FE: Updated dashboard
```

## 3. Material And Rubric Upload To KB

```mermaid
flowchart TD
  A[Teacher selects target session] --> B[Upload material or rubric files]
  B --> C[Frontend sends multipart upload]
  C --> D[Backend validates teacher access]
  D --> E[Store file in local uploads folder]
  D --> F[Create Material record]
  F --> G[Optional: call Python Model API]
  G --> H[PDF/image ingestion]
  H --> I[Gemini Vision or parser extracts page evidence]
  I --> J[Verification and grounding checks]
  J --> K[Verified KB artifacts]
  K --> L[Chat, quiz, summary, next-class preview can reference material]
```

## 4. Student Chat With RAG And References

```mermaid
sequenceDiagram
  actor Student
  participant FE as Student Session UI
  participant BE as Backend API
  participant DB as PostgreSQL
  participant Model as Python Model API
  participant KB as Verified KB
  participant Gemini as Gemini

  Student->>FE: Ask text question or attach image
  FE->>BE: POST /api/v1/chat or /api/v1/chat/upload
  BE->>DB: Upsert Conversation + save student Message

  alt Text-only question
    BE->>Model: Ask with session/material context
    Model->>KB: Retrieve relevant chunks/pages
    Model->>Gemini: Generate grounded answer
  else Image attachment
    BE->>DB: Save ChatImageLog
    BE->>Model: Send question + image
    Model->>Gemini: Vision analysis
    Model->>KB: Match image/page/material evidence
    Model->>Gemini: Generate answer
  end

  Model-->>BE: Answer + references + flagged criteria
  BE->>DB: Save agent Message + AnswerReference rows
  BE-->>FE: Answer, references table, status
  FE-->>Student: Render chat history in scrollable chat panel
```

## 5. Quiz Flow: Pre-class And After-class

```mermaid
flowchart TD
  A[Student opens quiz page] --> B{Quiz phase}

  B -->|Before class| C[Generate pre-class readiness quiz]
  B -->|After class| D[Generate after-class personalized quiz]

  C --> E[Use current or next session material KB]
  D --> F[Use session KB + rubric + student's weak criteria/chat history]

  E --> G[Backend creates Quiz + QuizQuestion]
  F --> G

  G --> H[Student answers in own words]
  H --> I[POST /api/v1/quiz/submit]
  I --> J[Score against SessionCriteria / rubric]
  J --> K[Create CriteriaResult rows]
  K --> L[Update Quiz totalScore and readiness]
  L --> M[Student sees score, result, feedback]
  M --> N[Teacher summary aggregates quiz overview]
```

## 6. Attendance Check-in Flow

```mermaid
sequenceDiagram
  actor Teacher
  actor Student
  participant FE as Frontend
  participant BE as Backend API
  participant DB as PostgreSQL
  participant FS as Local uploads

  Teacher->>FE: Create session with start/end time
  FE->>BE: POST /api/v1/sessions
  BE->>DB: Save ClassSession date + duration

  Student->>FE: Opens active session
  FE->>FE: Calculate student-specific attendance slot
  FE-->>Student: Show countdown until check-in opens

  Student->>FE: Upload check-in photo
  FE->>BE: POST /api/v1/attendance
  BE->>BE: Validate active session and image file
  BE->>FS: Store photo
  BE->>DB: Upsert Attendance(studentId, sessionId)
  DB-->>BE: Attendance row
  BE-->>FE: Checked-in status
  FE-->>Student: Show checked-in badge

  Teacher->>FE: Open session summary
  FE->>BE: GET /api/v1/sessions/:id/summary
  BE->>DB: Read Attendance rows
  BE-->>FE: Attendance list + photo URLs
```

## 7. Teacher Session Summary

```mermaid
flowchart TD
  A[Teacher opens session summary] --> B[GET /api/v1/sessions/:id/summary]

  B --> C[Read session metadata]
  B --> D[Read student messages]
  B --> E[Read chat image logs]
  B --> F[Read answer references]
  B --> G[Read attendance photos]
  B --> H[Read quizzes and criteria results]
  B --> I[Read next-class previews]

  D --> J[Question feed]
  E --> K[Chat image files]
  F --> L[Most asked topics + material references]
  G --> M[Attendance section]
  H --> N[Quiz overview section]
  I --> O[Next-class readiness loop]

  J --> P[Teacher summary page]
  K --> P
  L --> P
  M --> P
  N --> P
  O --> P
```

## 8. Next-Class Readiness Feedback Loop

```mermaid
sequenceDiagram
  actor Teacher
  actor Student
  participant FE as Frontend
  participant BE as Backend API
  participant DB as PostgreSQL
  participant Model as Python Model API / KB

  Teacher->>FE: Prepare next class from current session summary
  FE->>BE: POST /api/v1/next-class-previews
  BE->>DB: Find next session and next-session materials
  BE->>Model: Build preview content/questions from next class KB
  Model-->>BE: Preview + readiness questions + references
  BE->>DB: Save NextClassPreview + questions

  Teacher->>FE: Publish preview
  FE->>BE: POST /api/v1/next-class-previews/:previewId/publish
  BE->>DB: Mark preview as PUBLISHED

  Student->>FE: Open next/current student session
  FE->>BE: GET /api/v1/sessions/:id/next-class-preview
  BE->>DB: Load published preview for session
  BE-->>FE: Preview and questions
  FE-->>Student: Show next-class preview/readiness check

  Student->>FE: Answer readiness question
  FE->>BE: POST /api/v1/next-class-previews/:previewId/responses
  BE->>DB: Save response and correctness

  Teacher->>FE: Analyze readiness
  FE->>BE: POST /api/v1/next-class-previews/:previewId/analyze
  BE->>DB: Aggregate responses
  BE->>Model: Generate teaching recommendations
  Model-->>BE: Misconceptions + revision notes
  BE->>DB: Save NextClassFeedbackSummary + TeacherRevisionNote
  BE-->>FE: Summary for teacher
```

## 9. Data Ownership Map

```mermaid
erDiagram
  User ||--o{ Subject : teaches
  User ||--o{ Conversation : starts
  User ||--o{ Message : sends
  User ||--o{ Quiz : takes
  User ||--o{ Attendance : checks_in

  Subject ||--o{ ClassSession : contains
  Subject ||--o{ SemesterCriteria : defines

  ClassSession ||--o{ SessionCriteria : measures
  ClassSession ||--o{ Material : uses
  ClassSession ||--o{ Conversation : has
  ClassSession ||--o{ Quiz : has
  ClassSession ||--o{ Attendance : has
  ClassSession ||--o{ ChatImageLog : stores
  ClassSession ||--o{ AnswerReference : cites

  Conversation ||--o{ Message : contains
  Message ||--o{ AnswerReference : has

  Quiz ||--o{ QuizQuestion : contains
  Quiz ||--o{ CriteriaResult : produces
  SessionCriteria ||--o{ QuizQuestion : drives
  SessionCriteria ||--o{ CriteriaResult : evaluates

  NextClassPreview ||--o{ NextClassReadinessQuestion : includes
  NextClassPreview ||--o{ NextClassReadinessResponse : receives
  NextClassPreview ||--|| NextClassFeedbackSummary : analyzes
  NextClassFeedbackSummary ||--o{ TeacherRevisionNote : recommends
```

## 10. End-to-End Manual Test Path

```mermaid
flowchart TD
  A[Start with clean database] --> B[Teacher login]
  B --> C[Create course]
  C --> D[Create Session 1]
  D --> E[Create Session 2 with later date/time]
  E --> F[Upload materials/rubric to sessions]
  F --> G[Student login]
  G --> H[Open active session]
  H --> I[Chat text question]
  I --> J[Chat image question]
  J --> K[Wait for attendance countdown]
  K --> L[Upload attendance photo]
  L --> M[Take pre-class quiz]
  M --> N[Take after-class quiz]
  N --> O[Teacher opens session summary]
  O --> P[Check question feed, references, attendance, images, quiz overview]
  P --> Q[Teacher prepares next-class preview]
  Q --> R[Publish preview]
  R --> S[Student sees next-class readiness check]
  S --> T[Teacher analyzes responses and revision notes]
```
