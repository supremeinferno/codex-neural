import React from "react";

export default function ChatStarButton({ starred, loading, onClick }) {
  return (
    <button
      type="button"
      className={`conversation-star-button${starred ? " is-starred" : ""}`}
      onClick={onClick}
      disabled={loading}
      aria-pressed={starred}
      aria-label={starred ? "Remove star from this chat" : "Star this chat"}
      title={starred ? "Remove from starred chats" : "Add to starred chats"}
    >
      <span className="conversation-star-icon" aria-hidden="true">{starred ? "★" : "☆"}</span>
      <span>{loading ? "Saving…" : starred ? "Starred" : "Star chat"}</span>
    </button>
  );
}
