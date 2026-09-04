import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { API_URL } from "./config";

function Individual() {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [document, setDocument] = useState(null);
    const [error, setError] = useState("");

    const [question, setQuestion] = useState("");
    const [messages, setMessages] = useState([]);
    const [asking, setAsking] = useState(false);

    const handleFileChange = (event) => {
        const selectedFile = event.target.files[0];

        setError("");
        setDocument(null);
        setMessages([]);
        setQuestion("");

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

        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await fetch(
                `${API_URL}/api/individual/upload`,
                {
                    method: "POST",
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
            {
                role: "user",
                content: currentQuestion,
            },
        ]);

        try {
            const response = await fetch(
                `${API_URL}/api/individual/chat`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
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

            setMessages((previousMessages) => [
                ...previousMessages,
                {
                    role: "assistant",
                    content: data.answer,
                    sources: data.sources || [],
                },
            ]);
        } catch (error) {
            console.error("Chat error:", error);

            setError(
                error instanceof TypeError
                    ? "Unable to connect to the server."
                    : "Something went wrong while getting the answer."
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
                <div className="individual-workspace">

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

                            <div>
                                <strong>
                                    {document.chunks}
                                </strong>
                                <span>Chunks</span>
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

                            <div className="individual-chat-document">
                                {document.pages} PAGES
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