# Personal command guide

This is a quick reference for running, building, testing, and measuring CODEX
locally on Windows with PowerShell. Run commands from the repository root unless
a step says to change folders:

```powershell
C:\Users\91991\OneDrive\Desktop\codexproject\codex-neural
```

The backend must be started from this folder so Python can import the `backend`
package.

## Prerequisites

- Python 3.11 or newer.
- Node.js 18 or newer, with npm.
- API credentials in a root-level `.env` file for the live AI/search features.
- Network access for provider calls and package installation.

Example `.env` names (use your own values; do not commit real credentials):

```env
GROQ_API_KEY=...
TAVILY_API_KEY=...
MISTRAL_API_KEY=...
SMTP_EMAIL=...
SMTP_APP_PASSWORD=...
```

Groq and Tavily are used by research; Groq and Mistral are used by PDF
features; SMTP values are needed for email password reset. The app can start
without all provider credentials, but the features depending on missing keys
will fail. Frontend development defaults to `http://127.0.0.1:8000`; set
`VITE_API_URL` in `frontend/.env` only if the backend uses another URL, then
restart Vite.

## One-time environment setup

### Backend virtual environment

Create a virtual environment once from the repository root if you do not
already have one:

```powershell
python -m venv .venv
```

Activate it in each new PowerShell terminal that will run backend commands:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the Python executable in the environment
directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-test.txt
```

Install backend and test packages once (or after dependencies change):

```powershell
python -m pip install -r backend\requirements-test.txt
```

`requirements-test.txt` includes the backend runtime requirements plus `pytest`
and `httpx`. For running the backend only, `backend\requirements.txt` contains
runtime dependencies.

### Frontend packages

Install npm packages once (or after `frontend\package.json` changes):

```powershell
npm --prefix frontend install
```

## Start the application

Use separate PowerShell terminals for the backend and frontend. Activate the
backend virtual environment in the backend terminal first.

### Terminal 1: backend

From the repository root:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info
```

Keep this terminal open. Check that the backend is responding at
<http://127.0.0.1:8000/api/health>. Open <http://127.0.0.1:8000/docs> for the
interactive API page.

### Terminal 2: frontend development server

```powershell
npm --prefix frontend run dev
```

Open the localhost URL printed by Vite (normally <http://localhost:5173>).
This is the usual choice while changing frontend code; Vite reloads changes.

## Build and preview the frontend

Building is required before preview. From the repository root:

```powershell
npm --prefix frontend run build
npm --prefix frontend run preview
```

Open the preview URL printed by Vite (normally <http://localhost:4173>). The
backend must also be running for API-backed features. Rebuild after frontend
changes if you want preview to show the new build.

## Run tests

Run backend tests from the repository root with the backend virtual environment
activated and the test dependencies installed:

```powershell
python -m pytest -c backend\pytest.ini backend\tests
```

Run frontend tests after npm packages are installed:

```powershell
npm --prefix frontend test
```

The backend tests use a temporary database and mocked provider operations;
they do not require live AI keys or a running server.

## Capture and analyze performance logs

Prerequisites:

- Start the backend from the repository root, in the intended virtual
  environment.
- Frontend package setup is only needed if you will exercise the app through
  its UI; API requests can be tested independently.
- Use the dev server or a successful production build and preview.
- Sign in and run a few representative research/PDF actions. Live actions
  require the relevant `.env` API keys.

Start the backend with a log capture in Terminal 1:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info 2>&1 |
  Tee-Object -FilePath .\backend-performance.log
```

In Terminal 2, start the frontend (`npm --prefix frontend run dev`) or preview
(`npm --prefix frontend run preview`) and use the app. After collecting requests,
stop Uvicorn with `Ctrl+C`. Back in the repository root, with the backend
virtual environment active, summarize the log:

```powershell
python -m backend.analyze_performance_logs .\backend-performance.log
```

The summary groups requests and workflow stages and shows counts, errors,
p50/p95 durations, and retry counts/delays. The log file is created in the
repository root. Do not commit it; it may contain operational details.

To analyze an existing log through standard input:

```powershell
Get-Content .\backend-performance.log |
  python -m backend.analyze_performance_logs -
```

## Common command problems

| Problem | Cause and fix |
| --- | --- |
| `No module named 'backend'` | The current folder is not the repository root. `Set-Location C:\Users\91991\OneDrive\Desktop\codexproject\codex-neural`, activate `.venv`, and retry. |
| `No module named 'uvicorn'` or `pytest` | The active Python environment lacks dependencies. Activate `.venv` and install the relevant requirements file above. |
| `npm` or `node` is not recognized | Install Node.js, reopen PowerShell, and check `node --version` and `npm --version`. |
| Frontend cannot connect to API | Confirm Uvicorn is running at port 8000 and check `frontend/.env` for `VITE_API_URL`; restart Vite after changing it. |
| `npm run preview` shows an old build | Stop preview, rerun the build command, and start preview again. |
| Unicode/charmap error in backend terminal | Restart the backend after updating to the version that prints progress only, rather than dumping AI-generated text to the Windows console. |

For fuller setup and deployment notes, see
[docs/08-setup-and-deployment.md](docs/08-setup-and-deployment.md). For the
instrumentation and log event details, see
[docs/performance-measurement.md](docs/performance-measurement.md).
