import React, { useEffect } from "react";

export default function NavigationDrawer({ open, onClose, onHistory, onSignOut }) {
  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  return <>
    <button className={`drawer-scrim ${open ? "visible" : ""}`} type="button" aria-label="Close navigation menu" onClick={onClose} tabIndex={open ? 0 : -1} />
    <aside className={`navigation-drawer ${open ? "open" : ""}`} aria-label="Main navigation" aria-hidden={!open} inert={!open}>
      <div className="drawer-header"><div className="drawer-brand">CODEX<span>.</span></div><button type="button" className="drawer-close" onClick={onClose} aria-label="Close menu">×</button></div>
      <div className="drawer-section-label">WORKSPACE</div>
      <nav className="drawer-nav">
        <button type="button" className="drawer-link" onClick={onHistory}><span className="drawer-link-icon">◷</span><span>History</span><span className="drawer-link-arrow">›</span></button>
        <button type="button" className="drawer-link disabled" disabled title="Coming later"><span className="drawer-link-icon">☆</span><span>Starred chats</span><small>SOON</small></button>
        <button type="button" className="drawer-link disabled" disabled title="Coming later"><span className="drawer-link-icon">⚙</span><span>Settings</span><small>SOON</small></button>
      </nav>
      <div className="drawer-footer"><div className="drawer-divider" /><button type="button" className="drawer-link signout-link" onClick={onSignOut}><span className="drawer-link-icon">↪</span><span>Sign out</span></button><div className="drawer-footer-note">NEXUS RESEARCH WORKSPACE</div></div>
    </aside>
  </>;
}
