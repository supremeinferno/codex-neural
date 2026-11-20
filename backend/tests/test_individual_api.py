def _insert_document(app_module, document_id, user_id, name="paper.pdf"):
    conn = app_module.get_db()
    conn.execute(
        """
        INSERT INTO user_documents
            (document_id, user_id, document_name, pages, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (document_id, user_id, name, 1, "2026-01-01 00:00:00"),
    )
    conn.commit()
    conn.close()


def test_pdf_upload_rejects_non_pdf_and_oversized_file_without_indexing(
    app_module,
    client,
    monkeypatch,
    user_factory,
):
    headers, _ = user_factory("pdf-user@example.com")
    calls = []
    monkeypatch.setattr(
        app_module,
        "build_individual_index",
        lambda *_args: calls.append("called"),
    )

    invalid_type = client.post(
        "/api/individual/upload",
        headers=headers,
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )
    assert invalid_type.status_code == 200
    assert invalid_type.json()["success"] is False
    assert invalid_type.json()["message"] == "Only PDF files are allowed."

    monkeypatch.setattr(app_module, "MAX_PDF_BYTES", 4)
    oversized = client.post(
        "/api/individual/upload",
        headers=headers,
        files={"file": ("large.pdf", b"12345", "application/pdf")},
    )
    assert oversized.status_code == 200
    assert oversized.json()["success"] is False
    assert "25 MB" in oversized.json()["message"]
    assert calls == []


def test_pdf_upload_indexes_with_mock_and_records_document_owner(
    app_module,
    client,
    monkeypatch,
    user_factory,
):
    headers, user_id = user_factory("pdf-user@example.com")
    payload = b"%PDF-1.4 fake test bytes"
    expected = {
        "success": True,
        "message": "PDF indexed successfully.",
        "document_id": "abcdef123456",
        "document_name": "paper.pdf",
        "pages": 2,
        "chunks": 3,
    }
    calls = []

    def build_index(pdf_bytes, filename):
        calls.append((pdf_bytes, filename))
        return expected

    monkeypatch.setattr(app_module, "build_individual_index", build_index)

    response = client.post(
        "/api/individual/upload",
        headers=headers,
        files={"file": ("paper.pdf", payload, "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert calls == [(payload, "paper.pdf")]

    conn = app_module.get_db()
    document = conn.execute(
        "SELECT document_name, pages FROM user_documents "
        "WHERE document_id = ? AND user_id = ?",
        ("abcdef123456", user_id),
    ).fetchone()
    conn.close()
    assert dict(document) == {"document_name": "paper.pdf", "pages": 2}


def test_failed_pdf_index_does_not_create_document_record(
    app_module,
    client,
    monkeypatch,
    user_factory,
):
    headers, user_id = user_factory("pdf-user@example.com")
    monkeypatch.setattr(
        app_module,
        "build_individual_index",
        lambda *_args: {"success": False, "message": "No readable text."},
    )

    response = client.post(
        "/api/individual/upload",
        headers=headers,
        files={"file": ("empty.pdf", b"%PDF", "application/pdf")},
    )

    assert response.json()["success"] is False
    conn = app_module.get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM user_documents WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0]
    conn.close()
    assert count == 0


def test_pdf_chat_requires_document_ownership_before_answering(
    app_module,
    client,
    monkeypatch,
    user_factory,
):
    owner_headers, owner_id = user_factory("owner@example.com")
    other_headers, _ = user_factory("other@example.com")
    document_id = "abcdef123456"
    _insert_document(app_module, document_id, owner_id)
    calls = []
    monkeypatch.setattr(
        app_module,
        "answer_individual_question",
        lambda question, doc_id: calls.append((question, doc_id))
        or {"success": True, "answer": "Answer", "sources": []},
    )

    denied = client.post(
        "/api/individual/chat",
        headers=other_headers,
        json={"question": "What is the conclusion?", "document_id": document_id},
    )
    assert denied.status_code == 404
    assert calls == []

    allowed = client.post(
        "/api/individual/chat",
        headers=owner_headers,
        json={"question": "What is the conclusion?", "document_id": document_id},
    )
    assert allowed.status_code == 200
    assert allowed.json()["answer"] == "Answer"
    assert calls == [("What is the conclusion?", document_id)]


def test_pdf_file_endpoint_validates_id_and_enforces_owner(
    app_module,
    client,
    monkeypatch,
    tmp_path,
    user_factory,
):
    owner_headers, owner_id = user_factory("owner@example.com")
    other_headers, _ = user_factory("other@example.com")
    document_id = "abcdef123456"
    _insert_document(app_module, document_id, owner_id)

    pdf_file = tmp_path / f"{document_id}.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")
    monkeypatch.setattr(app_module, "INDIVIDUAL_DB_PATH", str(tmp_path))

    invalid_id = client.get(
        "/api/individual/not-a-valid-id/file",
        headers=owner_headers,
    )
    assert invalid_id.status_code == 400

    denied = client.get(
        f"/api/individual/{document_id}/file",
        headers=other_headers,
    )
    assert denied.status_code == 404

    inline = client.get(
        f"/api/individual/{document_id}/file",
        headers=owner_headers,
    )
    assert inline.status_code == 200
    assert inline.content == b"%PDF-1.4 test"
    assert inline.headers["content-type"] == "application/pdf"
    assert inline.headers["content-disposition"].startswith("inline;")

    download = client.get(
        f"/api/individual/{document_id}/file?download=true",
        headers=owner_headers,
    )
    assert download.status_code == 200
    assert download.headers["content-disposition"].startswith("attachment;")


def test_pdf_routes_require_authentication(client):
    upload = client.post(
        "/api/individual/upload",
        files={"file": ("paper.pdf", b"%PDF", "application/pdf")},
    )
    chat = client.post(
        "/api/individual/chat",
        json={"question": "Summarize", "document_id": "abcdef123456"},
    )

    assert upload.status_code == 401
    assert chat.status_code == 401
