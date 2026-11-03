import React, { useEffect, useState } from "react";
import { API_URL } from "./config";

export default function ChatHistory({ token, version, currentId, onSelect, onNew }) {
  const [chats, setChats] = useState([]);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
  const refresh = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/conversations`, { headers });
      if (!response.ok) throw new Error("Unable to load your saved chats.");
      const data = await response.json(); setChats(data.conversations || []); setError("");
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { refresh(); }, [token, version]);
  const rename = async (chat) => {
    const next = title.trim(); if (!next) return;
    const response = await fetch(`${API_URL}/api/conversations/${chat.id}`, { method: "PATCH", headers, body: JSON.stringify({ title: next }) });
    if (response.ok) { setEditing(null); refresh(); }
  };
  const remove = async (chat) => {
    if (!window.confirm(`Delete “${chat.title}”? This cannot be undone.`)) return;
    const response = await fetch(`${API_URL}/api/conversations/${chat.id}`, { method: "DELETE", headers });
    if (response.ok) { setChats((items) => items.filter((item) => item.id !== chat.id)); if (currentId === chat.id) onNew(); }
    else setError("Unable to delete that chat.");
  };
  return <main className="history-page">
    <div className="history-page-heading">
      <div><div className="eyebrow"><span></span> YOUR WORKSPACE</div><h1>Chat <span>history.</span></h1><p>Pick up where you left off across research and document chats.</p></div>
      <button className="history-new-chat" type="button" onClick={onNew}><span>＋</span> NEW CHAT</button>
    </div>
    {error && <div className="history-page-error">{error}</div>}
    {loading ? <div className="history-page-empty">Loading your chats…</div> : !chats.length ? <div className="history-page-empty"><span>✦</span><h2>No saved chats yet</h2><p>Your research and PDF conversations will appear here.</p><button type="button" onClick={onNew}>START A CHAT <span>↗</span></button></div> :
      <section className="history-chat-list" aria-label="Saved chats">{chats.map((chat) => <article className="history-chat-card" key={chat.id}>
        {editing === chat.id ? <form className="history-rename-form" onSubmit={(event) => { event.preventDefault(); rename(chat); }}><input aria-label="Chat name" value={title} onChange={(event) => setTitle(event.target.value)} autoFocus /><button type="submit">SAVE</button><button type="button" onClick={() => setEditing(null)}>CANCEL</button></form> : <>
          <button className="history-chat-main" type="button" onClick={() => onSelect(chat)}>
            <span className="history-chat-icon">{chat.kind === "pdf" ? "PDF" : "✦"}</span>
            <span className="history-chat-copy"><strong>{chat.title}</strong><small>{chat.kind === "pdf" ? "DOCUMENT CHAT" : "RESEARCH CHAT"} <span>·</span> {new Date(chat.updated_at).toLocaleDateString()}</small></span>
            <span className="history-chat-arrow">↗</span>
          </button>
          <div className="history-chat-actions"><button type="button" aria-label={`Rename ${chat.title}`} onClick={() => { setEditing(chat.id); setTitle(chat.title); }}>RENAME</button><button type="button" aria-label={`Delete ${chat.title}`} onClick={() => remove(chat)}>DELETE</button></div>
        </>}
      </article>)}</section>}
  </main>;
}
