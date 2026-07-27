
# API Testing Guide

## Base URL

```
http://localhost:3000

```

## Before You Start
Download Postman at https://www.postman.com/downloads/

---

## Auth Routes

### 1. Register Teacher

**Method:** `POST`  
**URL:** `http://localhost:3000/api/v1/auth/register`  
**Body → raw → JSON:**
```json
{
  "name": "Professor Somchai",
  "email": "teacher@university.ac.th",
  "password": "password123",
  "role": "TEACHER",
  "language": "th"
}
```
**Expected:** `201 Created`

---

### 2. Register Student

**Method:** `POST`  
**URL:** `http://localhost:3000/api/v1/auth/register`  
**Body → raw → JSON:**
```json
{
  "name": "Somchai Jaidee",
  "email": "student@university.ac.th",
  "password": "password123",
  "role": "STUDENT",
  "language": "th"
}
```
**Expected:** `201 Created`

---

### 3. Login

**Method:** `POST`  
**URL:** `http://localhost:3000/api/v1/auth/login`  
**Body → raw → JSON:**
```json
{
  "email": "teacher@university.ac.th",
  "password": "password123"
}
```
**Expected:** `200 OK` + token in response

> ⚠️ Important — copy the token from the response, you will need it later

---

### 4. Get Current Session

**Method:** `GET`  
**URL:** `http://localhost:3000/api/v1/auth/session`  
**Expected:** `200 OK` + current logged in user data

---

### 5. Logout

**Method:** `POST`  
**URL:** `http://localhost:3000/api/v1/auth/logout`  
**Expected:** `200 OK`

---

## How To Use Bearer Token

Bearer Token is how you tell the API who you are without logging in every time. Useful when testing multiple accounts at the same time.

### Step by Step

**Step 1 — Login and copy token**

Call the login route and look for token in the response:

```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": { ... }
}
```

Copy the entire token value (the long string)

---

**Step 2 — Create a new request**

**Method:** `GET`  
**URL:** `http://localhost:3000/api/v1/auth/session`

---

**Step 3 — Add token to Headers tab**

Click the **Headers** tab then add:

| Key | Value |
|---|---|
| Authorization | Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... |

> ⚠️ Always put a space between `Bearer` and the token

---

**Step 4 — Click Send**

Expected response:
```json
{
  "user": {
    "name": "Professor Somchai",
    "role": "TEACHER"
  }
}
```

---

**Want to test a different account?**

Login with that account → copy the new token → paste it in the Authorization header to replace the old one

---

## Error Cases To Test

| Test | Expected Result |
|---|---|
| Register with duplicate email | `409 Email already exists` |
| Login with wrong password | `401 Invalid credentials` |
| Send request without token | `401 Not authenticated` |
| Send request with missing fields | `400 Missing required fields` |
```

---

Save this as `API_TESTING.md` in your backend folder. Ready for Day 3?