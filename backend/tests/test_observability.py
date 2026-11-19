import logging
import re

import pytest

from backend.observability import measure_stage, request_id_context


def test_stage_timing_logs_duration_and_request_id(caplog):
    context_token = request_id_context.set("request-123")
    try:
        with caplog.at_level(logging.INFO, logger="backend.performance"):
            with measure_stage("test_stage"):
                pass
    finally:
        request_id_context.reset(context_token)

    assert "event=stage_timing" in caplog.text
    assert "stage=test_stage" in caplog.text
    assert "outcome=success" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "request_id=request-123" in caplog.text


def test_stage_timing_logs_failure_and_preserves_exception(caplog):
    with caplog.at_level(logging.INFO, logger="backend.performance"):
        with pytest.raises(ValueError, match="expected failure"):
            with measure_stage("failing_stage"):
                raise ValueError("expected failure")

    assert "stage=failing_stage" in caplog.text
    assert "outcome=error" in caplog.text
    assert "error_type=ValueError" in caplog.text
    assert "expected failure" not in caplog.text


def test_request_timing_returns_id_and_logs_route_without_query_data(
    app_module,
    client,
    caplog,
):
    secret_query = "private-user-input"
    with caplog.at_level(logging.INFO, logger="backend.performance"):
        response = client.get(f"/api/health?topic={secret_query}")

    request_id = response.headers["X-Request-ID"]
    assert re.fullmatch(r"[a-f0-9]{32}", request_id)
    assert response.status_code == 200
    assert "event=http_request" in caplog.text
    assert "route=/api/health" in caplog.text
    assert f"request_id={request_id}" in caplog.text
    assert secret_query not in caplog.text


def test_retry_log_includes_operation_and_delay_without_exception_content(caplog):
    from backend.individual import run_with_retry

    class RateLimitError(Exception):
        status_code = 429

    def fail_with_rate_limit():
        raise RateLimitError("sensitive provider response")

    with caplog.at_level(logging.WARNING, logger="backend.performance"):
        with pytest.raises(RateLimitError):
            run_with_retry(
                fail_with_rate_limit,
                attempts=2,
                wait_seconds=0,
                operation="test_operation",
            )

    assert "event=provider_retry" in caplog.text
    assert "operation=test_operation" in caplog.text
    assert "attempt=1" in caplog.text
    assert "delay_seconds=0" in caplog.text
    assert "sensitive provider response" not in caplog.text
