import React, { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { API_URL } from "./config";

const ACTIONS = [
    ["summary", "Summary"],
    ["objective", "Main Objective"],
    ["findings", "Key Findings"],
    ["methodology", "Methodology"],
];
const MAX_DOCUMENTS = 10;

function Individual() {
    const fileInput = useRef(null);
    const [documents, setDocuments] = useState([]);
    const [activeIds, setActiveIds] = useState([]);
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [statuses, setStatuses] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState("");
    const [question, setQuestion] = useState("");
    const [messages, setMessages] = useState([]);
    const [asking, setAsking] = useState(false);
    const [runningAction, setRunningAction] = useState("");
    const [showPdf, setShowPdf] = useState(false);
    const [viewerId, setViewerId] = useState("");

    const acceptFiles = (event) => {
        const files = Array.from(event.target.files || []);
        event.target.value = "";
        setError("");
        if (!files.length) return;
        const nonPdfs = files.filter((file) => !file.name.toLowerCase().endsWith(".pdf"));
        const pdfs = files.filter((file) => file.name.toLowerCase().endsWith(".pdf"));
        const slots = MAX_DOCUMENTS - documents.length - selectedFiles.length;
        if (nonPdfs.length) setError(`Only PDF files are allowed: ${nonPdfs.map((file) => file.name).join(", ")}`);
        if (pdfs.length > slots) {
            setError(`You can add up to ${MAX_DOCUMENTS} documents per session. ${Math.max(slots, 0)} slot(s) remain.`);
        }
        const accepted = pdfs.slice(0, Math.max(slots, 0));
        setSelectedFiles((previous) => [...previous, ...accepted]);
        if (!documents.length && fileInput.current && !fileInput.current.multiple) return;
    };

    const handleUpload = async () => {
        if (!selectedFiles.length || uploading) return;
        const batch = selectedFiles;
        setUploading(true);
        setError("");
        setStatuses(batch.map((file) => ({ name: file.name, status: "queued" })));
        try {
            const formData = new FormData();
            batch.forEach((file) => formData.append("files", file));
            setStatuses(batch.map((file) => ({ name: file.name, status: "processing" })));
            const response = await fetch(`${API_URL}/api/individual/upload`, { method: "POST", body: formData });
            if (!response.ok) throw new Error(`Server returned ${response.status}`);
            const data = await response.json();
            const results = data.results || [];
            const ready = [];
            const failed = [];
            results.forEach((result, index) => {
                const name = result.document_name || batch[index]?.name || "PDF";
                if (result.success && result.document_id) {
                    if (![...documents, ...ready].some((doc) => doc.document_id === result.document_id)) {
                        ready.push(result);
                    }
                } else failed.push(`${name}: ${result.message || "Unable to process PDF."}`);
            });
            setDocuments((previous) => {
                const merged = [...previous];
                ready.forEach((doc) => {
                    if (!merged.some((item) => item.document_id === doc.document_id)) merged.push(doc);
                });
                return merged.slice(0, MAX_DOCUMENTS);
            });
            setActiveIds((previous) => Array.from(new Set([...previous, ...ready.map((doc) => doc.document_id)])));
            if (!viewerId && ready[0]) setViewerId(ready[0].document_id);
            setStatuses(results.map((result, index) => ({ name: result.document_name || batch[index]?.name || "PDF", status: result.success ? "ready" : "failed", message: result.message })));
            setSelectedFiles([]);
            if (failed.length) setError(failed.join(" "));
            if (!results.length && data.message) setError(data.message);
        } catch (err) {
            console.error("PDF upload error:", err);
            setStatuses(batch.map((file) => ({ name: file.name, status: "failed", message: "Upload failed." })));
            setError(err instanceof TypeError ? "Unable to connect to the server." : "Something went wrong while processing the PDFs.");
        } finally {
            setUploading(false);
        }
    };

    const handleAskQuestion = async () => {
        if (!question.trim() || !activeIds.length || asking) return;
        const currentQuestion = question.trim();
        setQuestion("");
        setAsking(true);
        setRunningAction("");
        setError("");
        setMessages((previous) => [...previous, { role: "user", content: currentQuestion }]);
        try {
            const response = await fetch(`${API_URL}/api/individual/chat`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: currentQuestion, document_ids: activeIds }),
            });
            if (!response.ok) throw new Error(`Server returned ${response.status}`);
            const data = await response.json();
            if (!data.success) { setError(data.message || "Unable to answer the question."); return; }
            setMessages((previous) => [...previous, { role: "assistant", content: data.answer, sources: data.sources || [] }]);
        } catch (err) {
            console.error("Chat error:", err);
            setError(err instanceof TypeError ? "Unable to connect to the server." : "Something went wrong while getting the answer.");
        } finally { setAsking(false); }
    };

    const runAction = async (action, label) => {
        if (!activeIds.length || asking) return;
        const names = documents.filter((doc) => activeIds.includes(doc.document_id)).map((doc) => doc.document_name).join(", ");
        setAsking(true);
        setRunningAction(label);
        setError("");
        setMessages((previous) => [...previous, { role: "user", content: `${label.replace("this document", "")}: ${names}` }]);
        try {
            const response = await fetch(`${API_URL}/api/individual/action`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action, document_ids: activeIds }),
            });
            if (!response.ok) throw new Error(`Server returned ${response.status}`);
            const data = await response.json();
            if (!data.success) { setError(data.message || "Unable to analyze the selected documents."); return; }
            setMessages((previous) => [...previous, { role: "assistant", content: data.answer, sources: data.sources || [] }]);
        } catch (err) {
            console.error("Document action error:", err);
            setError(err instanceof TypeError ? "Unable to connect to the server." : "Something went wrong while analyzing the documents.");
        } finally { setAsking(false); setRunningAction(""); }
    };

    const handleKeyDown = (event) => {
        if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); if (!asking) handleAskQuestion(); }
    };
    const toggleDocument = (id) => setActiveIds((previous) => previous.includes(id) ? previous.filter((item) => item !== id) : [...previous, id]);
    const removeDocument = (id) => {
        setDocuments((previous) => previous.filter((doc) => doc.document_id !== id));
        setActiveIds((previous) => previous.filter((item) => item !== id));
        if (viewerId === id) setViewerId(documents.find((doc) => doc.document_id !== id)?.document_id || "");
    };
    const shownDocument = documents.find((doc) => doc.document_id === viewerId) || documents[0];
    const pdfFileUrl = shownDocument ? `${API_URL}/api/individual/${shownDocument.document_id}/file` : "";
    const selectedPages = documents.filter((doc) => activeIds.includes(doc.document_id)).reduce((sum, doc) => sum + (Number(doc.pages) || 0), 0);
    const controlsDisabled = asking || activeIds.length === 0;

    return (
        <div className="individual-page">
            <div className="individual-header"><div>
                <div className="individual-eyebrow"><span></span>INDIVIDUAL ANALYSIS</div>
                <h1>Your documents.<br /><span>Your intelligence.</span></h1>
                <p>Upload PDFs and interact with their contents using document-aware AI.</p>
            </div></div>

            {!documents.length && <div className="individual-upload-card">
                <div className="individual-upload-icon">↑</div>
                <h2>Upload PDFs</h2>
                <p>Select research papers, reports, or other PDF documents you want to analyze.</p>
                <label className="individual-file-button">SELECT PDFs
                    <input ref={fileInput} type="file" accept=".pdf,application/pdf" multiple onChange={acceptFiles} disabled={uploading} />
                </label>
                {selectedFiles.map((file, index) => <div className="individual-file-name" key={`${file.name}-${index}`}><span>PDF</span>{file.name}</div>)}
                {statuses.map((item, index) => <div className="individual-upload-status" key={`${item.name}-${index}`}>{item.name} · {item.status}{item.message && item.status === "failed" ? ` · ${item.message}` : ""}</div>)}
                {error && <div className="individual-error">{error}</div>}
                <button className="individual-analyze-button" onClick={handleUpload} disabled={!selectedFiles.length || uploading}>{uploading ? "PROCESSING..." : "ANALYZE DOCUMENTS"}{!uploading && <span>↗</span>}</button>
            </div>}

            {!!documents.length && <div className={`individual-workspace${showPdf ? " individual-workspace-pdf-visible" : ""}`}>
                <aside className="individual-sidebar">
                    <div className="individual-sidebar-status"><span></span>{documents.length} DOCUMENT{documents.length === 1 ? "" : "S"} READY</div>
                    <div className="individual-document-icon">PDF</div>
                    <h2>YOUR DOCUMENTS</h2>
                    <div className="individual-document-list">
                        {documents.map((doc) => <div className="individual-document-row" key={doc.document_id}>
                            <label className="individual-document-choice"><input type="checkbox" checked={activeIds.includes(doc.document_id)} onChange={() => toggleDocument(doc.document_id)} disabled={asking} /><span>{doc.document_name}</span></label>
                            <small>{doc.pages} pages</small>
                            <button type="button" className="individual-remove-document" onClick={() => removeDocument(doc.document_id)} disabled={asking} aria-label={`Remove ${doc.document_name}`}>×</button>
                        </div>)}
                    </div>
                    <div className="individual-chat-hint">{activeIds.length ? `${activeIds.length} DOCUMENT(S) SELECTED` : "SELECT AT LEAST ONE DOCUMENT"}</div>
                    <button type="button" className="individual-add-more" onClick={() => fileInput.current?.click()} disabled={uploading || documents.length + selectedFiles.length >= MAX_DOCUMENTS}>ADD MORE PDFs</button>
                    <input ref={fileInput} className="individual-hidden-input" type="file" accept=".pdf,application/pdf" multiple onChange={acceptFiles} disabled={uploading || documents.length >= MAX_DOCUMENTS} />
                    {selectedFiles.length > 0 && <>
                        {selectedFiles.map((file, index) => <div className="individual-upload-status" key={`${file.name}-${index}`}>{file.name} · queued</div>)}
                        <button type="button" className="individual-add-more" onClick={handleUpload} disabled={uploading}>{uploading ? "PROCESSING..." : "UPLOAD QUEUED PDFs"}</button>
                    </>}
                    {statuses.map((item, index) => <div className="individual-upload-status" key={`${item.name}-${index}`}>{item.name} · {item.status}{item.message && item.status === "failed" ? ` · ${item.message}` : ""}</div>)}
                    <div className="individual-sidebar-divider"></div>
                    <div className="individual-suggested-title">QUICK ACTIONS</div>
                    {ACTIONS.map(([action, label]) => <button key={action} type="button" onClick={() => runAction(action, label)} disabled={controlsDisabled}>{label}</button>)}
                </aside>

                {showPdf && <section id="individual-pdf-panel" className="individual-pdf-panel">
                    <div className="individual-pdf-topbar"><div><div className="individual-eyebrow"><span></span>ORIGINAL DOCUMENT</div><h2>PDF <span>viewer</span></h2></div>
                        <a className="individual-download-button" href={`${pdfFileUrl}?download=true`}>DOWNLOAD ORIGINAL <span>↓</span></a>
                    </div>
                    {documents.length > 1 && <select className="individual-viewer-select" value={shownDocument?.document_id || ""} onChange={(event) => setViewerId(event.target.value)} aria-label="Choose PDF to view">{documents.map((doc) => <option key={doc.document_id} value={doc.document_id}>{doc.document_name}</option>)}</select>}
                    {shownDocument && <iframe className="individual-pdf-frame" src={`${pdfFileUrl}#page=1`} title={`PDF viewer for ${shownDocument.document_name}`} />}
                </section>}

                <main className="individual-chat-workspace">
                    <div className="individual-chat-topbar"><div><div className="individual-eyebrow"><span></span>CODEX DOCUMENT ASSISTANT</div><h2>Ask your <span>documents.</span></h2></div>
                        <div className="individual-chat-topbar-actions"><button type="button" className="individual-pdf-toggle-button" aria-expanded={showPdf} aria-controls={showPdf ? "individual-pdf-panel" : undefined} onClick={() => setShowPdf((visible) => !visible)}>{showPdf ? "HIDE PDF" : "VIEW PDF"}</button><div className="individual-chat-document">{selectedPages} PAGES · {activeIds.length} DOCUMENTS</div></div>
                    </div>
                    <div className="individual-chat-messages">
                        {!messages.length && <div className="individual-chat-empty"><div className="individual-chat-empty-icon">✦</div><h3>Start exploring your documents</h3><p>Ask a question or choose a quick action. Responses use selected documents only.</p></div>}
                        {messages.map((message, index) => <div key={index} className={`individual-message ${message.role === "user" ? "individual-message-user" : "individual-message-assistant"}`}>
                            <div className="individual-message-role">{message.role === "user" ? "YOU" : "CODEX"}</div>
                            <div className="individual-message-content">{message.role === "assistant" ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown> : message.content}</div>
                            {message.sources?.length > 0 && <div className="individual-message-sources">{message.sources.map((source, sourceIndex) => <span key={`${source.document_id}-${source.page}-${sourceIndex}`}>{(source.document_name || "Document").slice(0, 20)} · PAGE {source.page}</span>)}</div>}
                        </div>)}
                        {asking && <div className="individual-message individual-message-assistant"><div className="individual-message-role">CODEX</div><div className="individual-thinking">{runningAction ? `${runningAction.toUpperCase()} · ANALYZING DOCUMENT...` : "ANALYZING DOCUMENT..."}</div></div>}
                    </div>
                    {error && <div className="individual-error">{error}</div>}
                    {!activeIds.length && <div className="individual-chat-hint">Select at least one document to ask questions or run actions.</div>}
                    <div className="individual-chat-input-area"><textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={handleKeyDown} placeholder="Ask anything about the selected documents..." rows={1} disabled={controlsDisabled} /><button onClick={handleAskQuestion} disabled={!question.trim() || controlsDisabled}>{asking ? "..." : "↗"}</button></div>
                    <div className="individual-chat-hint">ENTER TO ASK · SHIFT + ENTER FOR NEW LINE</div>
                </main>
            </div>}
        </div>
    );
}

export default Individual;


