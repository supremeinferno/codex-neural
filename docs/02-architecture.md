# 2. Architecture

## The big picture

CODEX has three parts: a React app in the browser, a FastAPI server, and outside services the server calls.

```
┌──────────────────────────── Browser ─────────────────────────────┐
│  React app (frontend/)                                           │
│  Login · Register · Forgot password · Research · PDF · History   │
│  · Admin dashboard                                               │
└──────────────────────────────┬───────────────────────────────────┘
                               │  HTTPS + JSON
                               │  Authorization: Bearer <token>
┌──────────────────────────────▼───────────────────────────────────┐
│  FastAPI server (backend/main.py)                                │
│                                                                  │
│   auth.py ─────────► SQLite (users.db)                           │
│   pipeline.py ─┬───► agents.py ──► Groq LLM                      │
│                └───► tools.py ───► Tavily search, web pages      │
│   individual.py ───► PyMuPDF, Mistral embeddings,                │
│                      Chroma (backend/individual_chroma/), Groq   │
└──────────────────────────────────────────────────────────────────┘
                               │
              Gmail SMTP (password reset emails)
```

### Design principles

- **The frontend never talks to AI services directly.** API keys stay on the server, in `.env`.
- **The backend decides who you are.** Every protected route reads the session token and looks up the user. The frontend's idea of "logged in" or "admin" only controls what is shown.
- **Each backend file has one job.** `main.py` handles HTTP, `auth.py` handles accounts, `pipeline.py` runs research, `individual.py` handles PDFs.

## Flow 1: Signing in

```
User types email + password
        │
        ▼
login.jsx ── POST /api/login ──► main.login()
                                    │
                                    ├─ auth.authenticate_user()
                                    │     ├─ find user by email
                                    │     ├─ verify_password() (PBKDF2 or legacy SHA-256)
                                    │     └─ if legacy hash → re-hash with PBKDF2 and save
                                    ├─ insert a row into login_activity
                                    └─ auth.create_session() → random token
                                          (only its SHA-256 hash is stored)
        ◄──── { success, user: {id, email}, token } ─────┘
        │
App.jsx stores user + token in sessionStorage
        │
Every later request sends  Authorization: Bearer <token>
```

When the app reloads, `App.jsx` calls `GET /api/session`. If the token has expired or been revoked, the user is signed out.

## Flow 2: A research request

```
User enters a topic and presses Run
        │
        ▼
App.jsx
  ├─ POST /api/conversations            (create a chat, kind = "research")
  ├─ POST /api/conversations/{id}/messages   (save the user's topic)
  ├─ POST /api/research  { topic }      ──────────────┐
  │     (3-minute timeout via AbortController)        │
  │                                                   ▼
  │                               pipeline.run_research_pipeline(topic)
  │                                 STEP 1  Search agent (LangChain + Groq)
  │                                         calls tavily_search 1–3 times
  │                                         returns 4–6 sources with URLs
  │                                 STEP 2  Take the first URL from step 1
  │                                         scrape_webpage → clean text (≤ 6000 chars)
  │                                 STEP 3  writer_chain (prompt → Groq → text)
  │                                         builds the Markdown report
  │                                 STEP 4  Critic — currently skipped
  │                                         returns { search_results, scraped_content,
  │                                                   report, feedback }
  ├─ show state.report with react-markdown
  └─ POST /api/conversations/{id}/messages   (save the report as the assistant reply)
```

While waiting, the UI animates four stages (Research → Read → Write → Critique) on a timer. The animation is cosmetic; the backend does not stream progress.

## Flow 3: Uploading a PDF

```
Individual.jsx ── POST /api/individual/upload (multipart file) ──► main.upload_individual_pdf()
                                                                      │
   check: name ends in .pdf, size ≤ 25 MB                             │
                                                                      ▼
                                           individual.build_individual_index(bytes, name)
                                             1. document_id = first 12 hex chars of MD5(file)
                                             2. save file as individual_chroma/<id>.pdf
                                             3. PyMuPDF: one Document per page, with
                                                page number and detected section heading
                                             4. split into 3000-char chunks (200 overlap)
                                             5. if Chroma already has this id → done
                                             6. embed chunks with Mistral, store in Chroma
                                                (retry on rate limit, clean up on failure)
                                                                      │
   main.py records (document_id, user_id) in user_documents  ◄────────┘
   so only this user can open or chat with the PDF
```

Because the ID comes from the file's content, uploading the same PDF twice does not index it twice.

## Flow 4: Asking a question about a PDF

```
Individual.jsx ── POST /api/individual/chat { question, document_id }
                        │
main.py: does this user own document_id?  (no → 404)
                        │
individual.answer_individual_question()
   │
   ├─ Is it a summary request? ("summarize", "overview of", "what is this paper about", ...)
   │     YES → load ALL chunks for the document, sort by page,
   │           sample evenly down to 30,000 characters, ask Groq for a structured summary
   │
   └─ NO  → MMR retrieval: fetch 10 similar chunks, keep 5 diverse ones
            → prompt Groq: "answer ONLY from this context, mention page numbers"
            → return { answer, sources: [{page, section}, ...] }
```

Rate-limit errors (HTTP 429) are retried a few times, then turned into a friendly message instead of a server error.

## Flow 5: Password reset

```
Step 1  POST /api/forgot-password { email }
        → account exists? → generate 6-digit OTP (secrets module)
        → store OTP with 5-minute expiry → email it via Gmail SMTP
        → if email fails, delete the OTP
Step 2  POST /api/verify-otp { email, otp }
        → expired? wrong? (5 wrong tries deletes the OTP)
Step 3  POST /api/reset-password { email, otp, new_password }
        → verify OTP again → save new PBKDF2 hash → delete OTP
```

`Forgotpassword.jsx` shows these as three screens (`step` = 1, 2, 3).

## Flow 6: Admin dashboard

```
Dashboard.jsx ── GET /api/admin/dashboard (Bearer token)
                        │
main.require_admin(): session user's email == ADMIN_EMAIL ?  (no → 403)
                        │
returns total_users, total_logins, users[], recent_logins[] (last 100)
```

The admin can also delete a user (and that user's login records), delete one login record, or clear all login history. The admin account itself cannot be deleted.

## Folder layout

```
software-eng/
├── backend/
│   ├── main.py          HTTP routes, request models, database setup for chats/admin
│   ├── auth.py          users, password hashing, sessions, OTP email
│   ├── pipeline.py      research pipeline (search → scrape → write)
│   ├── agents.py        LLM, agents and prompt templates
│   ├── tools.py         tavily_search and scrape_webpage tools
│   ├── individual.py    PDF indexing, retrieval, summaries
│   ├── api/index.py     placeholder for a Vercel Python entry point (empty)
│   ├── vercel.json      Vercel routing for a combined deploy
│   ├── requirements.txt Python dependencies
│   └── users.db         SQLite database (tracked in git)
├── frontend/
│   ├── index.html
│   ├── package.json
│   └── src/             React components and CSS (see 04-frontend.md)
├── docs/                this documentation
├── diagrams/            UML diagrams
├── report/              project reports (PDF)
└── journals/            developer journals and reflections
```

Next: [03-backend.md](03-backend.md)
