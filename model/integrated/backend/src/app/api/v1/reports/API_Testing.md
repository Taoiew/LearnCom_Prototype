Methods ready to test:

- `POST /api/v1/reports/trigger/[sessionId]`
- `GET /api/v1/reports/session/[sessionId]`
- `GET /api/v1/reports/student/[studentId]`
- `POST /api/v1/reports/weekly/generate`
- `GET /api/v1/reports/weekly/[subjectId]`
- `GET /api/v1/reports/materials/[sessionId]`

Prerequisite: the session must be `COMPLETED` before triggering its report. Ideally, have at least one student submit a quiz first.

```text
Method: POST
URL: http://localhost:3000/api/v1/reports/trigger/{{completedSessionId}}
Headers:
  Authorization: Bearer {{teacherToken}}

Body: None

Expected: 200 OK
```

```text
Method: GET
URL: http://localhost:3000/api/v1/reports/session/{{completedSessionId}}
Headers:
  Authorization: Bearer {{teacherToken}}

Body: None

Expected: 200 OK
```

```text
Method: GET
URL: http://localhost:3000/api/v1/reports/student/{{studentId}}
Headers:
  Authorization: Bearer {{teacherToken}}

Body: None

Expected: 200 OK
```

A student can use the same endpoint only for their own ID:

```text
Authorization: Bearer {{studentToken}}
URL: http://localhost:3000/api/v1/reports/student/{{studentId}}
```

```text
Method: POST
URL: http://localhost:3000/api/v1/reports/weekly/generate
Headers:
  Authorization: Bearer {{teacherToken}}
  Content-Type: application/json

Body:
{
  "subjectId": "{{subjectId}}",
  "weekNumber": 3,
  "weekStart": "2026-07-20T00:00:00.000Z",
  "weekEnd": "2026-07-26T23:59:59.999Z"
}

Expected: 201 Created
```

```text
Method: GET
URL: http://localhost:3000/api/v1/reports/weekly/{{subjectId}}?weekNumber=3
Headers:
  Authorization: Bearer {{teacherToken}}

Body: None

Expected: 200 OK
```

```text
Method: GET
URL: http://localhost:3000/api/v1/reports/materials/{{completedSessionId}}
Headers:
  Authorization: Bearer {{teacherToken}}

Body: None

Expected: 200 OK
```

The materials report returns an empty `materials` array when no chat image upload has been matched to a course material yet.