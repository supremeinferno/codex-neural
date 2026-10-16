import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { API_URL } from "./config";
import { useEffect } from "react";

function Individual({ token, openedConversation, currentConversationId, onConversationChange }) {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [document, setDocument] = useState(null);
    const [error, setError] = useState("");

    const [question, setQuestion] = useState("");
    const [messages, setMessages] = useState([]);
    const [asking, setAsking] = useState(false);
    const [showPdf, setShowPdf] = useState(false);
    const [pdfUrl, setPdfUrl] = useState("");

    useEffect(() => {
        let objectUrl;
        if (!document?.document_id || !token) { setPdfUrl(""); return; }
        fetch(`${API_URL}/api/individual/${document.document_id}/file`, { headers: { Authorization: `Bearer ${token}` } })
            .then((response) => { if (!response.ok) throw new Error("Unable to open this PDF."); return response.blob(); })
            .then((blob) => { objectUrl = URL.createObjectURL(blob); setPdfUrl(objectUrl); })
            .catch(() => setError("Unable to open this PDF."));
        return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
    }, [document?.document_id, token]);

    useEffect(() => {
        if (!openedConversation) { setDocument(null); setMessages([]); setFile(null); setQuestion(""); return; }
        let cancelled = false;
        fetch(`${API_URL}/api/conversations/${openedConversation.id}`, { headers: { Authorization: `Bearer ${token}` } })
            .then((response) => { if (!response.ok) throw new Error("Unable to reopen this chat."); return response.json(); })
            .then((data) => {
                if (cancelled) return;
                if (data.kind !== "pdf" || !data.document) { setError("This saved PDF is no longer available."); return; }
                setDocument({ document_id: data.document_id, document_name: data.document.document_name, pages: data.document.pages });
                setMessages(data.messages || []);
                setError("");
            }).catch((e) => { if (!cancelled) setError(e.message); });
        return () => { cancelled = true; };
    }, [openedConversation, token]);

    const handleFileChange = (event) => {
        const selectedFile = event.target.files[0];

        setError("");
        setDocument(null);
        setMessages([]);
        setQuestion("");
        onConversationChange(null);

        if (!selectedFile) {
            setFile(null);
            return;
        }

        if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
            setError("Only PDF files are allowed.");
            setFile(null);
            return;
        }

        setFile(selectedFile);
    };

    const handleUpload = async () => {
        if (!file) {
            setError("Please select a PDF first.");
            return;
        }

        setUploading(true);
        setError("");
        setDocument(null);
        setMessages([]);
        onConversationChange(null);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await fetch(
                `${API_URL}/api/individual/upload`,
                {
                    method: "POST",
                    headers: { Authorization: `Bearer ${token}` },
                    body: formData,
                }
            );

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                setError(data.message || "Unable to process PDF.");
                return;
            }

            setDocument(data);
            const created = await fetch(`${API_URL}/api/conversations`, {
                method: "POST",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify({ kind: "pdf", title: data.document_name, document_id: data.document_id }),
            });
            if (!created.ok) throw new Error("PDF is ready, but its chat could not be saved.");
            const chat = await created.json();
            onConversationChange(chat.id);
        } catch (error) {
            console.error("PDF upload error:", error);

            setError(
                error instanceof TypeError
                    ? "Unable to connect to the server."
                    : "Something went wrong while processing the PDF."
            );
        } finally {
            setUploading(false);
        }
    };

    const handleAskQuestion = async () => {
        if (!question.trim() || !document || asking) {
            return;
        }

        const currentQuestion = question.trim();

        setQuestion("");
        setAsking(true);
        setError("");

        setMessages((previousMessages) => [
            ...previousMessages,
            { role: "user", content: currentQuestion },
        ]);

        try {
            // Prefer the current workspace ID. A new upload clears this ID while
            // an older openedConversation may still be present during transitions.
            let activeId = currentConversationId || openedConversation?.id;
            if (!activeId) {
                const created = await fetch(`${API_URL}/api/conversations`, {
                    method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                    body: JSON.stringify({ kind: "pdf", title: document.document_name, document_id: document.document_id }),
                });
                if (!created.ok) throw new Error("Unable to save this chat.");
                const chat = await created.json(); activeId = chat.id; onConversationChange(chat.id);
            }
            const userMessageSave = await fetch(`${API_URL}/api/conversations/${activeId}/messages`, {
                method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify({ role: "user", content: currentQuestion }),
            });
            if (!userMessageSave.ok) {
                throw new Error("Your question could not be saved. Please try again.");
            }
            setMessages((previousMessages) => [
                ...previousMessages,
                { role: "user", content: currentQuestion },
            ]);
            const response = await fetch(
                `${API_URL}/api/individual/chat`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        question: currentQuestion,
                        document_id: document.document_id,
                    }),
                }
            );

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                setError(
                    data.message ||
                    "Unable to answer the question."
                );
                return;
            }

            const assistantMessage = { role: "assistant", content: data.answer, sources: data.sources || [] };
            const assistantMessageSave = await fetch(`${API_URL}/api/conversations/${activeId}/messages`, {
                method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify({ role: "assistant", content: data.answer, sources: data.sources || [] }),
            });
            setMessages((previousMessages) => [...previousMessages, assistantMessage]);
            if (!assistantMessageSave.ok) {
                setError("The answer arrived, but it could not be saved to chat history.");
            }
        } catch (error) {
            console.error("Chat error:", error);
            setQuestion(currentQuestion);
            setError(
                error instanceof TypeError
                    ? "Unable to connect to the server."
                    : (error.message || "Something went wrong while getting the answer.")
            );
        } finally {
            setAsking(false);
        }
    };

    const handleKeyDown = (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();

            if (!asking) {
                handleAskQuestion();
            }
        }
    };

    const askSuggestedQuestion = (text) => {
        setQuestion(text);
    };


    return (
        <div className="individual-page">

            <div className="individual-header">
                <div>
                    <div className="individual-eyebrow">
                        <span></span>
                        INDIVIDUAL ANALYSIS
                    </div>

                    <h1>
                        Your document.
                        <br />
                        <span>Your intelligence.</span>
                    </h1>

                    <p>
                        Upload a PDF and interact with its contents
                        using document-aware AI.
                    </p>
                </div>
            </div>

            {!document && (
                <div className="individual-upload-card">

                    <div className="individual-upload-icon">
                        ↑
                    </div>

                    <h2>Upload PDF</h2>

                    <p>
                        Select a research paper, report, or any PDF
                        document you want to analyze.
                    </p>

                    <label className="individual-file-button">
                        {file ? "CHANGE PDF" : "SELECT PDF"}

                        <input
                            type="file"
                            accept=".pdf,application/pdf"
                            onChange={handleFileChange}
                            disabled={uploading}
                        />
                    </label>

                    {file && (
                        <div className="individual-file-name">
                            <span>PDF</span>
                            {file.name}
                        </div>
                    )}

                    {error && (
                        <div className="individual-error">
                            {error}
                        </div>
                    )}

                    <button
                        className="individual-analyze-button"
                        onClick={handleUpload}
                        disabled={!file || uploading}
                    >
                        {uploading
                            ? "PROCESSING..."
                            : "ANALYZE DOCUMENT"}

                        {!uploading && <span>↗</span>}
                    </button>

                </div>
            )}

            {document && (
                <div
                    className={`individual-workspace${
                        showPdf ? " individual-workspace-pdf-visible" : ""
                    }`}
                >

                    <aside className="individual-sidebar">

                        <div className="individual-sidebar-status">
                            <span></span>
                            DOCUMENT READY
                        </div>

                        <div className="individual-document-icon">
                            PDF
                        </div>

                        <h2>
                            {document.document_name}
                        </h2>

                        <div className="individual-document-stats">

                            <div>
                                <strong>
                                    {document.pages}
                                </strong>
                                <span>Pages</span>
                            </div>

                        </div>

                        <div className="individual-sidebar-divider"></div>

                        <div className="individual-suggested-title">
                            SUGGESTED QUESTIONS
                        </div>

                        <button
                            onClick={() =>
                                askSuggestedQuestion(
                                    "Summarize this document"
                                )
                            }
                        >
                            Summarize this document
                        </button>

                        <button
                            onClick={() =>
                                askSuggestedQuestion(
                                    "What is the main objective of this document?"
                                )
                            }
                        >
                            What is the main objective?
                        </button>

                        <button
                            onClick={() =>
                                askSuggestedQuestion(
                                    "What are the key findings?"
                                )
                            }
                        >
                            What are the key findings?
                        </button>

                        <button
                            onClick={() =>
                                askSuggestedQuestion(
                                    "Explain the methodology used."
                                )
                            }
                        >
                            Explain the methodology
                        </button>

                    </aside>

                    {showPdf && (
                        <section
                            id="individual-pdf-panel"
                            className="individual-pdf-panel"
                        >
                            <div className="individual-pdf-topbar">
                                <div>
                                    <div className="individual-eyebrow">
                                        <span></span>
                                        ORIGINAL DOCUMENT
                                    </div>
                                    <h2>PDF <span>viewer</span></h2>
                                </div>

                                <a
                                    className="individual-download-button"
                                    href={pdfUrl} download={document.document_name}
                                >
                                    DOWNLOAD ORIGINAL
                                    <span>↓</span>
                                </a>
                            </div>

                            <iframe
                                className="individual-pdf-frame"
                                src={`${pdfUrl}#page=1`}
                                title={`PDF viewer for ${document.document_name}`}
                            />
                        </section>
                    )}

                    <main className="individual-chat-workspace">

                        <div className="individual-chat-topbar">

                            <div>
                                <div className="individual-eyebrow">
                                    <span></span>
                                    CODEX DOCUMENT ASSISTANT
                                </div>

                                <h2>
                                    Ask your <span>document.</span>
                                </h2>
                            </div>

                            <div className="individual-chat-topbar-actions">
                                <button
                                    type="button"
                                    className="individual-pdf-toggle-button"
                                    aria-expanded={showPdf}
                                    aria-controls={
                                        showPdf
                                            ? "individual-pdf-panel"
                                            : undefined
                                    }
                                    onClick={() =>
                                        setShowPdf((visible) => !visible)
                                    }
                                >
                                    {showPdf ? "HIDE PDF" : "VIEW PDF"}
                                </button>

                                <div className="individual-chat-document">
                                    {document.pages} PAGES
                                </div>
                            </div>

                        </div>

                        <div className="individual-chat-messages">

                            {messages.length === 0 && (
                                <div className="individual-chat-empty">

                                    <div className="individual-chat-empty-icon">
                                        ✦
                                    </div>

                                    <h3>
                                        Start exploring your document
                                    </h3>

                                    <p>
                                        Ask a question, request a summary,
                                        or choose one of the suggested
                                        questions.
                                    </p>

                                </div>
                            )}

                            {messages.map((message, index) => (
                                <div
                                    key={index}
                                    className={`individual-message ${
                                        message.role === "user"
                                            ? "individual-message-user"
                                            : "individual-message-assistant"
                                    }`}
                                >

                                    <div className="individual-message-role">
                                        {message.role === "user"
                                            ? "YOU"
                                            : "CODEX"}
                                    </div>

                                    <div className="individual-message-content">

                                        {message.role === "assistant" ? (
                                            <ReactMarkdown
                                                remarkPlugins={[remarkGfm]}
                                            >
                                                {message.content}
                                            </ReactMarkdown>
                                        ) : (
                                            message.content
                                        )}

                                    </div>

                                    {message.sources &&
                                        message.sources.length > 0 && (
                                            <div className="individual-message-sources">
                                                {message.sources.map(
                                                    (source, sourceIndex) => (
                                                        <span
                                                            key={sourceIndex}
                                                        >
                                                            PAGE {source.page}
                                                        </span>
                                                    )
                                                )}
                                            </div>
                                        )}

                                </div>
                            ))}

                            {asking && (
                                <div className="individual-message individual-message-assistant">

                                    <div className="individual-message-role">
                                        CODEX
                                    </div>

                                    <div className="individual-thinking">
                                        ANALYZING DOCUMENT...
                                    </div>

                                </div>
                            )}

                        </div>

                        {error && (
                            <div className="individual-error">
                                {error}
                            </div>
                        )}

                        <div className="individual-chat-input-area">

                            <textarea
                                value={question}
                                onChange={(event) =>
                                    setQuestion(event.target.value)
                                }
                                onKeyDown={handleKeyDown}
                                placeholder="Ask anything about this document..."
                                rows={1}
                                disabled={asking}
                            />

                            <button
                                onClick={handleAskQuestion}
                                disabled={
                                    !question.trim() ||
                                    asking
                                }
                            >
                                {asking ? "..." : "↗"}
                            </button>

                        </div>

                        <div className="individual-chat-hint">
                            ENTER TO ASK · SHIFT + ENTER FOR NEW LINE
                        </div>

                    </main>

                </div>
            )}

        </div>
    );
}

export default Individual;
