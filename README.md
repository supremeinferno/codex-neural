# CODEX

CODEX is a multi-agent research assistant with a React front end and a FastAPI back end. It has two modes:

- **CODEX (Nexus research)** – enter any topic. A search agent finds sources, one source is scraped for detail, and a writer agent produces a structured, cited Markdown report.
- **Individual (PDF analyzer)** – upload a PDF, then ask questions about it or request a full summary. Answers come only from the document and mention page numbers.

Other features: user accounts with email OTP password reset, saved chat history (rename and delete) with a sliding sidebar, and an admin dashboard for managing users and login activity.

## How the research pipeline works

```
Topic ─► Search agent (Tavily) ─► Scrape top URL ─► Writer ─► Report
```

1. **Search** – an agent with the `tavily_search` tool collects the best sources.
2. **Scrape** – the first URL is fetched and cleaned with BeautifulSoup (capped at 6000 characters).
3. **Write** – the writer turns the search results and scraped text into a report: Introduction, Key Findings, Deeper Analysis, Conclusion, Sources.
4. **Critic** – defined in `backend/agents.py` but currently switched off in the pipeline.

PDF mode splits each page into chunks, embeds them with Mistral and stores them in a local Chroma database. Questions use MMR retrieval over the chunks, and summaries use text sampled evenly across the whole document.

## Tech stack

| Layer | Tools |
| --- | --- |
| Front end | React 19, Vite, react-markdown, remark-gfm |
| Back end | FastAPI, SQLite |
| LLM | Groq (`openai/gpt-oss-120b`) through LangChain |
| Embeddings and vector store | Mistral embeddings, Chroma |
| Web research | Tavily, requests, BeautifulSoup |
| PDF parsing | PyMuPDF |

## Project structure

```
backend/
  main.py        FastAPI app and all API routes
  auth.py        Login, sessions, password reset email
  pipeline.py    Research pipeline (search, scrape, write)
  agents.py      LLM, agent and prompt definitions
  tools.py       tavily_search and scrape_webpage tools
  individual.py  PDF indexing, retrieval and answering
  api/index.py   Vercel entry point
frontend/
  src/App.jsx              App shell, tabs, research page
  src/Individual.jsx       PDF analyzer
  src/NavigationDrawer.jsx Sidebar (new chat, recent chats, account)
  src/ChatHistory.jsx      Full history page
  src/Dashboard.jsx        Admin dashboard
diagrams/  Use case, class and activity diagrams
```

## Getting started

### Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- API keys for [Groq](https://console.groq.com), [Tavily](https://tavily.com) and [Mistral](https://console.mistral.ai)
- A Gmail address with an app password, used to send password reset codes

### 1. Environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
MISTRAL_API_KEY=your_mistral_key
SMTP_EMAIL=you@gmail.com
SMTP_APP_PASSWORD=your_gmail_app_password

# Optional: where the SQLite database is stored
# CODEX_DATABASE_PATH=/path/to/users.db
```

### 2. Back end

Run these from the project root, because the code imports from the `backend` package:

```bash
python -m venv backend/.venv
source backend/.venv/bin/activate        # Windows: backend\.venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

The API is now at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/api/health`.

You can also test the research pipeline on its own:

```bash
python -m backend.pipeline
```

### 3. Front end

```bash
cd frontend
npm install
npm run dev
```

The front end reads the API address from `VITE_API_URL` in `frontend/.env`. If it is not set, it uses `http://127.0.0.1:8000`.

```env
VITE_API_URL=http://127.0.0.1:8000
```

## API overview

| Area | Endpoints |
| --- | --- |
| Auth | `POST /api/register`, `/api/login`, `/api/logout`, `GET /api/session` |
| Password reset | `POST /api/forgot-password`, `/api/verify-otp`, `/api/reset-password` |
| Research | `POST /api/research` |
| PDF | `POST /api/individual/upload`, `POST /api/individual/chat`, `GET /api/individual/{id}/file` |
| Chat history | `GET/POST /api/conversations`, `GET/PATCH/DELETE /api/conversations/{id}`, `POST /api/conversations/{id}/messages` |
| Admin | `GET /api/admin/dashboard`, `DELETE /api/admin/users/{id}`, `DELETE /api/admin/logins` |

Chat, research and PDF routes need an `Authorization: Bearer <token>` header, which the login response provides. Admin routes additionally require the admin account.

## Deployment notes

- The front end can be deployed to Vercel. Set `VITE_API_URL` to your back end URL.
- Uploaded PDFs and the Chroma index are saved on local disk (`backend/individual_chroma`). Serverless hosts such as Vercel have temporary disks, so use a host with persistent storage for the back end, or move these files to external storage.
- A research request can take a while. The front end gives up after 3 minutes.
- Groq and Mistral free tiers have rate limits. The app retries and shows a friendly message when one is hit.

## Admin access

The dashboard is available only to the admin email, which is hard-coded as `ADMIN_EMAIL` in both `backend/main.py` and `frontend/src/App.jsx`. To use a different admin, change it in both places.
