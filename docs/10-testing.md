# 10. Testing and continuous integration

This project uses a foundation-first automated test setup:

- **Backend:** pytest and FastAPI's `TestClient` for unit and API tests.
- **Frontend:** Vitest, jsdom and React Testing Library for unit and component tests.
- **CI:** GitHub Actions runs backend tests, frontend tests and the production frontend build on pushes and pull requests.

Browser end-to-end testing (for example Playwright) is not part of this setup.

## Safety and isolation

Tests must be deterministic and must not use production data, live API keys,
emails, or external AI/search services.

Backend `conftest.py` sets `CODEX_DATABASE_PATH` to a temporary directory and
sets dummy Groq, Tavily and Mistral credentials before importing application
modules. The application initializes its SQLite schema on import, so the
environment must be set first. The temporary database is cleared between
tests and removed when the pytest process exits. Never change tests to point at
`backend/users.db`.

Tests that exercise external integrations should replace the provider boundary
with a mock using pytest's `monkeypatch` or another explicit fake. Avoid
network calls in regular test runs. PDF/vector-store tests should similarly
use a temporary Chroma path or mock the embedding/vector-store boundary; the
initial suite does not call live embedding services.

Frontend tests replace `fetch` with a controlled mock. They do not need a
running FastAPI server or `.env` file.

## One-time setup

From the repository root, create and activate the backend virtual environment
as described in [08-setup-and-deployment.md](08-setup-and-deployment.md), then
install test dependencies:

```bash
python -m pip install -r backend/requirements-test.txt
```

Install frontend dependencies from the lockfile:

```bash
npm ci --prefix frontend
```

## Running checks locally

From the repository root:

```bash
python -m pytest -c backend/pytest.ini
npm --prefix frontend test
npm --prefix frontend run build
```

For iterative frontend development, use:

```bash
npm --prefix frontend run test:watch
```

The backend configuration discovers tests only under `backend/tests/` and
reports skipped, failed and passed tests. Vitest runs once by default; the
watch script is for local work. No coverage threshold is enforced yet. A
coverage percentage will be considered after the suite has enough stable,
meaningful tests to make that metric useful.

## Current coverage

The initial backend suite covers:

- Account registration, email normalization, duplicate/short-password rejection,
  password authentication and session revocation.
- The HTTP login lifecycle: register, authenticate, receive a session token,
  access the protected session endpoint, log out, and verify the token is
  rejected. Invalid credentials do not create a session or login-activity row.
- Authentication requirements on research endpoints.
- Technical prompt rewrite success and empty-input rejection.
- Confirmation that rewriting does not create conversation/history records.
- Research API request/response behavior and one full authenticated
  search-scrape-write pipeline run with the external services mocked.
- Password reset through OTP request, verification, password replacement,
  expiry, and invalid-attempt exhaustion. OTP email delivery is mocked.
- Admin authorization, protected-account deletion, user/login-history deletion,
  and rejection of admin actions by non-admin users.
- PDF upload validation and document ownership checks for PDF chat and file
  retrieval. Index building and answer generation are mocked.
- Conversation ownership and first-message chat-title behavior.
- Research report title parsing, the 80-character limit, and malformed-output
  fallback.

The initial frontend suite covers:

- Conversion of alternate math delimiters, bracketed standalone equations and
  selected math expressions in prose.
- Preservation of inline/fenced code and ordinary currency text.
- Login form submission and rejected credentials.
- Technical-mode prompt rewrite, editable draft approval, and submission of
  the approved text to both research and conversation history.

The pipeline test uses fake search, scraping, and writer services. It executes
the real pipeline orchestration and authenticated research route, but it does
not call Groq, Tavily, or external websites.

PDF API tests do not require a Mistral API key. They replace the PDF index
builder and answer-generation boundary with fakes, while exercising upload
validation, database ownership records, and route authorization. They do not
test real PDF extraction, embeddings, or Chroma persistence.

These are regression checks for covered behavior, not a guarantee that every
route, component, integration, or security property has been tested. Extend
the suite as features are added. Prioritize ownership boundaries, auth/session
changes, data mutations, and failure paths.

## Writing tests

### Backend

- Put tests in `backend/tests/test_*.py`.
- Keep unit tests independent of HTTP where possible; use `TestClient` for
  request/response behavior.
- Use the `client` and `user_factory` fixtures for authenticated API tests.
- Patch imported service functions at the point where the route uses them
  (for example, `backend.main.rewrite_research_prompt`).
- Assert observable outcomes and security boundaries, not only that a function
  was called.
- If adding a module import that opens a database or provider connection, make
  sure the test environment is established before import and the resource is
  isolated or mocked.

### Frontend

- Put tests beside their source as `*.test.js` or `*.test.jsx`.
- Prefer React Testing Library queries by role, label, and visible text.
- Mock `fetch` with explicit responses and assert request bodies/behavior.
- Avoid snapshots of the entire application; test user-visible behaviors and
  meaningful data contracts.
- Keep pure transformation logic separately testable without mounting React.

## GitHub Actions

`.github/workflows/ci.yml` defines independent backend and frontend jobs.
The backend job installs `backend/requirements-test.txt` and runs pytest.
The frontend job runs `npm ci`, the Vitest suite and `vite build`. CI uses dummy
provider keys only through test setup; no repository secrets are required.
The workflow has read-only repository permissions and does not deploy.

Before merging a pull request, confirm both jobs pass. A local command that
fails should be fixed or its reason clearly reported; do not skip a test just
to obtain a green check.

Next: [09-project-history.md](09-project-history.md)
