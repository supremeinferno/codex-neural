# Backend Guide

The backend is a Python 3.11+ FastAPI service. Its runtime dependencies are listed in [`requirements.txt`](requirements.txt); `pyproject.toml` currently declares Python and pytest configuration but does not declare runtime packages.

From the repository root, create/activate a virtual environment, then install and test:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m pip install pytest
python -m pytest backend/tests -q
```

The intended API launch command is:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
```

The app imports and registers its routers through `main.py`. The focused route tests exercise research, PDF, and admin handlers without provider credentials; live AI calls still require their configured provider keys. See the repository's [development guide](../docs/development.md) for remaining runtime caveats.

For detailed responsibilities and functions, see the [architecture and module reference](../docs/architecture.md). For provider credentials, settings, dependencies, and frontend integration, see [development setup](../docs/development.md). The database is stored at `backend/users.db`; PDF source files and Chroma index data are stored under `backend/individual_chroma/`.
