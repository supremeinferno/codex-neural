# 1. Overview

## What is CODEX?

CODEX is a web app that does research for you. It has two modes:

1. **CODEX research mode (also called "Nexus")** — You type a topic, such as *"Microplastics and human health"*. CODEX searches the web, reads the best source, and writes a structured report with an introduction, key findings, analysis, conclusion, and a list of cited sources.
2. **Individual mode (PDF analyzer)** — You upload a PDF, such as a research paper or class notes. You can then ask questions about it ("What method did the authors use?") or ask for a full summary. Answers come only from the PDF and mention page numbers.

Both modes save your conversations, so you can come back to them later from the sidebar.

## Who is it for?

- **Students** who want a quick, cited overview of a topic or want to understand a long paper.
- **Anyone** who wants answers grounded in real sources instead of a chatbot's memory.
- **An administrator** (one fixed account) who can see registered users and login activity on a dashboard.

## Feature list

| Feature | What it does |
| --- | --- |
| Register and sign in | Create an account with email and password. |
| Forgot password | Get a 6-digit code (OTP) by email, verify it, and set a new password. |
| Research reports | Multi-step AI pipeline: search, scrape, write. The report is shown as formatted Markdown. |
| Copy and download | Copy a report to the clipboard or download it as a `.md` file. |
| PDF upload | Upload a PDF up to 25 MB. It is split into chunks and indexed for search. |
| PDF Q&A | Ask questions about the PDF. The answer lists the pages it used. |
| PDF summary | Ask "summarize this" to get a summary of the whole document. |
| View PDF | Open the uploaded PDF next to the chat, or download it. |
| Chat history | Every research and PDF chat is saved. Rename or delete chats from the history page. |
| Sidebar | Slide-out drawer with "New chat", recent chats, and sign out. |
| Admin dashboard | Admin-only page showing total users, total logins, a user list, and recent logins. The admin can remove users and login records. |

## Key terms

If you are new to AI or web development, these terms appear throughout the docs.

| Term | Meaning in this project |
| --- | --- |
| **Frontend** | The part you see in the browser. Built with React. Lives in `frontend/`. |
| **Backend** | The server that does the work (database, AI calls). Built with FastAPI (Python). Lives in `backend/`. |
| **API** | The set of URLs (like `/api/login`) the frontend calls to talk to the backend. |
| **LLM** | Large Language Model, the AI that writes text. We use `openai/gpt-oss-120b`, served by Groq. |
| **Agent** | An LLM that can decide to call tools (such as a web search) before answering. |
| **Tool** | A Python function the agent may call. We have `tavily_search` and `scrape_webpage`. |
| **Pipeline** | A fixed sequence of steps. Our research pipeline is search → scrape → write. |
| **Tavily** | A search API built for AI apps. It returns clean results with titles, URLs, and text. |
| **Scraping** | Downloading a web page and pulling out its readable text. |
| **Embedding** | A list of numbers that represents the meaning of a piece of text. Similar meanings give similar numbers. We use Mistral to make embeddings. |
| **Vector store** | A database that stores embeddings and finds the most similar ones to a question. We use Chroma. |
| **Chunk** | A piece of a PDF page (up to 3000 characters). PDFs are split into chunks before being embedded. |
| **RAG** | Retrieval-Augmented Generation: find relevant chunks first, then give them to the LLM so it answers from real text. This is how PDF mode works. |
| **MMR** | Maximal Marginal Relevance: a retrieval method that picks chunks that are relevant *and* different from each other, so the answer is not built from five copies of the same paragraph. |
| **OTP** | One-Time Password: the 6-digit code emailed for password reset. |
| **SMTP** | The protocol used to send email. We send through Gmail's SMTP server. |
| **Session token** | A long random string given to you when you sign in. The browser sends it with every request to prove who you are. |
| **Hashing** | Turning a password into a fixed string that cannot be turned back. We store hashes, never real passwords. |
| **Rate limit** | A cap from an AI provider on how many requests you can make per minute. Free tiers hit it often. |

## Technology at a glance

| Layer | Technology | Why we chose it |
| --- | --- | --- |
| Frontend | React 19 + Vite | Component-based UI, fast dev server and builds |
| Markdown display | react-markdown + remark-gfm | Renders the AI's Markdown reports, including tables |
| Backend | FastAPI | Simple Python web framework with automatic request validation (Pydantic) |
| Database | SQLite | A single file, no server to install, enough for a class project |
| LLM | Groq (`openai/gpt-oss-120b`) via LangChain | Fast inference and a free tier |
| Agent framework | LangChain (`create_agent`) | Ready-made tool-calling agent loop |
| Web search | Tavily | Search results designed for LLMs |
| Scraping | requests + BeautifulSoup | Standard, reliable HTML parsing |
| PDF parsing | PyMuPDF (`fitz`) | Fast page-by-page text extraction |
| Embeddings | Mistral | Good quality and a free tier |
| Vector store | Chroma | Runs locally, persists to a folder |
| Email | Gmail SMTP + app password | Free, no extra service needed |

Next: [02-architecture.md](02-architecture.md)
