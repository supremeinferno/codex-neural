# 8. Setup, Deployment and Troubleshooting

## Run it locally

### What you need

| Tool | Version | Check with |
| --- | --- | --- |
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| Git | any | `git --version` |

You also need free accounts and API keys from:

| Service | Used for | Get a key |
| --- | --- | --- |
| Groq | The LLM (writing reports and answers) | https://console.groq.com |
| Tavily | Web search | https://tavily.com |
| Mistral | Embeddings for PDF search | https://console.mistral.ai |
| Gmail | Sending password-reset codes | Google Account → Security → 2-Step Verification → App passwords |

### Step 1: Get the code

```bash
git clone https://github.com/supremeinferno/codex-neural.git
cd codex-neural
```

### Step 2: Create `.env` in the project root

```env
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
MISTRAL_API_KEY=your_mistral_key
SMTP_EMAIL=you@gmail.com
SMTP_APP_PASSWORD=your_16_character_app_password

# Optional: put the SQLite file somewhere else
# CODEX_DATABASE_PATH=/absolute/path/to/users.db
```

Never commit this file. It is already in `.gitignore`.

| Variable | Read by | If missing |
| --- | --- | --- |
| `GROQ_API_KEY` | `agents.py`, `individual.py` | Research and PDF answers fail |
| `TAVILY_API_KEY` | `tools.py` | Search fails, so research fails |
| `MISTRAL_API_KEY` | `individual.py` (via `MistralAIEmbeddings`) | PDF upload and questions fail |
| `SMTP_EMAIL`, `SMTP_APP_PASSWORD` | `auth.py` | "Unable to send OTP" on forgot password |
| `CODEX_DATABASE_PATH` | `main.py`, `auth.py` | Uses `backend/users.db` |

### Step 3: Start the backend

From the project root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate          # Windows: backend\.venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Open http://127.0.0.1:8000/api/health. You should see `"status": "healthy"`. Open http://127.0.0.1:8000/docs to try the API in the browser.

### Step 4: Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. To point at a different backend, create `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Restart `npm run dev` after changing `.env`. Vite reads it only at start-up.

### Step 5: Try it

1. Register a new account and sign in.
2. Research tab: click a suggested topic and press Run. Wait up to a minute.
3. Individual tab: upload a text-based PDF and ask "summarize this".
4. Open the sidebar (menu button) to see saved chats.

To see the admin dashboard, register and sign in as `codexproject9@gmail.com`, or change `ADMIN_EMAIL` (see below).

## Changing the admin

`ADMIN_EMAIL` appears in three files. Change all three:

- `backend/main.py` (this one enforces access)
- `frontend/src/App.jsx` (shows the Dashboard tab)
- `frontend/src/Dashboard.jsx`

## Deployment

The setup we used:

| Part | Host | Settings |
| --- | --- | --- |
| Frontend | Vercel | Root directory `frontend`, framework Vite, env var `VITE_API_URL=https://<your-backend>` |
| Backend | Render (web service) | Build: `pip install -r backend/requirements.txt`. Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`. Add every `.env` variable in the dashboard. |

`backend/vercel.json` describes an alternative where Vercel hosts both parts and routes `/api/*` to the backend. `backend/api/index.py` is empty, so this route is not finished.

### Things to watch in production

- **Storage is temporary** on free tiers. Uploaded PDFs, the Chroma index and possibly `users.db` disappear on redeploy. Use a persistent disk and set `CODEX_DATABASE_PATH`.
- **Cold starts:** a sleeping free Render service can take 30–60 seconds to wake up. The first request may fail; try again.
- **Long requests:** research can take over a minute. The frontend waits 3 minutes. Some proxies cut connections sooner.
- **CORS** is open to all origins. Restrict it to the Vercel URL in production.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| "Unable to connect to the server" on login | Backend not running, or wrong `VITE_API_URL` | Start uvicorn; check `frontend/.env`; restart `npm run dev` |
| `ModuleNotFoundError: No module named 'backend'` | Uvicorn started from inside `backend/` | Run from the project root: `uvicorn backend.main:app` |
| "Please sign in again." | Token expired (7 days) or the database was replaced | Sign in again |
| "The AI provider's rate limit was hit" | Groq or Mistral free-tier limit | Wait a minute. Use shorter PDFs. |
| "No readable text was found in the PDF" | The PDF is scanned images | Use a PDF with selectable text (OCR is not supported) |
| "Unable to send OTP" | Missing or wrong Gmail app password | Check `SMTP_EMAIL` and `SMTP_APP_PASSWORD`; use an app password, not your normal password |
| Research report says sources were unavailable | The first URL blocked scraping or timed out | Normal for some sites; the report is written from search results |
| "This saved PDF is no longer available" | `individual_chroma/` was deleted or the server was redeployed | Upload the PDF again |
| Dashboard tab missing | Not signed in as `ADMIN_EMAIL` | Sign in as the admin |
| Teammate's accounts disappeared after a pull | Someone committed their own `users.db` | Coordinate before committing `users.db`, or stop tracking it |

Next: [09-project-history.md](09-project-history.md)
