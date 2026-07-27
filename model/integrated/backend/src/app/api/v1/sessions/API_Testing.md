
## Sessions

### Create Session
```
Method: POST
URL: http://localhost:3000/api/v1/sessions
Headers: Authorization: Bearer {{teacherToken}}
Body:
{
  "subjectId": "{{subjectId}}",
  "title": "Week 3 - EC2 and IAM",
  "description": "Understanding EC2 and IAM roles",
  "date": "2024-03-15T09:00:00.000Z"
}
Expected: 201 Created
```

### Get All Sessions
```
Method: GET
URL: http://localhost:3000/api/v1/sessions
Headers: Authorization: Bearer {{teacherToken}}
Expected: 200 OK
```

### Update Session Status
```
Method: PATCH
URL: http://localhost:3000/api/v1/sessions/{{sessionId}}/status
Headers: Authorization: Bearer {{teacherToken}}
Body:
{
  "status": "ACTIVE",
  "phase": "BEFORE"
}
Expected: 200 OK
```

---

### Add Session Criteria
```
Method: POST
URL: http://localhost:3000/api/v1/sessions/{{sessionId}}/criteria
Headers: Authorization: Bearer {{teacherToken}}
Body:
{
  "description": "Explain IAM Role vs Policy",
  "goal": "Student can clearly differentiate IAM Role and Policy",
  "order": 1,
  "semesterCriteriaId": "{{semesterCriteriaId}}"
}
Expected: 201 Created
```

---

### Upload Material
```
Method: POST
URL: http://localhost:3000/api/v1/sessions/{{sessionId}}/materials
Headers: Authorization: Bearer {{teacherToken}}
Body → form-data:
  key: file
  value: (select a PDF file)
Expected: 201 Created
```

---
