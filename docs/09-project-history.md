# 9. Project History

How CODEX was built, and why the main decisions were made. Dates are from the developer journals and git history.

## Team

| Member | GitHub | Main areas |
| --- | --- | --- |
| Pranav Garg (1024170298) | Pranav Garg | Full stack and integration: Streamlit prototype, React + FastAPI migration, research pipeline, admin dashboard, deployment, UI polish, security hardening |
| Harshil Agarwal (1024170304) | hagarwalbe24-sys | PDF analyzer (Individual mode), OTP password recovery with Gmail SMTP, login page, PDF viewer |
| Noor (noorpeep) | noorpeep | Persistent chat history and the navigation drawer |
| Axenvyy | Axenvyy | Security work on the `secure` branch: Argon2 hashing, cookies, rate limiting, role-based access, tests, architecture docs (not yet merged into `main`) |

## Timeline

### Phase 1 — Streamlit prototype (7–28 Aug 2026)
- Built the first version in Streamlit: Individual mode, Nexus mode and an admin dashboard.
- Added registration, login and OTP password reset (Gmail SMTP with an app password).
- Added SQLite for users and login activity, with admin CRUD and an Excel export.
- **Why Streamlit first:** it let us test the AI ideas in days without writing a frontend.

### Phase 2 — React + FastAPI migration (26 Aug–5 Sep)
- New repository created on 26 Aug.
- Rebuilt every screen in React with Vite and moved logic into a FastAPI backend with REST endpoints.
- **Why we moved:** Streamlit reruns the whole script on every click, which made login state, multi-page navigation and custom design hard. A separate API also lets other clients use the backend.

### Phase 3 — AI integration and first deployment (5–10 Sep)
- Connected the research pipeline and PDF Q&A to the React UI.
- Deployed the frontend to Vercel and the backend to Render. Fixed environment variables, API URLs and import paths in production.
- Admin dashboard rebuilt in React (many small PRs from the `nolan` branch on 7–8 Sep).

### Phase 4 — Documentation (10–19 Sep)
- Developer journals added.
- UML use case, class and activity diagrams, and the project report.

### Phase 5 — Features (7–16 Oct)
- **PDF viewer** (Harshil, 7–8 Oct): view and download the uploaded PDF.
- **Chat history and sidebar** (Noor, 10 Oct): conversations saved in SQLite, rename and delete, sliding drawer.
- **Pipeline fixes** (16 Oct): research flow, PDF indexing and agent prompts improved. The "NEXUS" tab was renamed "CODEX" and the drawer became a chat sidebar.

### Phase 6 — Cleanup, polish and hardening (30 Oct)
- **Cleanup:** stopped tracking `node_modules`, the Chroma runtime data and `.DS_Store`; removed unused packages (framer-motion, xlsx, langgraph, extra LangChain providers).
- **UI polish:** design tokens in `globals.css`, tactile buttons, a ticker, accessibility fixes.
- **Security:** admin access moved from a query parameter to the session; salted PBKDF2 hashing with automatic upgrade; OTP attempt limit; minimum password length; 25 MB upload cap. Done with AI-assisted code review (Claude).

## Key design decisions

| Decision | Alternatives | Why |
| --- | --- | --- |
| Fixed pipeline (search → scrape → write) instead of a free-running agent | Fully autonomous multi-agent loop | Predictable cost and time; fewer LLM calls stays within free-tier rate limits |
| Scrape directly instead of via a reader agent | Reader agent with `scrape_webpage` | Saves one LLM call per request |
| Critic turned off | Run the critic each time | Doubled LLM calls and kept hitting rate limits |
| Groq for the LLM | OpenAI, Gemini | Very fast and has a free tier |
| Mistral for embeddings | OpenAI, local models | Free tier, good quality, no GPU needed on the server |
| Chroma for vectors | Pinecone, FAISS | Runs locally, saves to disk, no extra service |
| MMR retrieval | Plain similarity | Avoids five near-identical chunks; gives broader context |
| Separate summary path | Normal retrieval for everything | "Summarize" is not similar to any one chunk; summaries need the whole document |
| Content-based document ID (MD5) | Random ID | Re-uploading the same PDF reuses its index |
| Opaque session tokens in SQLite | JWT | Can be revoked on sign-out; simple to understand |
| PBKDF2 from the standard library | bcrypt, Argon2 | No extra dependency, and old SHA-256 hashes could be upgraded in place |

## What we would do next

- Merge the useful parts of the `secure` branch (rate limiting, roles, tests).
- Stop tracking `users.db`.
- Stream research progress to the UI so the stage display reflects real steps.
- Re-enable the critic when rate limits allow, and use its feedback to revise the report.
- Support scanned PDFs with OCR, and multiple PDFs in one chat.
- Move storage to a managed database and object storage for reliable deployment.
