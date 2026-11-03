# Personal Reflection — Pranav Garg

**Roll No:** 1024170298
**Role:** Full Stack / AI Systems Developer, and integrator for the team
**Project:** CODEX — Multi-Agent AI Research System
**Period:** 7 Aug – 30 Oct 2026

This document is the second half of my journal. My weekly log, contribution summary and technical learning are in [1024170298-Pranav_Garg.md](1024170298-Pranav_Garg.md). This file covers what I got wrong, what I got right, and the lessons I am taking forward. Every point can be checked in the repository (commit hashes are given where useful).

---

## 1. Mistakes I made

### Mistake 1: I committed generated files to git
**What happened:** `frontend/node_modules`, Python `__pycache__` files, the Chroma vector database and uploaded PDFs, and `.DS_Store` files were all committed. One teammate commit (`e3dca7d`, "update") changed only cache and build files.
**Why it was wrong:** It bloated the repository by thousands of files, caused pointless merge conflicts, and put user-uploaded PDFs into version history.
**How I fixed it:** In `b247a13` I stopped tracking these files and tidied `.gitignore`.
**What I learned:** Write `.gitignore` *before* the first commit, and check `git status` before every commit. Git is for source code, not for things a tool can regenerate.

### Mistake 2: I tracked the user database (`users.db`) in git
**What happened:** `backend/users.db` has been changed in 22 commits, many titled just "Update users.db".
**Why it was wrong:** Every teammate's local accounts overwrote everyone else's, and the file holds email addresses and password hashes in the repository history. Binary files also cannot be merged.
**Status:** Not fixed yet. A teammate added it to `.gitignore` on the `secure` branch (`fa28c63`), but that branch is not merged. Fixing it is listed in [docs/07-security.md](../docs/07-security.md).
**What I learned:** Data and code are different things. The app should create its database on first run, and a seed script should create test accounts.

### Mistake 3: I stored passwords with plain SHA-256
**What happened:** Early versions hashed passwords with a single unsalted SHA-256.
**Why it was wrong:** SHA-256 is designed to be fast, so an attacker can try billions of guesses per second. Without a salt, two users with the same password have the same hash, and precomputed tables work.
**How I fixed it:** In `10cc3af` I switched to PBKDF2-SHA256 with a random salt and 600,000 iterations. Old hashes still verify and are upgraded automatically at the next sign-in, so no user had to reset a password.
**What I learned:** Password hashing needs a *slow*, *salted* algorithm (PBKDF2, bcrypt, Argon2). I also learned how to migrate live data without breaking existing users.

### Mistake 4: Anyone could become admin
**What happened:** The admin API decided who was admin from an `?email=` query parameter sent by the browser.
**Why it was wrong:** Anyone could call `/api/admin/dashboard?email=<admin email>` and see or delete every user. Hiding the Dashboard tab in React did not protect anything, because the API could be called directly.
**How I fixed it:** In `10cc3af` admin routes now use `require_admin`, which reads the signed-in session on the server.
**What I learned:** Never trust the client. The frontend controls what is *shown*; only the backend controls what is *allowed*.

### Mistake 5: Unclear commits and too many tiny pull requests
**What happened:** Commit messages like "...", "..", "useless update", "update files" and "regular updates". On 7–8 Sep I opened and merged more than 15 PRs from the `nolan` branch, some changing one line. `config.js` was changed 6 times in one day while I tried different API URLs.
**Why it was wrong:** History does not explain *why* anything changed, reviewers cannot follow the work, and I was effectively debugging production by committing.
**What I learned:** One commit should be one logical change with a message that says what and why. Test configuration locally (or with environment variables) before committing. My later commits (`b247a13`, `10cc3af`) follow this.

### Mistake 6: I added dependencies we never used
**What happened:** `requirements.txt` and `package.json` included `langgraph`, `langchain-google-genai`, `langchain-xai`, `framer-motion` and `xlsx`, none of which the code used.
**Why it was wrong:** Slower installs, larger deploys, and more packages that could have security problems.
**How I fixed it:** Removed in `b247a13`.
**What I learned:** Add a dependency when the code needs it, and remove it when the code stops needing it.

### Mistake 7: The progress display does not reflect real progress
**What happened:** The research page shows four stages (Research, Read, Write, Critique) that advance on a timer. The backend does not report progress, and the Critic stage is switched off.
**Why it was wrong:** The UI suggests something is happening that may not be. A user could think the report was critiqued.
**Status:** Not fixed. The proper fix is to stream real progress from the backend (Server-Sent Events) and remove or re-enable the Critique stage.
**What I learned:** UI feedback should be honest about what the system is doing.

### Mistake 8: I did not plan for where data lives in production
**What happened:** SQLite and the Chroma folder are saved on the server's local disk. Free hosting tiers wipe that disk on redeploy, so uploaded PDFs and new accounts can disappear. `backend/api/index.py` is empty, so the combined Vercel deploy in `vercel.json` is unfinished.
**What I learned:** Check early whether the host has persistent storage. Stateless servers need an external database and file storage.

### Mistake 9: No automated tests
**What happened:** Every change was checked by hand in the browser.
**Why it was wrong:** The security fixes in `10cc3af` could be broken by a later change and nobody would notice.
**What I learned:** At least the risky parts (sign-in, admin checks, chat ownership) should have tests. The `secure` branch has a start on this that should be merged.

### Mistake 10: Team branches drifted apart
**What happened:** The `secure` branch has 12 commits (Argon2 hashing, rate limiting, role-based access, tests) that were never merged into `main`. Meanwhile I added different security fixes to `main`, so two people solved the same problem in two ways.
**What I learned:** As the integrator, I should have reviewed open branches regularly and agreed with the team who owns which area before starting work.

### Mistake 11: A merge deleted working code, and the pipeline used the wrong agent
**What happened:** While merging branches, the code that created a chat before a research request and the 3-minute `AbortController` timeout were lost from `App.jsx`. Separately, the research pipeline called the agent that did *not* have the search tool, and fixed 40-second `sleep` calls had been added to avoid rate limits.
**Why it was wrong:** Research results stopped saving to history, requests could hang forever, the "search" step was not actually searching, and every request waited 40 extra seconds even when no limit was hit.
**How I fixed it:** In `a6b44cd` I restored the lost code, switched to the agent with `tavily_search`, removed the sleeps and added retries that only wait when a rate limit actually occurs.
**What I learned:** After every merge, test the main user flows end to end. When something is slow or failing, find the cause instead of adding a delay.

---

## 2. What I did well

1. **Choosing to migrate from Streamlit.** Streamlit was right for a fast prototype. Once we needed login state, multiple pages and a custom design, moving to React + FastAPI was the correct call, and it gave us a clean API that any client can use.
2. **Designing around free-tier limits.** I cut the pipeline to one search agent plus direct scraping plus one writer call, capped text at 6000 characters, and added retry logic. This kept the app usable without paying for API access.
3. **Migrating passwords without breaking users.** The legacy-hash upgrade meant zero forced password resets.
4. **Separating concerns in the backend.** `main.py` (HTTP), `auth.py` (accounts), `pipeline.py` (research), `individual.py` (PDFs). Each teammate could work on one file without touching the others.
5. **Getting it deployed.** I took the app from localhost to a live Vercel + Render deployment and fixed the production-only problems (environment variables, CORS, import paths).
6. **Integrating everyone's work.** I merged 30+ pull requests from four branches into one working app.
7. **Cleaning up and documenting.** I removed dead files and dependencies and wrote documentation so anyone can understand and run the project.

---

## 3. Lessons I am taking forward

My technical learning is listed in my [journal](1024170298-Pranav_Garg.md#overall-technical-learning). These are the lessons about how I work.

- **Git hygiene:** `.gitignore` first, meaningful commit messages, small but *complete* commits, no generated or data files.
- **Reviewing my own old code:** finding and fixing my own security mistakes taught me more than getting it right the first time would have.
- **Using AI tools responsibly:** I used Claude for code review and for parts of the pipeline fixes, sidebar, security hardening and cleanup (those commits are marked `Co-Authored-By`). I learned to read and understand every suggested change before committing it, and to check it against the actual code.
- **Teamwork:** an integrator needs to communicate, not only merge. Unmerged branches and duplicated work were a coordination failure I am responsible for.

---

## 4. What I would do differently next time

1. Set up `.gitignore`, a branch strategy and commit-message rules on day one.
2. Write down the security model (who is allowed to do what) before writing any endpoints.
3. Choose hosting with persistent storage, or use a managed database, from the start.
4. Add tests for sign-in and access control alongside the code.
5. Hold a short weekly sync to review open branches and merge or close them.
6. Stream real progress from the backend instead of showing a timer-based animation.
