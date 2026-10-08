# Nexus Research

Nexus Research is a full-stack research assistant. Users can request a web-sourced research report or upload a PDF and ask questions about its contents. The project contains a React/Vite frontend and a Python/FastAPI backend, with SQLite-backed accounts and sessions.

## Project Contents

- `frontend/`: React application and Vite development server.
- `backend/`: FastAPI application, research pipeline, PDF retrieval, authentication, and local tests.
- `journals/`: project journals and research notes.
- `security.md`: implemented security controls and known limitations.
- `docs/architecture.md`: module responsibilities, key functions, data flow, and API routes.
- `docs/development.md`: dependencies, configuration, local commands, and current integration caveats.

## Quick Start

Requirements: Python 3.11 or newer and Node.js/npm. The local demo runs without provider credentials; live research and PDF AI features need external model/search keys.

From the repository root, install backend dependencies and pytest:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m pip install pytest
```

Run the isolated backend tests:

```bash
python -m pytest backend/tests -q
```

Install and start the frontend:

```bash
cd frontend
npm ci
npm run dev
```

The frontend defaults to `http://localhost:5173` and sends API calls to the same origin. Vite proxies `/api` to the local backend on `127.0.0.1:8001`; leave `VITE_API_URL` unset for this local setup. Set it in `frontend/.env.local` only when the API is hosted at a separate origin.

## Backend Runtime

The intended local API command is:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
```

The API exposes interactive docs at `/docs` when running. Feature handlers are registered from dedicated route modules; see [Architecture and Module Reference](docs/architecture.md) for the route ownership and [Development Setup](docs/development.md) for remaining runtime caveats.

## No-Credential Demo

Run `uvicorn backend.demo:app --reload --host 127.0.0.1 --port 8001` in one terminal and `cd frontend && npm run dev` in another. Open `http://localhost:5173` and sign in with `codexproject9@gmail.com` / `NexusDemo!2026`.

This uses the real authentication, sessions, route authorization, admin dashboard, and UI, but returns clearly labeled placeholder research and PDF answers without calling external providers. Demo SQLite and uploaded files stay under the system temporary directory, separate from `backend/users.db`. Do not expose the demo server publicly; it uses a known seeded admin credential. More details are in [Development Setup](docs/development.md#no-credential-demo).

## Architecture

The backend separates app wiring, middleware, API routers, security helpers, auth services, and SQLite repository access. The frontend's main state and workflows remain primarily in `frontend/src/App.jsx`.

See [Architecture and Module Reference](docs/architecture.md) for module-level responsibilities and the API route list. See [Development Setup](docs/development.md) for dependency and environment variable details.