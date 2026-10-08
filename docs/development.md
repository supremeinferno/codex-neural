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

Other scripts are `npm run build` and `npm run preview`. `frontend/package.json` declares React 19, Vite 7, React Markdown/GFM, Framer Motion, and XLSX; `package-lock.json` is present for reproducible npm installs. Vite normally serves the UI at `http://localhost:5173`.

Set the frontend API origin in `frontend/.env.local`:

```dotenv
VITE_API_URL=http://127.0.0.1:8001
```

The default in `frontend/src/config.js` is already `http://127.0.0.1:8001`.

## Backend Configuration

Backend settings are read in `backend/config.py`; its optional dotenv loader checks the repository-root `.env`. Most values have development defaults, so isolated tests do not require an `.env` file. Create a local `.env` only for the features you intend to exercise. Never commit credentials.

| Variable | Default | Used for |
| --- | --- | --- |
| `GROQ_API_KEY` | empty | Groq chat model used by the web research agents |
| `TAVILY_API_KEY` | empty | Tavily search tool |
| `MISTRAL_API_KEY` | empty | Mistral PDF embeddings/chat integrations; provider libraries may also read their standard environment variable directly |
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

Password reset requires both a real user account and working SMTP credentials. Research requires Groq and Tavily credentials. PDF indexing/chat requires Mistral credentials. Auth/security/repository unit tests use temporary local state and do not need these external services.

## Run the API

The intended local command is:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
```

FastAPI's interactive API docs are at `http://127.0.0.1:8001/docs` when the app starts successfully. The app initializes the SQLite database during lifespan startup; the database path is `backend/users.db`. Keep the frontend's `VITE_API_URL` aligned with the API host/port.

## Current Checkout Caveats

The API app imports successfully and its registered paths can be inspected in OpenAPI. The focused test suite exercises isolated route modules but does not boot the full ASGI lifespan or contact provider APIs. Live research/PDF calls therefore still require valid credentials and a runtime smoke test. SQLite persistence is also split only partially: `backend/repositories/sqlite_repository.py` owns schema initialization and admin access, while `backend/services/auth_service.py` retains its own `get_connection` and `init_db` implementation.
