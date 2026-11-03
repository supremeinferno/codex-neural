# 5. API Reference

Base URL: `http://127.0.0.1:8000` locally. FastAPI also serves interactive docs at `/docs` (Swagger UI) where you can try every endpoint.

## Conventions

- Request and response bodies are JSON unless noted.
- **Protected** routes need the header `Authorization: Bearer <token>`. The token comes from `/api/login`.
- Auth routes return `{"success": true|false, "message": "..."}` with HTTP 200 even when the action fails. Check `success`.
- Other routes use HTTP status codes for errors and return `{"detail": "..."}`.

| Status | Meaning |
| --- | --- |
| 400 | Bad input (for example, an invalid chat type) |
| 401 | Missing, expired or revoked token: "Please sign in again." |
| 403 | Signed in but not the admin |
| 404 | Not found, or it belongs to another user |
| 422 | Body did not match the expected fields (FastAPI validation) |
| 500 | Research pipeline failure (message trimmed to 300 characters) |

---

## Health

### `GET /api` — public
`{"message": "Nexus Research API is running"}`

### `GET /api/health` — public
```json
{"status": "healthy", "database": "users.db", "timestamp": "2026-11-03 10:00:00"}
```

---

## Authentication

### `POST /api/register` — public
```json
{"email": "student@example.com", "password": "secret123"}
```
→ `{"success": true, "message": "Account created successfully."}`

Failures: missing fields, password shorter than 6 characters, email already registered.

### `POST /api/login` — public
```json
{"email": "student@example.com", "password": "secret123"}
```
→
```json
{
  "success": true,
  "message": "Login successful",
  "user": {"id": 3, "email": "student@example.com"},
  "token": "q9X...random...Zk"
}
```
Failure: `{"success": false, "message": "Invalid email or password."}`

### `GET /api/session` — protected
→ `{"user": {"id": 3, "email": "student@example.com"}}` or 401.

### `POST /api/logout` — send the token
Revokes the session. Always returns `{"success": true}`.

### `POST /api/forgot-password` — public
`{"email": "student@example.com"}` → `{"success": true, "message": "OTP sent successfully."}`

### `POST /api/verify-otp` — public
`{"email": "...", "otp": "482913"}` → `{"success": true, "message": "OTP verified successfully."}`

Failures: "No OTP request found.", "OTP has expired.", "Invalid OTP."

### `POST /api/reset-password` — public
`{"email": "...", "otp": "482913", "new_password": "newsecret"}` → `{"success": true, "message": "Password reset successfully."}`

---

## Research

### `POST /api/research` — protected
```json
{"topic": "Microplastics and human health"}
```
→
```json
{
  "search_results": "- Title ... URL ... facts ...",
  "scraped_content": "Plain text of the first source ...",
  "report": "# 1. Introduction\n...\n# Sources\n- [Title](https://...)",
  "feedback": "Critic temporarily skipped because Mistral rate limit was reached."
}
```
The frontend shows `report`. This call can take a minute or more.

---

## PDF (Individual mode)

### `POST /api/individual/upload` — protected, `multipart/form-data`
Field name: `file`.

```bash
curl -X POST http://127.0.0.1:8000/api/individual/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@paper.pdf"
```
→
```json
{
  "success": true,
  "message": "PDF indexed successfully.",
  "document_id": "aa320bdf998f",
  "document_name": "paper.pdf",
  "pages": 12,
  "chunks": 18
}
```
Other messages: "PDF is already indexed.", "Only PDF files are allowed.", "PDF is too large. The limit is 25 MB.", "No readable text was found in the PDF." (for scanned images), or a rate-limit message.

### `POST /api/individual/chat` — protected
```json
{"question": "What dataset did they use?", "document_id": "aa320bdf998f"}
```
→
```json
{
  "success": true,
  "answer": "The authors used ... (page 4).",
  "sources": [{"page": 4, "section": "3. Methodology"}, {"page": 5, "section": "3. Methodology"}]
}
```
Summary questions ("summarize this") return `"sources": []`. Returns 404 if the user did not upload this document.

### `GET /api/individual/{document_id}/file?download=false` — protected
Returns the PDF. `download=true` sets `Content-Disposition: attachment`. The ID must be 12 lowercase hex characters (else 400) and owned by the user (else 404).

---

## Chat history

All protected. Users only ever see their own chats.

| Method and path | Body | Response |
| --- | --- | --- |
| `GET /api/conversations?kind=research\|pdf` | — | `{"conversations": [{id, title, kind, document_id, created_at, updated_at}]}` newest first. `kind` is optional. |
| `POST /api/conversations` | `{"title": "New chat", "kind": "research"}` or `{"kind": "pdf", "document_id": "..."}` | `{id, title, kind, document_id}` |
| `GET /api/conversations/{id}` | — | Chat fields plus `messages: [{id, role, content, sources, created_at}]`, and `document: {document_name, pages}` for PDF chats |
| `PATCH /api/conversations/{id}` | `{"title": "New name"}` | `{"success": true, "title": "New name"}` |
| `DELETE /api/conversations/{id}` | — | `{"success": true}` (messages are deleted too) |
| `POST /api/conversations/{id}/messages` | `{"role": "user"\|"assistant", "content": "...", "sources": []}` | `{"success": true}` |

Titles are cut to 200 characters. The first user message renames a "New chat".

---

## Admin

All require the admin's token (else 401 or 403).

| Method and path | Response |
| --- | --- |
| `GET /api/admin/dashboard` | `{success, total_users, total_logins, users: [{id, email, created_at}], recent_logins: [{id, user_id, email, login_time}]}` (last 100 logins) |
| `DELETE /api/admin/users/{user_id}` | Deletes the user and their login records. 403 for the admin account, 404 if not found. |
| `DELETE /api/admin/logins/{activity_id}` | Deletes one login record. 404 if not found. |
| `DELETE /api/admin/logins` | Deletes all login records. Returns `deleted` count. |

Next: [06-database.md](06-database.md)
