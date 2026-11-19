# Test Infrastructure

This project now has a foundation-first automated test setup for the FastAPI
backend and React frontend. It is intended to catch regressions during
development and pull-request review. It does not include browser end-to-end
(E2E) testing such as Playwright, and it does not deploy the application.

## Components

### Backend

- **pytest** is the test runner. Backend tests live in `backend/tests/` and are
  selected by `backend/pytest.ini`.
- **FastAPI `TestClient`** exercises API routes without starting a separate
  server.
- `backend/requirements-test.txt` includes the backend runtime requirements
  plus the test dependencies.
- `backend/tests/conftest.py` supplies the shared test fixtures, including an
  API client and a helper for creating authenticated users.

The backend tests cover registration and session behavior, the API login
lifecycle, research endpoint authentication, technical prompt rewriting,
conversation ownership, initial chat-title behavior, research report-title
parsing and fallback, and a complete mocked search-scrape-write run through the
authenticated research endpoint. They also cover password-reset OTP success
and failure cases, admin authorization and mutations, and PDF upload and
document-ownership boundaries.

### Frontend

- **Vitest** runs JavaScript and React tests.
- **jsdom** supplies a browser-like DOM for component tests.
- **React Testing Library** tests visible UI behavior and interactions.
- `frontend/package.json` defines `test` for a one-time run and `test:watch` for
  interactive local development. Dependencies are locked in
  `frontend/package-lock.json`.

The frontend tests cover login form success and rejection, the shared
math-Markdown normalizer, and the Technical-mode review flow, including editing
the proposed prompt and approving it before research is sent.

### Continuous integration

`.github/workflows/ci.yml` runs on pushes and pull requests. It has separate
backend and frontend jobs:

1. Install backend test dependencies and run pytest.
2. Install frontend dependencies with `npm ci`, run Vitest, and build the
   production frontend.

The workflow uses read-only repository permissions. It does not deploy and
does not require repository secrets for these tests.

## Test isolation and safety

The login workflow test exercises registration, login, protected session
access, logout, and rejection of the revoked token through the HTTP API. The
frontend login tests exercise successful credential submission and rejected
credentials at the form level.

The full research workflow test runs the protected research endpoint and the
real search-scrape-write pipeline orchestration with fake provider boundaries.
It verifies search input, first-URL scraping, writer inputs, and the parsed
report response without contacting Groq, Tavily, or external websites.

Password-reset tests replace OTP email delivery with a captured test OTP. PDF
route tests mock index construction and question answering, so they do not
require a Mistral API key or perform real extraction, embedding, or vector
database operations.

Backend modules initialize SQLite during import and use
`CODEX_DATABASE_PATH` to choose the database. The test setup sets this variable
to a uniquely named temporary database before importing the application. It
also sets dummy provider credentials, clears test tables between tests, and
removes the temporary directory when the pytest process exits. A guard raises
an error if the configured test database resolves to the repository's
`backend/users.db`.

External AI, search, email, PDF indexing, and answer-generation behavior is
mocked where exercised by the suite. Tests should not make live provider
requests, send email, or use production credentials. Frontend API requests are
replaced with mocked `fetch` responses; tests do not need a running backend.

## Running tests

Run commands from the repository root.

Install backend test requirements into the active Python environment:

```bash
python -m pip install -r backend/requirements-test.txt
```

Install the frontend dependencies from the lockfile:

```bash
npm ci --prefix frontend
```

Run the backend tests:

```bash
python -m pytest -c backend/pytest.ini
```

Run frontend tests once:

```bash
npm --prefix frontend test
```

Run frontend tests in watch mode:

```bash
npm --prefix frontend run test:watch
```

Run the production build:

```bash
npm --prefix frontend run build
```

## Adding tests

### Backend

- Add test modules named `test_*.py` under `backend/tests/`.
- Use the `client` fixture for HTTP behavior and `user_factory` for protected
  routes requiring a signed-in user.
- Use pytest's `monkeypatch` fixture to replace service functions at the point
  where they are called, such as `backend.main.rewrite_research_prompt`.
- Prefer assertions on observable responses, database state, and authorization
  boundaries over assertions that only confirm a mock was called.
- Keep any new database, file, vector-store, or provider state isolated from
  developer and production data.

### Frontend

- Add `*.test.js` or `*.test.jsx` files beside the source they test.
- Query components by accessible role, label, and visible text.
- Mock `fetch` with explicit responses and verify meaningful request payloads
  and UI behavior.
- Keep pure transformations independently testable; avoid broad snapshots of
  the entire application.

## Current limitations

The current tests are a growing regression baseline, not complete coverage of
all routes, components, integrations, or security properties. Real PDF
extraction/indexing and vector-store behavior are not covered; PDF API tests
mock those external-resource boundaries. Coverage percentages are not
enforced. Browser E2E tests and performance benchmarking are deferred.