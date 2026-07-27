Quiz is implemented and passes lint, TypeScript, and route checks. It uses mock generation/scoring until the AI teammate provides the real quiz contract.

Methods ready for Postman testing:

- `POST /api/v1/quiz/generate` — implemented, not Postman-tested yet
- `POST /api/v1/quiz/submit` — implemented, not Postman-tested yet
- `GET /api/v1/quiz/history/[sessionId]` — implemented, not Postman-tested yet

Use an active session and student token.

```text
Method: POST
URL: http://localhost:3000/api/v1/quiz/generate
Headers:
  Authorization: Bearer {{studentToken}}
  Content-Type: application/json

Body:
{
  "sessionId": "{{activeSessionId}}",
  "phase": "BEFORE"
}

Expected: 200 OK
```

Copy `quizId` and every returned question `id`, then submit:

```text
Method: POST
URL: http://localhost:3000/api/v1/quiz/submit
Headers:
  Authorization: Bearer {{studentToken}}
  Content-Type: application/json

Body:
{
  "quizId": "{{quizId}}",
  "answers": [
    {
      "questionId": "{{questionId1}}",
      "answer": "My answer to the first question."
    }
  ]
}

Expected: 200 OK
```

Include one answer for every generated question.

```text
Method: GET
URL: http://localhost:3000/api/v1/quiz/history/{{activeSessionId}}
Headers:
  Authorization: Bearer {{studentToken}}

Body: None

Expected: 200 OK
```
