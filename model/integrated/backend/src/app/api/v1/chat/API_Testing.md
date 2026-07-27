### Send chat message

```text
Method: POST
URL: http://localhost:3000/api/v1/chat
Headers:
  Authorization: Bearer {{studentToken}}
  Content-Type: application/json

Body:
{
  "sessionId": "{{activeSessionId}}",
  "message": "What is the difference between an IAM Role and an IAM Policy?"
}

Expected: 200 OK
```

### Get chat history

```text
Method: GET
URL: http://localhost:3000/api/v1/chat/history/{{activeSessionId}}
Headers:
  Authorization: Bearer {{studentToken}}

Body: None

Expected: 200 OK
```

### Upload an image or PDF in chat

```text
Method: POST
URL: http://localhost:3000/api/v1/chat/upload
Headers:
  Authorization: Bearer {{studentToken}}

Body: form-data
  sessionId: {{activeSessionId}}     (Text)
  message: What does this diagram mean?  (Text)
  file: [select an image or PDF]     (File)

Expected: 201 Created
```

Do not add `Content-Type` manually for this request—Postman creates the correct multipart boundary.

### Create an internal image log

```text
Method: POST
URL: http://localhost:3000/api/v1/chat/image-log
Headers:
  Authorization: Bearer {{studentToken}}
  x-internal-api-secret: {{internalApiSecret}}
  Content-Type: application/json

Body:
{
  "studentId": "{{studentId}}",
  "sessionId": "{{activeSessionId}}",
  "messageId": "{{messageId}}",
  "imageUrl": "/uploads/chat/{{activeSessionId}}/{{studentId}}/example.png",
  "materialId": null,
  "pageNumber": null
}

Expected: 201 Created
```

For all Chat tests, `{{activeSessionId}}` must reference a session whose status is `ACTIVE`.