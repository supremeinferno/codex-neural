def test_conversation_is_visible_only_to_its_owner(client, user_factory):
    owner_headers, _ = user_factory("owner@example.com")
    other_headers, _ = user_factory("other@example.com")
    created = client.post(
        "/api/conversations",
        headers=owner_headers,
        json={"kind": "research", "title": "Private research"},
    )

    assert created.status_code == 200
    conversation_id = created.json()["id"]

    owner_view = client.get(
        f"/api/conversations/{conversation_id}",
        headers=owner_headers,
    )
    other_view = client.get(
        f"/api/conversations/{conversation_id}",
        headers=other_headers,
    )
    other_list = client.get("/api/conversations", headers=other_headers)

    assert owner_view.status_code == 200
    assert other_view.status_code == 404
    assert other_list.json() == {"conversations": []}


def test_new_chat_title_uses_first_user_message(client, user_factory):
    headers, _ = user_factory("author@example.com")
    created = client.post(
        "/api/conversations",
        headers=headers,
        json={"kind": "research"},
    )
    conversation_id = created.json()["id"]

    saved = client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=headers,
        json={"role": "user", "content": "A useful research question"},
    )
    detail = client.get(
        f"/api/conversations/{conversation_id}",
        headers=headers,
    )

    assert saved.status_code == 200
    assert detail.json()["title"] == "A useful research question"
    assert [message["role"] for message in detail.json()["messages"]] == ["user"]
