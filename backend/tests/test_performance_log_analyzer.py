from backend.analyze_performance_logs import analyze_lines, format_report, main


def test_analyzer_groups_request_and_stage_timings_and_calculates_percentiles():
    lines = [
        "INFO:backend.performance:event=http_request method=POST "
        "route=/api/research status_code=200 duration_ms=1 request_id=a",
        "INFO:backend.performance:event=http_request method=POST "
        "route=/api/research status_code=500 duration_ms=2 request_id=b",
        "INFO:backend.performance:event=http_request method=POST "
        "route=/api/research status_code=200 duration_ms=100 request_id=c",
        "INFO:backend.performance:event=stage_timing stage=research_write "
        "outcome=success duration_ms=4 request_id=a error_type=-",
        "INFO:backend.performance:event=stage_timing stage=research_write "
        "outcome=error duration_ms=8 request_id=b error_type=RuntimeError",
    ]

    summary = analyze_lines(lines)

    request = summary["requests"]["POST /api/research"]
    assert request["count"] == 3
    assert request["errors"] == 1

    stage = summary["stages"]["research_write"]
    assert stage["count"] == 2
    assert stage["errors"] == 1
    assert stage["durations"] == [4.0, 8.0]

    report = format_report(summary)
    assert "POST /api/research" in report
    assert "90.20" in report
    assert "research_write" in report
    assert "p50 ms" in report


def test_analyzer_counts_provider_retries_and_ignores_invalid_events():
    lines = [
        "WARNING:backend.performance:event=provider_retry "
        "operation=pdf_answer_llm attempt=1 delay_seconds=8 request_id=x",
        "WARNING:backend.performance:event=provider_retry "
        "operation=pdf_answer_llm attempt=2 delay_seconds=16 request_id=x",
        "INFO:backend.performance:event=stage_timing stage=broken "
        "outcome=error duration_ms=NaN request_id=x error_type=ValueError",
        "INFO:backend.performance:event=http_request method=GET "
        "route=/api/health status_code=200 duration_ms=-1 request_id=x",
    ]

    summary = analyze_lines(lines)

    assert summary["retries"] == {
        "pdf_answer_llm": {
            "count": 2,
            "total_delay_seconds": 24.0,
        }
    }
    assert summary["stages"] == {}
    assert summary["requests"] == {}
    assert summary["ignored_events"] == 2


def test_cli_reads_a_file_and_reports_unreadable_file(capsys, tmp_path):
    log_file = tmp_path / "performance.log"
    log_file.write_text(
        "INFO:backend.performance:event=http_request method=GET "
        "route=/api/health status_code=200 duration_ms=12 request_id=x\n",
        encoding="utf-8",
    )

    assert main([str(log_file)]) == 0
    assert "GET /api/health" in capsys.readouterr().out

    assert main([str(tmp_path / "missing.log")]) == 2
    assert "Unable to read log file" in capsys.readouterr().err
