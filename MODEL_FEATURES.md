# Learning Companion Model — Teacher Assessment & Session Reports

## New teacher-facing model capabilities

### Rubric creation

- `POST /v1/rubrics` accepts a structured rubric.
- `POST /v1/rubrics/upload` accepts PDF, DOCX, XLSX, TXT, MD, or CSV up to 25 MB.
- When the configured LLM is available, the model converts the uploaded document into structured criteria and performance levels.
- Without an LLM, the service produces a deterministic draft rubric that an instructor can review.

### Rubric assessment

- `POST /v1/rubrics/{rubric_id}/evaluate`
- Evaluates a student submission against every criterion.
- Returns criterion scores, evidence, feedback, strengths, improvements, and a weighted percentage.
- The LLM is constrained to the uploaded rubric and cannot add criteria.

### End-of-session reports

- Every `/v1/chat` response is recorded as a model analytics event.
- Rubric evaluations are recorded in the same course/session stream.
- `POST /v1/session-reports/{course_id}/{class_session_id}/generate` creates a report.
- `GET /v1/session-reports/{course_id}/{class_session_id}` returns the latest report.

The report includes:

- Total interactions and unique students
- Average answer confidence
- Readiness percentage
- On-track, needs-review, and at-risk counts
- Common learning issues from `learning_signals`
- Suggested focus for the next session
- Rubric evaluation count and average score

## Example: upload rubric

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/v1/rubrics/upload" `
  -Method Post `
  -Form @{
    course_id = "CS332"
    class_session_id = "week-02"
    title = "S3 scenario rubric"
    file = Get-Item ".\rubric.pdf"
  }
```

## Example: evaluate

```json
POST /v1/rubrics/{rubric_id}/evaluate
{
  "student_id": "student-001",
  "submission_text": "The student's answer or work",
  "evidence": ["Optional teacher or system evidence"]
}
```

## Environment

Rubric extraction and evaluation reuse the same OpenAI-compatible LLM settings as RAG:

- `MODEL_RUNTIME_MODE=verified_kb`
- `LOCAL_LLM_BASE_URL`
- `LOCAL_LLM_API_KEY`
- `LOCAL_LLM_MODEL`
