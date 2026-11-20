# Performance measurement

This document records the plan and the instrumentation added to measure request
latency and find slow stages in CODEX's backend workflows.

## Plan

1. Measure total HTTP request duration and status for each API route.
2. Give each request a generated ID and include it in the response and timing
   events so request and stage measurements can be correlated.
3. Measure expensive research and PDF processing stages independently.
4. Record provider retry attempts and backoff delay.
5. Keep measurements privacy-safe, use the standard Python logging package, and
   avoid adding a monitoring dependency before there is data to justify one.
6. Add tests for timing, errors, request correlation, and avoiding sensitive
   values in logs.

## Implemented

### Request-level events

HTTP middleware in `backend/main.py` records method, route template, response
status, elapsed milliseconds, and request ID. Each response includes the same
ID in its `X-Request-ID` header. Unmatched routes are logged as `unmatched`;
raw URL paths and query strings are not logged.

### Stage-level events

`backend/observability.py` provides a reusable timer. Stage events include the
stage name, success/error outcome, elapsed milliseconds, request ID, and (on
failure) the exception class. Errors are re-raised unchanged.

Current stages:

| Workflow | Stage names |
| --- | --- |
| Research | `research_search`, `research_scrape`, `research_write` |
| PDF upload/indexing | `pdf_extract`, `pdf_chunk`, `pdf_vector_store_open`, `pdf_existing_index_lookup`, `pdf_embedding_and_index` |
| PDF question/summary | `pdf_vector_store_open`, `pdf_retrieval`, `pdf_answer_llm`, `pdf_summary_llm` |

`pdf_embedding_and_index` includes embedding API work and Chroma writes because
the current vector-store operation performs both together.

### Provider retries

When a PDF external call is retried after a rate limit, a warning event records
the fixed operation label, retry attempt, delay in seconds, and request ID.
Prompt text, provider response bodies, and exception messages are not logged.

## How to use the measurements

Run the API with normal INFO logging, for example:

```powershell
uvicorn backend.main:app --log-level info
```

For a local capture, run the API while saving its console logs to one file:

```powershell
uvicorn backend.main:app --log-level info 2>&1 |
  Tee-Object -FilePath .\backend-performance.log
```

In another terminal, reproduce the workflow a few times. Then summarize the
captured measurements with the standard-library analyzer:

```powershell
python -m backend.analyze_performance_logs .\backend-performance.log
```

It reports request and stage counts, errors, p50, and p95 durations, plus retry
counts and total retry delay. It reads the app's normal log format, ignores
unrelated lines, and reports malformed performance events. It uses linear
interpolation for percentiles. To analyze piped logs instead of a file:

```powershell
Get-Content .\backend-performance.log |
  python -m backend.analyze_performance_logs -
```

Compare repeated, representative runs. A large difference between a stage's
p50 and p95 can indicate intermittent upstream latency; retry counts can help
explain some slow requests. Measurements involving live search and AI providers
include their network latency and rate limits. Use mocked providers for
repeatable automated tests and staging for realistic end-to-end timings.

Run the focused instrumentation tests from the repository root with:

```powershell
python -m pytest -c backend/pytest.ini backend/tests/test_performance_log_analyzer.py backend/tests/test_observability.py backend/tests/test_research_api.py
```

## Privacy and current scope

Events use route templates and fixed stage/operation labels. They do not include
request bodies, prompts, PDF contents, user/document IDs, query strings, or
provider exception messages. Request IDs are random correlation values, not
user identifiers. The research pipeline prints only fixed progress messages;
it does not dump search results, scraped pages, source URLs, or generated reports
to the console. This also avoids failures when Windows console encodings cannot
represent Unicode in provider output.

The analyzer calculates percentiles for one local log capture; it does not
retain metrics across runs, provide dashboards, or export Prometheus or
OpenTelemetry data. Frontend rendering time is also outside the current
instrumentation.
