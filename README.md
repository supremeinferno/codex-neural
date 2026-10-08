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

Requirements: Python 3.11 or newer and Node.js/npm. External model and search credentials are needed to use research and PDF AI features, but not to run the isolated security and repository tests.

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

The frontend defaults to `http://localhost:5173` and calls the backend at `http://127.0.0.1:8001`. Set `VITE_API_URL` in a Vite environment file such as `frontend/.env.local` to use another API origin.

## Backend Runtime

The intended local API command is:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
```

The API exposes interactive docs at `/docs` when running. Feature handlers are registered from dedicated route modules; see [Architecture and Module Reference](docs/architecture.md) for the route ownership and [Development Setup](docs/development.md) for remaining runtime caveats.

## Architecture

The backend separates app wiring, middleware, API routers, security helpers, auth services, and repository setup. This separation is still partial: auth services retain direct SQLite access alongside the repository module. The frontend's main state and workflows remain primarily in `frontend/src/App.jsx`.

See [Architecture and Module Reference](docs/architecture.md) for module-level responsibilities and the API route list. See [Development Setup](docs/development.md) for dependency and environment variable details.