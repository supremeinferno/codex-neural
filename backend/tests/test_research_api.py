import logging
from types import SimpleNamespace


def test_protected_research_routes_require_authentication(client):
    assert client.post("/api/research/clarify", json={"topic": "AI agents"}).status_code == 401
    assert client.post("/api/research", json={"topic": "AI agents"}).status_code == 401


def test_clarify_returns_draft_without_creating_history(
    app_module,
    client,
    monkeypatch,
    user_factory,
):
    headers, _ = user_factory("researcher@example.com")
    calls = []

    def rewrite(topic):
        calls.append(topic)
        return "Explain how AI agents select tools."

    monkeypatch.setattr(app_module, "rewrite_research_prompt", rewrite)
    response = client.post(
        "/api/research/clarify",
        headers=headers,
        json={"topic": "AI tools?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "topic": "Explain how AI agents select tools.",
    }
    assert calls == ["AI tools?"]

    conn = app_module.get_db()
    assert conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM conversation_messages").fetchone()[0] == 0
    conn.close()


def test_clarify_rejects_empty_topic_without_calling_rewriter(
    app_module,
    client,
    monkeypatch,
    user_factory,
):
    headers, _ = user_factory("researcher@example.com")
    monkeypatch.setattr(
        app_module,
        "rewrite_research_prompt",
        lambda _topic: (_ for _ in ()).throw(AssertionError("must not be called")),
    )

    response = client.post(
        "/api/research/clarify",
        headers=headers,
        json={"topic": "   "},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Please enter a research prompt."


def test_research_route_returns_pipeline_result(
    app_module,
    client,
    monkeypatch,
    user_factory,
):
    headers, _ = user_factory("researcher@example.com")
    result = {
        "title": "AI Agents",
        "report": "# Findings",
        "search_results": "source",
        "scraped_content": "details",
        "feedback": "skipped",
    }
    topics = []
    monkeypatch.setattr(
        app_module,
        "run_research_pipeline",
        lambda topic: topics.append(topic) or result,
    )

    response = client.post(
        "/api/research",
        headers=headers,
        json={"topic": "AI agent tools"},
    )

    assert response.status_code == 200
    assert response.json() == result
    assert topics == ["AI agent tools"]


def test_research_endpoint_runs_full_pipeline_with_mocked_services(
    app_module,
    client,
    monkeypatch,
    user_factory,
    caplog,
    capsys,
):
    caplog.set_level(logging.INFO, logger="backend.performance")
    from backend import pipeline

    headers, _ = user_factory("researcher@example.com")
    events = []
    search_response = (
        "Authoritative source: https://research.example.org/paper. "
        "The\u202fsource reports a result."
    )

    class FakeSearchAgent:
        def invoke(self, payload):
            events.append(("search", payload))
            return {"messages": [SimpleNamespace(content=search_response)]}

    class FakeScraper:
        def invoke(self, payload):
            events.append(("scrape", payload))
            return "Scraped\u202fevidence from the source."

    class FakeWriter:
        def invoke(self, payload):
            events.append(("write", payload))
            return (
                "TITLE: Evidence Review\nREPORT:\n# Findings\n"
                "Supported\u202fconclusion."
            )

    monkeypatch.setattr(pipeline, "build_research_agent", FakeSearchAgent)
    monkeypatch.setattr(pipeline, "scrape_webpage", FakeScraper())
    monkeypatch.setattr(pipeline, "writer_chain", FakeWriter())
    monkeypatch.setattr(app_module, "run_research_pipeline", pipeline.run_research_pipeline)

    response = client.post(
        "/api/research",
        headers=headers,
        json={"topic": "What does the evidence show?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "search_results": search_response,
        "scraped_content": "Scraped\u202fevidence from the source.",
        "title": "Evidence Review",
        "report": "# Findings\nSupported\u202fconclusion.",
        "feedback": (
            "Critic temporarily skipped because "
            "Mistral rate limit was reached."
        ),
    }
    assert [event[0] for event in events] == ["search", "scrape", "write"]
    assert events[0][1]["messages"][0][1] == (
        "Find recent, reliable and detailed information about: "
        "What does the evidence show?"
    )
    assert events[1][1] == {"url": "https://research.example.org/paper"}
    assert events[2][1]["topic"] == "What does the evidence show?"
    assert "Scraped\u202fevidence from the source." in events[2][1]["research"]
    request_id = response.headers["X-Request-ID"]
    assert f"stage=research_search" in caplog.text
    assert f"stage=research_scrape" in caplog.text
    assert f"stage=research_write" in caplog.text
    assert f"request_id={request_id}" in caplog.text
    captured_output = capsys.readouterr().out
    assert "Authoritative source:" not in captured_output
    assert "Supported\u202fconclusion." not in captured_output
