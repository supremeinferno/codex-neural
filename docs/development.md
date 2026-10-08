# Development Setup

## Requirements

- Python 3.11 or newer (`backend/pyproject.toml` specifies `>=3.11`).
- Node.js/npm for the Vite frontend.
- Internet access and provider credentials for live research and PDF AI features.
- Redis is optional in development; request limiting falls back to process memory if Redis is disabled, unavailable, or cannot connect.

## Python Environment and Tests

Run commands from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m pip install pytest
python -m pytest backend/tests -q
```

On Windows PowerShell, activate with `.venv\\Scripts\\Activate.ps1`.

`backend/requirements.txt` is the actual backend runtime dependency list. It includes FastAPI/Uvicorn, LangChain and LangGraph integrations, Tavily, Groq, Mistral, Google GenAI and xAI integrations, PDF/Chroma components, SQLite support from Python's standard library, Redis, and supporting HTTP/HTML libraries. `pytest` is not currently listed there. `backend/pyproject.toml` declares Python >=3.11 and pytest discovery settings, but its project dependency list is empty; do not use it alone to install the runtime.

## Frontend

```bash
cd frontend
npm ci
npm run dev
```

`frontend/package.json` declares React 19, Vite 7, React Markdown/GFM, Framer Motion, and XLSX; `package-lock.json` is present for reproducible npm installs. Vite normally serves the UI at `http://localhost:5173`. The current `build` script runs bare `vite` and starts the dev server; use `npx vite build` for a production bundle. `npm run preview` runs Vite's preview server against an existing bundle.

For local development, leave `VITE_API_URL` unset. The Vite server proxies same-origin `/api` requests to `http://127.0.0.1:8001`, which also keeps session cookies on the frontend origin. Set an API origin in `frontend/.env.local` only when using a separately hosted API:

```dotenv
VITE_API_URL=http://localhost:8001
```

`frontend/src/config.js` defaults to an empty API prefix, so requests use the current origin. The proxy is configured in `frontend/vite.config.js` and is used by the local Vite dev server.

## No-Credential Demo

The demo wires the same UI, authentication/session routes, permissions, admin views, and API route modules as the normal app. Only provider-facing research and PDF operations are replaced with deterministic placeholder services; Redis is disabled. It does not call Groq, Tavily, Mistral, SMTP, or Redis.

Start the API in one terminal from the repository root:

```bash
source .venv/bin/activate
uvicorn backend.demo:app --reload --host 127.0.0.1 --port 8001
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` and sign in with the seeded local admin `codexproject9@gmail.com` / `NexusDemo!2026`. Registration also works and creates ordinary users. Password reset still requires SMTP, and demo PDF answers are not grounded in the uploaded document; the upload is retained only so the PDF viewer can display the original file.

By default, demo state is isolated from `backend/users.db`: SQLite uses `/tmp/nexus-research-demo.sqlite3` and uploaded documents use `/tmp/nexus-research-demo-pdfs/`. Set `NEXUS_DEMO_DB_PATH` and `NEXUS_DEMO_DOCUMENTS_DIR` before launching to choose different locations. The account is seeded only in this demo database. Never expose this demo server publicly because its admin password is intentionally known.

The no-provider workflow is covered by `python -m pytest backend/tests/test_demo.py -q`.

## Backend Configuration

Backend settings are read in `backend/config.py`; its optional dotenv loader checks the repository-root `.env`. Most values have development defaults, so isolated tests do not require an `.env` file. Create a local `.env` only for the features you intend to exercise. Never commit credentials.

| Variable | Default | Used for |
| --- | --- | --- |
| `GROQ_API_KEY` | empty | Groq chat model used by the web research agents |
| `TAVILY_API_KEY` | empty | Tavily search tool |
| `MISTRAL_API_KEY` | empty | Mistral PDF embeddings; provider libraries may also read their standard environment variable directly |
| `SMTP_EMAIL` | `codexproject9@gmail.com` | Sender account for password-reset email |
| `SMTP_APP_PASSWORD` | empty | Gmail SMTP app password; needed to deliver OTP email |
| `SESSION_TTL_SECONDS` | `604800` | Server-side session lifetime (7 days) |
| `SESSION_COOKIE_SECURE` | `false` | Set the session cookie's Secure flag; enable behind HTTPS in production |
| `LOGIN_ATTEMPT_WINDOW_SECONDS` | `900` | In-memory failed-login tracking window |
| `MAX_LOGIN_ATTEMPTS` | `5` | Failed-login threshold per IP/email key |
| `ADMIN_EMAIL` | `codexproject9@gmail.com` | Configured admin email list; current authorization is based on the stored user role, not this value alone |
| `FRONTEND_ORIGINS` | `http://127.0.0.1:5173,http://localhost:5173` | Comma-separated CORS origins allowed by FastAPI |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Request limiter window |
| `RATE_LIMIT_MAX_REQUESTS` | `120` | Request limiter maximum per client/path/window |
| `RATE_LIMIT_ALGORITHM` | `sliding_window` | `sliding_window`, `fixed_window`, or `token_bucket` |
| `RATE_LIMIT_USE_REDIS` | `true` | Attempt Redis-backed request limiting when the redis package is available |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL; memory fallback is used when unavailable |

In normal mode, password reset requires both a real user account and working SMTP credentials. Research requires Groq and Tavily credentials. PDF indexing requires Mistral credentials for embeddings; PDF question answering also uses the Groq model. The local demo and unit/API-router tests use temporary local state or injected services and do not need these external services.

## Run the API

The intended local command is:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
```

FastAPI's interactive API docs are at `http://127.0.0.1:8001/docs` when the app starts successfully. The app initializes the SQLite database during lifespan startup; the database path is `backend/users.db`. Keep the frontend's `VITE_API_URL` aligned with the API host/port.

## Current Checkout Caveats

The focused suite imports the app and enters its ASGI lifespan with persistent database initialization stubbed; it also checks route registration. It does not contact provider APIs. Live research/PDF calls therefore still require valid credentials and a runtime smoke test. All production SQLite connections and queries are centralized in `backend/repositories/sqlite_repository.py`; services call semantic repository methods, and schema initialization runs in app lifespan rather than on service import.
