
### Get current profile

```text
Method: GET
URL: http://localhost:3000/api/v1/users/me
Headers:
  Authorization: Bearer {{studentToken}}

Body: None

Expected: 200 OK
```

### Update current profile

```text
Method: PATCH
URL: http://localhost:3000/api/v1/users/me
Headers:
  Authorization: Bearer {{studentToken}}
  Content-Type: application/json

Body:
{
  "name": "Somchai Updated",
  "language": "th"
}

Expected: 200 OK
```

Then call `GET /api/v1/users/me` again and confirm the updated name/language appear. You can use either a student or teacher token.