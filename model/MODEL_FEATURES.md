# Model Features

## Gemini Vision Setup

External multimodal mode now uses the native Gemini `generateContent` API for PNG, JPEG, and rendered PDF page images.

PowerShell setup:

```powershell
$env:GEMINI_API_KEY = "..."
$env:GEMINI_VISION_MODEL = "gemini-3.6-flash"
$env:MATERIAL_MULTIMODAL_AGENT = "external"
```

Do not store a real API key in `.env.example` or source control.

## Environment Variables

```text
GEMINI_API_KEY=
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_VISION_MODEL=gemini-3.6-flash
GEMINI_VISION_TIMEOUT_SECONDS=90
GEMINI_VISION_MAX_RETRIES=3
GEMINI_VISION_TEMPERATURE=0.1
GEMINI_VISION_MAX_OUTPUT_TOKENS=8192
MATERIAL_MULTIMODAL_AGENT=external
CHAT_ATTACHMENT_MULTIMODAL_AGENT=external
```

`MATERIAL_MULTIMODAL_AGENT` modes:

- `none`: no external vision provider.
- `demo`: deterministic offline demo agent for tests and local development.
- `external`: real Gemini Vision provider.
- `gemini`: alias for `external`.

External mode fails fast when `GEMINI_API_KEY` or model configuration is missing.

## Supported Types

- `image/png`
- `image/jpeg`
- PDF pages rendered to PNG through the existing PyMuPDF ingestion path

PDF files are not sent whole to Gemini. The pipeline extracts the PDF text layer, renders visual pages as PNG, sends required rendered pages to Gemini, fuses text and visual evidence, verifies the result, and exports Verified KB records.

## Processing Flow

Material flow:

```text
PDF/Image upload
-> ingestion
-> page rendering when needed
-> Gemini Vision request
-> structured JSON response
-> multimodal verification
-> Verified KB export
-> CourseKnowledgeStore activation
-> RAG answer with citations
```

Attachment flow:

```text
Student PNG/JPEG/PDF attachment
-> temporary material rendering
-> multimodal analysis when an agent is supplied
-> verifier remains authoritative
-> temporary Verified KB
-> ConversationKnowledgeStore activation
-> RAG answer scoped to the same student_id and conversation_id
```

Course material and conversation attachment knowledge stores remain isolated.

Set `CHAT_ATTACHMENT_MULTIMODAL_AGENT=external` to use Gemini Vision for student attachment processing through the attachment API. When it is unset, attachment routes keep the existing local fallback behavior for offline development.

## Failure Statuses

- Invalid upload content type: `415`
- Invalid input: `400`
- Material or attachment not found: `404`
- Gemini authentication/configuration failure: startup failure or `500`
- Gemini rate limit/provider unavailable: `502` or `503`
- Malformed Gemini JSON: `502`
- Verification failure: records are not activated as verified KB

Provider errors are sanitized and must not include API keys, authorization headers, image base64, or full raw provider responses.

## Swagger Smoke Tests

Start the server in external Gemini mode:

```powershell
$env:GEMINI_API_KEY = "..."
$env:GEMINI_VISION_MODEL = "gemini-3.6-flash"
$env:MATERIAL_MULTIMODAL_AGENT = "external"
python -m uvicorn src.service.main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

## API Smoke Commands

Upload a PNG material:

```powershell
$upload = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/v1/materials/upload" `
  -Form @{ file = Get-Item ".\sample.png" }
```

Process the material:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/v1/materials/$($upload.material_id)/process"
```

Check status:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/v1/materials/$($upload.material_id)/status"
```

Upload and ask with `/v1/chat/with-attachment`:

```powershell
$request = @{
  student_id = "student-1"
  course_id = "course-1"
  class_session_id = "session-1"
  phase = "during_class"
  question = "What does this attachment show?"
  conversation_id = "conversation-1"
} | ConvertTo-Json -Compress

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/v1/chat/with-attachment" `
  -Form @{
    request_json = $request
    course_relevance_score = "0.9"
    unsafe = "false"
    file = Get-Item ".\sample.png"
  }
```

Verify:

- `attachment.processing_status` is `ready`
- `chat.scope` is `in_material`
- `chat.citations` is non-empty when the runtime RAG answer agent is configured
- each citation `material_id` matches the uploaded attachment material

Isolation check:

```powershell
$otherRequest = @{
  student_id = "student-1"
  course_id = "course-1"
  class_session_id = "session-1"
  phase = "during_class"
  question = "Can I use the previous attachment?"
  conversation_id = "conversation-2"
} | ConvertTo-Json -Compress
```

Run the same chat query in `conversation-2` and confirm citations from `conversation-1` are not returned.
