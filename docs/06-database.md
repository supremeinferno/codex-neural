# 6. Data Storage

CODEX stores data in two places:

1. **SQLite** (`backend/users.db`) — accounts, sessions, chats, and admin data.
2. **Chroma + files** (`backend/individual_chroma/`) — uploaded PDFs and their embeddings.

## SQLite

One file, no server. Tables are created automatically when the backend starts: `auth.init_db()` creates the auth tables and `main.initialize_admin_database()` creates the rest. Neither function deletes existing data.

```
users ──1───*── auth_sessions
  │  └──1───*── login_activity
  │  └──1───*── conversations ──1───*── conversation_messages
  │  └──1───*── user_documents
  └─ (by email) password_reset_otps
```

There are no SQL foreign key constraints. The links above are enforced in code (for example, every chat query includes `user_id = ?`).

### `users`
| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PK | Auto-increment |
| `email` | TEXT UNIQUE | Stored in lowercase |
| `password` | TEXT | `pbkdf2_sha256$600000$<salt>$<hash>`, or a 64-character SHA-256 hex string for old accounts not yet upgraded |
| `created_at` | TEXT | `YYYY-MM-DD HH:MM:SS`. Added later, so old rows got the migration time. |

### `auth_sessions`
| Column | Type | Notes |
| --- | --- | --- |
| `token_hash` | TEXT PK | SHA-256 of the bearer token. The raw token is never stored. |
| `user_id` | INTEGER | Owner |
| `expires_at` | TEXT | UTC, 7 days after sign-in |

Expired rows are ignored but not cleaned up automatically.

### `password_reset_otps`
| Column | Type | Notes |
| --- | --- | --- |
| `email` | TEXT PK | One active code per email |
| `otp` | TEXT | 6 digits |
| `expires` | REAL | Unix timestamp, 5 minutes after the request |
| `attempts` | INTEGER | Wrong guesses; the row is deleted at 5 |

### `login_activity`
| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PK | |
| `user_id` | INTEGER | |
| `email` | TEXT | Copied so the record stays readable |
| `login_time` | TEXT | Local server time |

### `conversations`
| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PK | |
| `user_id` | INTEGER | Owner |
| `title` | TEXT | Max 200 characters |
| `kind` | TEXT | `research` or `pdf` (CHECK constraint) |
| `document_id` | TEXT | Set for PDF chats |
| `created_at`, `updated_at` | TEXT | List is sorted by `updated_at` |

### `conversation_messages`
| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PK | Gives message order |
| `conversation_id` | INTEGER | |
| `role` | TEXT | `user` or `assistant` (CHECK constraint) |
| `content` | TEXT | The question, report or answer (Markdown) |
| `sources` | TEXT | JSON list, such as `[{"page": 4, "section": "Methods"}]` |
| `created_at` | TEXT | |

### `user_documents`
| Column | Type | Notes |
| --- | --- | --- |
| `document_id` | TEXT | 12-character MD5 prefix |
| `user_id` | INTEGER | |
| `document_name` | TEXT | Original file name |
| `pages` | INTEGER | Pages with text |
| `created_at` | TEXT | |

Primary key is `(document_id, user_id)`. If two users upload the same file, they share one index but each gets their own ownership row.

### Inspecting the database

```bash
sqlite3 backend/users.db
.tables
.schema users
SELECT id, email, created_at FROM users;
.quit
```

## Chroma vector store

| Item | Value |
| --- | --- |
| Folder | `backend/individual_chroma/` (ignored by git) |
| Collection | `individual_documents` |
| Contents | `chroma.sqlite3` plus index files, and each uploaded PDF saved as `<document_id>.pdf` |
| Each entry | Chunk text, its Mistral embedding, and metadata: `document_id`, `document_name`, `page`, `section`, `content_type`, `chunk_id` |

Queries always filter by `document_id`, so one user's questions never pull text from another PDF.

To reset all PDF data, stop the backend and delete the `backend/individual_chroma/` folder. Old PDF chats will then say "This saved PDF is no longer available" when opened.

## Important notes

- `users.db` **is committed to git** so teammates share the same accounts. Committing it from your machine overwrites everyone's copy, and the file contains email addresses and password hashes. See [07-security.md](07-security.md).
- On hosts with temporary disks (such as Vercel or Render's free tier), both the SQLite file and the Chroma folder can be wiped on redeploy. Set `CODEX_DATABASE_PATH` to a persistent disk for production.

Next: [07-security.md](07-security.md)
