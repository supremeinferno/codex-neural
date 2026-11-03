# 3. Backend

The backend is a Python package in `backend/`. Run it from the project root (`uvicorn backend.main:app`) because files import each other as `backend.<module>`.

## `main.py` — the web server

This is the FastAPI app. It defines every URL the frontend calls.

### Setup done at import time

| Item | What it does |
| --- | --- |
| `DB_PATH` | Path to the SQLite file. Defaults to `backend/users.db`; override with `CODEX_DATABASE_PATH`. |
| `ADMIN_EMAIL` | The one admin account: `codexproject9@gmail.com`. |
| `MAX_PDF_BYTES` | Upload limit, 25 MB. |
| CORS middleware | Allows requests from any origin so the Vercel frontend can call the Render backend. |
| `initialize_admin_database()` | Creates the `conversations`, `conversation_messages`, `user_documents` and `login_activity` tables if missing, and adds a `created_at` column to old `users` tables. Never deletes data. |

### Request models (Pydantic)

FastAPI checks every JSON body against these classes and returns `422` if a field is missing or the wrong type.

| Model | Fields |
| --- | --- |
| `AuthRequest` | `email`, `password` |
| `ForgotPasswordRequest` | `email` |
| `VerifyOTPRequest` | `email`, `otp` |
| `ResetPasswordRequest` | `email`, `otp`, `new_password` |
| `ResearchRequest` | `topic` |
| `IndividualQuestionRequest` | `question`, `document_id` |
| `ConversationRequest` | `title` (default "New chat"), `kind` ("research" or "pdf"), `document_id` |
| `ConversationRenameRequest` | `title` |
| `MessageRequest` | `role` ("user" or "assistant"), `content`, `sources` (list) |

### Dependencies (access control)

| Function | Used by | What it does |
| --- | --- | --- |
| `require_user` | All chat, research, PDF and admin routes | Reads `Authorization: Bearer <token>`, looks up the session, returns `{id, email}` or raises `401`. |
| `require_admin` | Admin routes | Runs `require_user`, then raises `403` unless the email equals `ADMIN_EMAIL`. |
| `_owned_conversation` | Chat routes | Returns the conversation only if it belongs to the current user. |

### Routes

See [05-api-reference.md](05-api-reference.md) for full details. In short:

- **Auth:** `register`, `login`, `logout`, `session_info`, `forgot_password`, `verify_otp_endpoint`, `reset_password_endpoint`
- **Chats:** `list_conversations`, `create_conversation`, `get_conversation`, `rename_conversation`, `delete_conversation`, `save_message`
- **Research:** `research` — calls `run_research_pipeline` and turns rate-limit errors into a readable message
- **PDF:** `upload_individual_pdf`, `get_individual_pdf`, `individual_chat`
- **Admin:** `admin_dashboard`, `admin_delete_user`, `admin_delete_login`, `admin_clear_logins`
- **Health:** `health_check`

Notable behaviour:

- `save_message` renames a chat called "New chat" to the first 70 characters of the user's first message.
- `register` fills in `created_at` after `auth.register_user` creates the row.
- `login` records a row in `login_activity` before creating the session.

## `auth.py` — accounts, passwords, sessions, OTP

Loads `SMTP_EMAIL` and `SMTP_APP_PASSWORD` from the root `.env`, then runs `init_db()` to create the `users`, `auth_sessions` and `password_reset_otps` tables.

| Function | What it does |
| --- | --- |
| `hash_password(password, salt, iterations)` | PBKDF2-HMAC-SHA256 with a random 16-byte salt and 600,000 iterations. Returns `pbkdf2_sha256$<iterations>$<salt>$<hash>`. |
| `verify_password(password, stored)` | Recomputes the hash with the stored salt and compares in constant time. Falls back to plain SHA-256 for old accounts. |
| `needs_rehash(stored)` | True if the stored hash is not PBKDF2 with the current iteration count. |
| `register_user(email, password)` | Lowercases the email, checks the password is at least 6 characters, inserts the user. Returns `(success, message)`. |
| `authenticate_user(email, password)` | Returns `{id, email}` if the password is right, else `None`. Upgrades old hashes. |
| `create_session(user_id)` | Makes a 32-byte random token, stores its SHA-256 hash with a 7-day expiry, returns the raw token. |
| `get_user_for_session(token)` | Hashes the token and finds an unexpired session. Returns `{id, email}` or `None`. |
| `revoke_session(token)` | Deletes the session (sign out). |
| `generate_otp()` | Random 6-digit number using `secrets` (cryptographically secure). |
| `send_otp_email(email, otp)` | Sends the code through `smtp.gmail.com:587` with STARTTLS. |
| `request_password_reset(email)` | Replaces any old OTP, stores a new one for 5 minutes, emails it. Deletes the OTP if sending fails. |
| `verify_otp(email, otp)` | Checks existence, expiry and value. Counts wrong attempts and deletes the OTP after 5. |
| `reset_password(email, otp, new_password)` | Verifies the OTP, saves the new hash, deletes the OTP. |

## `pipeline.py` — the research pipeline

One public function: `run_research_pipeline(topic) -> dict`.

| Step | Code | Output stored in `state` |
| --- | --- | --- |
| 1. Search | `build_research_agent().invoke(...)` | `search_results` — the agent's list of 4–6 sources |
| 2. Scrape | Regex finds the first URL in step 1, then `scrape_webpage.invoke({"url": url})` | `scraped_content` — up to 6000 characters, or an error message |
| 3. Write | `writer_chain.invoke({"topic", "research"})` with both inputs cut to 6000 characters | `report` — the Markdown report |
| 4. Critic | Skipped; a placeholder message is stored | `feedback` |

Scraping is done directly instead of through a second agent. This saves one LLM call per request, which matters on Groq's free tier.

Run it alone with `python -m backend.pipeline`.

## `agents.py` — LLM, agents and prompts

| Name | Type | Purpose |
| --- | --- | --- |
| `llm` | `ChatGroq` | Model `openai/gpt-oss-120b`, temperature 0, up to 6 automatic retries on rate limits |
| `RESEARCH_AGENT_PROMPT` / `build_research_agent()` | Tool-calling agent with `tavily_search` | Runs 1–3 searches, prefers authoritative sources, must not invent URLs |
| `READER_AGENT_PROMPT` / `build_search_agent()` | Agent with `scrape_webpage` | **Not used by the pipeline** (scraping is done directly). Kept for a future multi-page reader. Note the function name says "search" but it builds the reader. |
| `writer_prompt` / `writer_chain` | Prompt → LLM → string | Writes a 1200–1800 word report with a fixed structure: Introduction, Key Findings, Deeper Analysis, Conclusion, Sources (max 5). Tells the model to ignore instructions found inside scraped text (prompt-injection defence). |
| `critic_prompt` / `critic_chain` | Prompt → LLM → string | Scores a report out of 10 with strengths and improvements. Defined but switched off. |

## `tools.py` — tools the agents can call

| Tool | What it does |
| --- | --- |
| `tavily_search(query)` | Calls Tavily for 5 results and returns `{title, url, snippet}` where the snippet is the first 100 words. |
| `scrape_webpage(url)` | Downloads the page (15 s timeout), removes `script`, `style`, `nav`, `header`, `footer`, `aside` and `form`, returns up to 6000 characters of text. Every kind of failure returns a readable message instead of crashing. |

The 6000-character cap keeps requests under Groq's tokens-per-minute limit (about 4 characters per token).

## `individual.py` — PDF analyzer

### Settings

| Constant | Value | Meaning |
| --- | --- | --- |
| `INDIVIDUAL_DB_PATH` | `backend/individual_chroma/` | Where PDFs and the Chroma database are saved |
| `COLLECTION_NAME` | `individual_documents` | One Chroma collection for all PDFs; each chunk is tagged with `document_id` |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Same model as research mode |
| `MAX_SUMMARY_CHARACTERS` | 30,000 | Most text sent to the model for a summary |

### Functions

| Function | What it does |
| --- | --- |
| `make_document_id(bytes)` | First 12 hex characters of the file's MD5. Same file → same ID. |
| `get_pdf_path(document_id)` | Validates the ID format (12 hex characters) and returns the file path, or `None`. |
| `looks_like_heading(text)` | Guesses whether a line is a section heading ("2.1 Methods", "Conclusion", ...). |
| `extract_pdf_documents(...)` | Reads each page with PyMuPDF and creates one LangChain `Document` per page with `page` and `section` metadata. |
| `chunk_documents(documents)` | Splits pages into chunks of 3000 characters with 200 characters of overlap, numbered `chunk_0`, `chunk_1`, ... |
| `build_individual_index(bytes, name)` | Saves the file, extracts, chunks, embeds and stores. Skips work if already indexed. Removes partial data if embedding fails. |
| `is_summary_question(question)` | True if the question contains phrases like "summarize", "overview of" or "what is this document about". |
| `generate_full_document_summary(...)` | Loads every chunk in page order. If the text is too long, keeps an evenly spaced sample so the conclusion is still included. Asks for an 8-part structured summary. |
| `answer_individual_question(question, id)` | Public entry point. Routes to summary or MMR retrieval (`k=5`, `fetch_k=10`, `lambda_mult=0.5`), then asks the LLM to answer only from the context. Converts rate-limit errors into a friendly message. |
| `is_rate_limit_error`, `run_with_retry`, `invoke_with_retry` | Detect HTTP 429 and retry up to 3 times, waiting 8 s, then 16 s. |

## Other files

| File | Purpose |
| --- | --- |
| `requirements.txt` | Python packages with version ranges |
| `vercel.json` | Routes `/api/*` to the backend service and everything else to the frontend, for a combined Vercel deploy |
| `api/index.py` | Empty placeholder for a Vercel Python entry point. The backend currently runs on Render instead. |
| `users.db` | SQLite database. Tracked in git so the team shares accounts. See [06-database.md](06-database.md). |

Next: [04-frontend.md](04-frontend.md)
