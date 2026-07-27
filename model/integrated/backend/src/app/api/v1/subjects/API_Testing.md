
## Subjects

### Create Subject
```
Method: POST
URL: http://localhost:3000/api/v1/subjects
Headers: Authorization: Bearer {{teacherToken}}
Body:
{
  "name": "CS332 Basic Cloud Computing",
  "description": "AWS fundamentals course"
}
Expected: 201 Created
```

### Get All Subjects
```
Method: GET
URL: http://localhost:3000/api/v1/subjects
Headers: Authorization: Bearer {{teacherToken}}
Expected: 200 OK
```

### Get Single Subject
```
Method: GET
URL: http://localhost:3000/api/v1/subjects/{{subjectId}}
Headers: Authorization: Bearer {{teacherToken}}
Expected: 200 OK
```

---

## Semester Criteria

### Create Semester Criteria
```
Method: POST
URL: http://localhost:3000/api/v1/subjects/{{subjectId}}/semester-criteria
Headers: Authorization: Bearer {{teacherToken}}
Body:
{
  "description": "Student can design secure AWS architecture",
  "goal": "Apply IAM, VPC, and S3 security best practices",
  "order": 1
}
Expected: 201 Created
```

---