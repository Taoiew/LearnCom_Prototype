Method: POST
URL: http://localhost:3000/api/v1/training/store
Headers:
  x-internal-api-secret: {{internalApiSecret}}
  Content-Type: application/json

Body:
{
  "question": "What is the difference between an IAM Role and an IAM Policy?",
  "answer": "An IAM Role is an identity that can be assumed, while a policy defines permissions.",
  "source": "gemini",
  "sessionId": "{{sessionId}}",
  "studentId": "{{studentId}}",
  "topic": "IAM"
}

Expected: 201 Created