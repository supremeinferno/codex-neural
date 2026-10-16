import React, { useEffect, useState } from "react";
import { API_URL } from "./config";

export default function NavigationDrawer({ open, onClose, token, version, currentId, email, onNewChat, onSelectChat, onHistory, onSignOut }) {
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  // Reload the chat list every time the sidebar opens or a chat is saved
  useEffect(() => {
    if (!open || !token) return undefined;
    let cancelled = false;
    setLoading(true);
    fetch(`${API_URL}/api/conversations`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => { if (!response.ok) throw new Error("Unable to load chats."); return response.json(); })
      .then((data) => { if (!cancelled) { setChats(data.conversations || []); setError(""); } })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [open, token, version]);

  return <>
    <button className={`drawer-scrim ${open ? "visible" : ""}`} type="button" aria-label="Close navigation menu" onClick={onClose} tabIndex={open ? 0 : -1} />
    <aside className={`navigation-drawer ${open ? "open" : ""}`} aria-label="Main navigation" aria-hidden={!open} inert={!open}>
      <div className="drawer-header"><div className="drawer-brand">CODEX<span>.</span></div><button type="button" className="drawer-close" onClick={onClose} aria-label="Close menu">×</button></div>

      <button type="button" className="drawer-new-chat" onClick={onNewChat}><span>＋</span> New chat</button>

      <div className="drawer-section-label">RECENT CHATS</div>
      <div className="drawer-chat-list">
        {loading && !chats.length ? <div className="drawer-chat-empty">Loading…</div>
          : error ? <div className="drawer-chat-empty">{error}</div>
          : !chats.length ? <div className="drawer-chat-empty">No chats yet</div>
          : chats.map((chat) => (
            <button type="button" key={chat.id} className={`drawer-chat ${chat.id === currentId ? "active" : ""}`} onClick={() => onSelectChat(chat)} title={chat.title}>
              <span className="drawer-chat-icon">{chat.kind === "pdf" ? "PDF" : "✦"}</span>
              <span className="drawer-chat-title">{chat.title}</span>
            </button>
          ))}
      </div>
      <button type="button" className="drawer-view-all" onClick={onHistory}>View all &amp; manage chats <span>›</span></button>

      <div className="drawer-footer">
        <div className="drawer-divider" />
        <button type="button" className="drawer-link disabled" disabled title="Coming later"><span className="drawer-link-icon">⚙</span><span>Settings</span><small>SOON</small></button>
        <button type="button" className="drawer-link signout-link" onClick={onSignOut}><span className="drawer-link-icon">↪</span><span>Sign out</span></button>
        {email && <div className="drawer-user" title={email}><span className="drawer-avatar">{email[0].toUpperCase()}</span><span className="drawer-email">{email}</span></div>}
      </div>
    </aside>
  </>;
}
