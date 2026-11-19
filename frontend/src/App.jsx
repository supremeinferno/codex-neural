import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import "./index.css";

import ForgotPassword from "./Forgotpassword.jsx";
import Dashboard from "./Dashboard";
import Login from "./login.jsx";
import Register from "./register.jsx";
import Individual from "./Individual.jsx";
import ChatHistory from "./ChatHistory.jsx";
import NavigationDrawer from "./NavigationDrawer.jsx";
import ChatStarButton from "./ChatStarButton.jsx";
import "./styles/navigation.css";

import { API_URL } from "./config";

const ADMIN_EMAIL = "codexproject9@gmail.com";

function App() {

  const [authPage, setAuthPage] = useState("login");

  // -------------------------------------------------------
  // SESSION AUTHENTICATION
  // sessionStorage survives refresh but is cleared when
  // the browser tab/session is closed.
  // -------------------------------------------------------

  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    try {
      return !!sessionStorage.getItem("codex_user");
    } catch {
      return false;
    }
  });

  const [token, setToken] = useState(() => sessionStorage.getItem("codex_token") || "");
  const [historyVersion, setHistoryVersion] = useState(0);
  const [openedConversation, setOpenedConversation] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activePage, setActivePage] = useState("workspace");
  const [conversationId, setConversationId] = useState(null);
  const [conversationStarred, setConversationStarred] = useState(false);
  const [starUpdating, setStarUpdating] = useState(false);
  const [starError, setStarError] = useState("");

  const [user, setUser] = useState(() => {
    try {
      const stored = sessionStorage.getItem("codex_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  // =======================================================
  // LOGIN
  // =======================================================

  const handleLogin = (loggedInUser, sessionToken) => {
    setToken(sessionToken);
    sessionStorage.setItem("codex_token", sessionToken);
    setUser(loggedInUser);

    setIsLoggedIn(true);

    setAuthPage("login");

    setActiveTab("nexus");

    try {
      sessionStorage.setItem(
        "codex_user",
        JSON.stringify(loggedInUser)
      );

      sessionStorage.setItem(
        "codex_active_tab",
        "nexus"
      );
    } catch (err) {
      console.error("Failed to persist session:", err);
    }
  };

  // =======================================================
  // LOGOUT
  // =======================================================

  const handleLogout = () => {
    setUser(null);

    setIsLoggedIn(false);

    setAuthPage("login");

    setActiveTab("nexus");
    setActivePage("workspace");
    setDrawerOpen(false);

    const oldToken = sessionStorage.getItem("codex_token");
    if (oldToken) fetch(`${API_URL}/api/logout`, { method: "POST", headers: { Authorization: `Bearer ${oldToken}` } }).catch(() => {});
    setToken("");
    setConversationId(null);
    setOpenedConversation(null);
    setConversationStarred(false);
    setStarError("");
    setPromptCorrection("");
    setFollowUpQuestion("");
    setTopic("");

    setReport("");
    setConversationId(null);
    setOpenedConversation(null);

    setError("");

    try {
      sessionStorage.removeItem("codex_user");
      sessionStorage.removeItem("codex_token");
      sessionStorage.removeItem("codex_active_tab");
    } catch (err) {
      console.error("Failed to clear session:", err);
    }
  };

  useEffect(() => {
    if (!user) return;
    if (!token) { handleLogout(); return; }
    let cancelled = false;
    fetch(`${API_URL}/api/session`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => { if (!response.ok && !cancelled) handleLogout(); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  // =======================================================
  // ADMIN CHECK
  // =======================================================

  const isAdmin =
    user?.email?.trim().toLowerCase() ===
    ADMIN_EMAIL.trim().toLowerCase();

  const handleToggleConversationStar = async () => {
    if (!conversationId || starUpdating) return;
    const nextStarred = !conversationStarred;
    setStarUpdating(true);
    setStarError("");
    try {
      const response = await fetch(
        `${API_URL}/api/conversations/${conversationId}/star`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ is_starred: nextStarred }),
        }
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Unable to update starred chats.");
      setConversationStarred(Boolean(data.is_starred));
      setOpenedConversation((current) =>
        current?.id === conversationId
          ? { ...current, is_starred: Boolean(data.is_starred) }
          : current
      );
      setHistoryVersion((value) => value + 1);
    } catch (error) {
      setStarError(error.message || "Unable to update starred chats.");
    } finally {
      setStarUpdating(false);
    }
  };

  // =======================================================
  // MAIN TABS
  // =======================================================

  const [activeTab, setActiveTab] = useState(() => {
    try {
      return (
        sessionStorage.getItem("codex_active_tab") ||
        "nexus"
      );
    } catch {
      return "nexus";
    }
  });

  useEffect(() => {
    try {
      sessionStorage.setItem(
        "codex_active_tab",
        activeTab
      );
    } catch (err) {
      console.error(
        "Failed to persist active tab:",
        err
      );
    }
  }, [activeTab]);

  // =======================================================
  // PROTECT ADMIN DASHBOARD
  // =======================================================

  useEffect(() => {
    if (activeTab === "dashboard" && !isAdmin) {
      setActiveTab("nexus");
    }
  }, [activeTab, isAdmin]);

  // =======================================================
  // NEXUS RESEARCH
  // =======================================================

  const [topic, setTopic] = useState("");
  const [followUpQuestion, setFollowUpQuestion] = useState("");

  const [report, setReport] = useState("");
  const [responseMode, setResponseMode] = useState("research");
  const [promptCorrection, setPromptCorrection] = useState("");

  const [wordExporting, setWordExporting] = useState(false);
  const [exportError, setExportError] = useState("");

  const exportWord = async () => {
    if (!conversationId || wordExporting) return;
    setWordExporting(true);
    setExportError("");
    try {
      const response = await fetch(
        API_URL + "/api/conversations/" + conversationId + "/export/word",
        { headers: { Authorization: "Bearer " + token } },
      );
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Unable to export this report.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const safeName = (topic || "Research_Report").replace(/[^a-z0-9._-]+/gi, "_").replace(/^[_\.]+|[_\.]+$/g, "").slice(0, 80) || "Research_Report";
      link.href = url;
      link.download = safeName + ".docx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setExportError(error.message || "Unable to export this report.");
    } finally {
      setWordExporting(false);
    }
  };

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  const [activeStage, setActiveStage] = useState(0);

  const stages = [
    {
      number: "01",
      title: "Research",
      description: "Searching the web",
    },

    {
      number: "02",
      title: "Read",
      description: "Reading sources",
    },

    {
      number: "03",
      title: "Write",
      description: "Synthesizing findings",
    },

    {
      number: "04",
      title: "Critique",
      description: "Evaluating the report",
    },
  ];

  // =======================================================
  // RESEARCH PROGRESS
  // =======================================================

  useEffect(() => {
    if (!loading) return;

    setActiveStage(0);

    const interval = setInterval(() => {
      setActiveStage((current) => {
        if (current < stages.length - 1) {
          return current + 1;
        }

        return current;
      });
    }, 4500);

    return () => clearInterval(interval);
  }, [loading]);

  // =======================================================
  // RUN RESEARCH
  // =======================================================

  const runResearch = async (promptOverride = null) => {
    const researchTopic = (promptOverride ?? topic).trim();
    if (!researchTopic || loading) return;
    setLoading(true);
    setError("");
    setStarError("");
    setReport("");
    setResponseMode("research");
    setPromptCorrection("");
    setActiveStage(0);
    let timeoutId;

    try {
      let currentConversationId = conversationId;
      if (!currentConversationId) {
        const createdResponse = await fetch(`${API_URL}/api/conversations`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ kind: "research", title: researchTopic }),
        });
        if (!createdResponse.ok) throw new Error("Unable to start a saved research chat.");
        const created = await createdResponse.json();
        currentConversationId = created.id;
        setConversationId(created.id);
        setOpenedConversation(null);
        setConversationStarred(false);
        setHistoryVersion((value) => value + 1);
      }

      const userMessageResponse = await fetch(
        `${API_URL}/api/conversations/${currentConversationId}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ role: "user", content: researchTopic }),
        }
      );
      if (!userMessageResponse.ok) throw new Error("Your research question could not be saved.");
      setHistoryVersion((value) => value + 1);

      const controller = new AbortController();
      timeoutId = setTimeout(() => controller.abort(), 180000);
      const response = await fetch(`${API_URL}/api/research`, {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ topic: researchTopic, conversation_id: currentConversationId }),
      });
      if (!response.ok) {
        let detail = "";
        try { detail = (await response.json()).detail; } catch { /* non-JSON response */ }
        throw new Error(detail || `Server returned ${response.status}`);
      }
      const data = await response.json();
      const responseText = data.report || data.answer;
      if (!responseText) throw new Error("The assistant returned an empty response.");

      const routedMode = data.mode || (data.report ? "research" : "general");
      const correctedPrompt = typeof data.interpreted_prompt === "string" ? data.interpreted_prompt.trim() : "";
      const wasCorrected = correctedPrompt && correctedPrompt.toLocaleLowerCase() !== researchTopic.toLocaleLowerCase();
      setResponseMode(routedMode);
      setPromptCorrection(wasCorrected ? `I interpreted “${researchTopic}” as “${correctedPrompt}”.` : "");
      setReport(responseText);
      const assistantMessageResponse = await fetch(
        `${API_URL}/api/conversations/${currentConversationId}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            role: "assistant",
            content: responseText,
            sources: routedMode === "research" && !wasCorrected
              ? []
              : [{
                  type: "app_metadata",
                  response_mode: routedMode,
                  ...(wasCorrected ? { corrected_prompt: correctedPrompt } : {}),
                }],
          }),
        }
      );
      if (!assistantMessageResponse.ok) {
        setError("The report is ready, but it could not be saved to chat history.");
      }
      setHistoryVersion((value) => value + 1);
      setActiveStage(stages.length - 1);
    } catch (err) {
      console.error("Research error:", err);
      if (err.name === "AbortError") {
        setError("The request timed out. The backend may have stopped or be rate limited. Please try again.");
      } else if (err instanceof TypeError && err.message === "Failed to fetch") {
        setError("Backend server is not connected. Please start the FastAPI server and try again.");
      } else {
        setError(err.message || "Something went wrong. Please try again.");
      }
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
      setLoading(false);
    }
  };

  const submitFollowUp = (event) => {
    event.preventDefault();
    const message = followUpQuestion.trim();
    if (!message || loading) return;
    setFollowUpQuestion("");
    setTopic(message);
    runResearch(message);
  };

  // KEYBOARD HANDLER
  // =======================================================

  const handleKeyDown = (event) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      runResearch();
    }
  };

  // =======================================================
  // RESET RESEARCH
  // =======================================================

  const resetResearch = () => {
    setTopic("");

    setReport("");
    setConversationId(null);
    setOpenedConversation(null);
    setConversationStarred(false);
    setStarError("");
    setPromptCorrection("");
    setFollowUpQuestion("");

    setError("");

    setLoading(false);

    setActiveStage(0);

    setActiveTab("nexus");
  };

  // =======================================================
  // AUTH SCREEN
  // =======================================================

  if (!isLoggedIn) {
    // -----------------------------------------------------
    // REGISTER
    // -----------------------------------------------------

    if (authPage === "register") {
      return (
        <Register
          onBackToLogin={() => {
            setAuthPage("login");
          }}
        />
      );
    }

    // -----------------------------------------------------
    // FORGOT PASSWORD
    // -----------------------------------------------------

    if (authPage === "forgot-password") {
      return (
        <ForgotPassword
          onBack={() => {
            setAuthPage("login");
          }}
        />
      );
    }

    // -----------------------------------------------------
    // LOGIN
    // -----------------------------------------------------

    return (
      <Login
        onLogin={handleLogin}
        onCreateAccount={() => {
          setAuthPage("register");
        }}
        onForgotPassword={() => {
          setAuthPage("forgot-password");
        }}
      />
    );
  }

  // =======================================================
  // SHARED BACKGROUND
  // =======================================================

  const Background = () => (
    <>
      <div className="ambient ambient-one"></div>

      <div className="ambient ambient-two"></div>

      <div className="stars">
        {Array.from({ length: 28 }).map(
          (_, index) => (
            <span
              key={index}
              className={`star star-${index % 5}`}
            ></span>
          )
        )}
      </div>
    </>
  );

  // =======================================================
  // SHARED NAVBAR
  // =======================================================

  const Navbar = () => (
    <>
    <nav className="navbar">
      <button className="menu-toggle" type="button" aria-label="Open navigation menu" aria-expanded={drawerOpen} onClick={() => setDrawerOpen(true)}>☰</button>
      {/* LOGO */}
      <div className="logo">
        CODEX.
      </div>

      {/* MODE SWITCHER */}

      <div className="mode-tabs">

        {/* NEXUS */}

        <button
          type="button"
          className={`mode-tab ${
            activeTab === "nexus"
              ? "active"
              : ""
          }`}
          onClick={() => {
            setActivePage("workspace");
            setConversationId(null); setOpenedConversation(null);
            setConversationStarred(false); setStarError("");
            setActiveTab("nexus");
          }}
        >
          NEXUS
        </button>

        {/* INDIVIDUAL */}

        <button
          type="button"
          className={`mode-tab ${
            activeTab === "individual"
              ? "active"
              : ""
          }`}
          onClick={() => {
            setActivePage("workspace");
            setConversationId(null); setOpenedConversation(null);
            setConversationStarred(false); setStarError("");
            setActiveTab("individual");
          }}
        >
          INDIVIDUAL
        </button>

        {/* DASHBOARD - ADMIN ONLY */}

        {isAdmin && (
          <button
            type="button"
            className={`mode-tab admin-tab ${
              activeTab === "dashboard"
                ? "active"
                : ""
            }`}
            onClick={() => {
              if (isAdmin) {
                setActivePage("workspace");
                setActiveTab("dashboard");
              }
            }}
          >
            DASHBOARD
          </button>
        )}
      </div>

      {/* RIGHT SIDE */}

      <div
        className="navbar-right"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "20px",
        }}
      >

        {/* STATUS */}

        <div className="status">
          <span className="status-dot"></span>
          RESEARCH ENGINE ONLINE
        </div>

      </div>
    </nav>
    <NavigationDrawer
      open={drawerOpen}
      onClose={() => setDrawerOpen(false)}
      onHistory={() => { setDrawerOpen(false); setActivePage("history"); }}
      onStarred={() => { setDrawerOpen(false); setActivePage("starred"); }}
      onSignOut={handleLogout}
    />
    </>
  );

  const startNewChat = () => {
    setOpenedConversation(null);
    setConversationId(null);
    setConversationStarred(false);
    setStarError("");
    setTopic(""); setReport(""); setResponseMode("research"); setPromptCorrection(""); setFollowUpQuestion(""); setError(""); setLoading(false);
    setActiveTab("nexus"); setActivePage("workspace");
  };

  const openSavedChat = async (chat) => {
    const response = await fetch(`${API_URL}/api/conversations/${chat.id}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) return;
    const data = await response.json();
    setOpenedConversation(data); setConversationId(data.id); setConversationStarred(Boolean(data.is_starred)); setStarError(""); setActivePage("workspace");
    if (data.kind === "pdf") {
      setActiveTab("individual");
    } else {
      const firstQuestion = data.messages.find((message) => message.role === "user");
      const lastAnswer = [...data.messages].reverse().find((message) => message.role === "assistant");
      const answerMetadata = lastAnswer?.sources?.find((item) => item?.type === "app_metadata");
      const savedMode = answerMetadata?.response_mode;
      const correctedPrompt = answerMetadata?.corrected_prompt;
      setTopic(firstQuestion?.content || data.title); setReport(lastAnswer?.content || ""); setResponseMode(savedMode || "research");
      setPromptCorrection(correctedPrompt ? `I interpreted “${firstQuestion?.content || data.title}” as “${correctedPrompt}”.` : "");
      setActiveTab("nexus");
    }
  };

  if (activePage === "history" || activePage === "starred") {
    return (
      <div className="app">
        <Background />
        <Navbar />
        <ChatHistory token={token} version={historyVersion} currentId={conversationId} onNew={startNewChat} onSelect={openSavedChat} starredOnly={activePage === "starred"} />
      </div>
    );
  }

  // =======================================================
  // INDIVIDUAL PDF ANALYZER
  // =======================================================

  if (activeTab === "individual") {
    return (
      <div className="app">
        <Background />
        <Navbar />
        <Individual
          token={token}
          openedConversation={openedConversation}
          currentConversationId={conversationId}
          conversationStarred={conversationStarred}
          starUpdating={starUpdating}
          starError={starError}
          onToggleStar={handleToggleConversationStar}
          onConversationChange={(id) => {
            setConversationId(id);
            setConversationStarred(false);
            setStarError("");
            if (id === null) setOpenedConversation(null);
            setHistoryVersion((value) => value + 1);
          }}
        />
      </div>
    );
  }

  // =======================================================
  // ADMIN DASHBOARD
  // =======================================================

  if (activeTab === "dashboard") {

    // Safety check
    // Non-admin can NEVER access dashboard.

    if (!isAdmin) {
      return null;
    }

    return (
      <div className="app">
        <Background />

        <Navbar />

        <Dashboard user={user} />
      </div>
    );
  }

  // =======================================================
  // NEXUS MAIN PAGE
  // =======================================================

  return (
    <div className="app">
      <Background />

      <Navbar />

      {/* =================================================
          LANDING / LOADING
      ================================================= */}

      {!report && (
        <main className="main-stage">

          <section className="hero">

            {/* EYEBROW */}

            <div className="eyebrow">
              <span></span>

              NEXUS RESEARCH ASSISTANT
            </div>

            {/* HERO TITLE */}

            <h1>
              Research,
              <br />

              <span>
                without the noise.
              </span>
            </h1>

            {/* SUBTITLE */}

            <p className="subtitle">
              Ask anything. Get a direct answer,
              or a researched report when your
              question calls for it.
            </p>

            {/* =================================================
                ORBITAL SYSTEM
            ================================================= */}

            <div
              className={`orbital-system ${
                loading
                  ? "is-loading"
                  : ""
              }`}
            >

              <div className="orbit orbit-large"></div>

              <div className="orbit orbit-medium"></div>

              <div className="orbit orbit-small"></div>

              <div className="orbital-glow"></div>

              <div className="core">
                <div className="core-inner"></div>
              </div>

              <div className="orbit-dot dot-one"></div>

              <div className="orbit-dot dot-two"></div>

              <div className="orbit-dot dot-three"></div>
            </div>

            {/* =================================================
                RESEARCH INPUT
            ================================================= */}

            {!loading && (
              <>
                <div className="research-box">

                  <textarea
                    value={topic}
                    onChange={(event) =>
                      setTopic(
                        event.target.value
                      )
                    }
                    onKeyDown={handleKeyDown}
                    placeholder="Ask a question or start a conversation…"
                    rows="2"
                  />

                  <button
                    type="button"
                    onClick={runResearch}
                    disabled={!topic.trim()}
                  >
                    SEND

                    <span>↗</span>
                  </button>
                </div>

                <div className="shortcut">
                  <span>⌘</span>

                  ENTER TO SEND
                </div>
              </>
            )}

            {/* =================================================
                RESEARCH LOADING
            ================================================= */}

            {loading && (
              <section className="research-progress">

                <div className="progress-header">

                  <div>

                    <span className="progress-label">PREPARING A RESPONSE</span>

                    <h2>
                      Thinking

                      <span>.</span>

                      <span>.</span>

                      <span>.</span>
                    </h2>

                  </div>

                  <div className="progress-topic">
                    "{topic}"
                  </div>

                </div>

                <div className="agent-pipeline" style={{ display: "none" }} aria-hidden="true">

                  {stages.map(
                    (stage, index) => {

                      const isActive =
                        index === activeStage;

                      const isDone =
                        index < activeStage;

                      return (
                        <React.Fragment
                          key={stage.number}
                        >

                          <div
                            className={`agent-stage ${
                              isActive
                                ? "active"
                                : ""
                            } ${
                              isDone
                                ? "done"
                                : ""
                            }`}
                          >

                            <div className="stage-number">
                              {isDone
                                ? "✓"
                                : stage.number}
                            </div>

                            <div className="stage-info">

                              <strong>
                                {stage.title}
                              </strong>

                              <small>
                                {isActive
                                  ? stage.description
                                  : isDone
                                  ? "Complete"
                                  : "Waiting"}
                              </small>

                            </div>

                            {isActive && (
                              <div className="stage-pulse"></div>
                            )}

                          </div>

                          {index <
                            stages.length - 1 && (
                            <div
                              className={`pipeline-connector ${
                                index <
                                activeStage
                                  ? "complete"
                                  : ""
                              }`}
                            ></div>
                          )}

                        </React.Fragment>
                      );
                    }
                  )}

                </div>

                <p className="progress-note">
                  Nexus is gathering evidence
                  before generating your report.
                  This may take a moment.
                </p>

              </section>
            )}

            {/* =================================================
                ERROR
            ================================================= */}

            {error && (
              <div className="error-box">

                <strong>
                  Something went wrong.
                </strong>

                <span>
                  {error}
                </span>

              </div>
            )}

          </section>
        </main>
      )}

      {/* =================================================
          REPORT
      ================================================= */}

      {report && !loading && (
        <main className="report-page">

          {/* REPORT HEADER */}

          <section className="report-header">

            <div className="report-heading">

              <div className="eyebrow">

                <span></span>

                {responseMode === "research" ? "RESEARCH OUTPUT" : responseMode === "clarify" ? "QUICK QUESTION" : "CHAT RESPONSE"}

              </div>

              <div className="report-title-row">
                <h1>{topic}</h1>
                {conversationId && (
                  <div className="star-control-wrap">
                    <ChatStarButton starred={conversationStarred} loading={starUpdating} onClick={handleToggleConversationStar} />
                    {starError && <span className="star-control-error" role="alert">{starError}</span>}
                  </div>
                )}
              </div>

              <p>
                {responseMode === "research"
                  ? "Synthesized by the Nexus multi-agent research pipeline."
                  : responseMode === "clarify"
                    ? "One quick question so I can help with the right thing."
                    : "Answered directly by the Nexus assistant."}
              </p>
              {promptCorrection && <p className="prompt-correction-note">{promptCorrection}</p>}

            </div>

            <div className="report-header-actions">
              {conversationId && responseMode === "research" && (
                <>
                  <button type="button" className="report-export-button" onClick={() => window.print()}>
                    ↓ EXPORT PDF
                  </button>
                  <button type="button" className="report-export-button" onClick={exportWord} disabled={wordExporting}>
                    ↓ {wordExporting ? "PREPARING WORD…" : "EXPORT WORD"}
                  </button>
                </>
              )}
              <button
                type="button"
                className="new-research"
                onClick={resetResearch}
              >
                <span>+</span>
                NEW RESEARCH
              </button>
            </div>
            {exportError && <div className="report-export-error" role="alert">{exportError}</div>}

          </section>

          {/* REPORT PIPELINE */}

          {responseMode === "research" && <section className="report-pipeline">

            {stages.map(
              (stage, index) => (
                <React.Fragment
                  key={stage.number}
                >

                  <div className="report-stage">

                    <span>
                      {stage.number}
                    </span>

                    <div>

                      <strong>
                        {stage.title}
                      </strong>

                      <small>
                        {stage.description}
                      </small>

                    </div>

                  </div>

                  {index <
                    stages.length - 1 && (
                    <div className="report-line"></div>
                  )}

                </React.Fragment>
              )
            )}

          </section>}

          {/* REPORT CARD */}

          <article className="report-card">

            <div className="report-card-top">

              <span>
                {responseMode === "research" ? "FINAL RESEARCH REPORT" : responseMode === "clarify" ? "CLARIFICATION" : "DIRECT RESPONSE"}
              </span>

              {responseMode === "research" && <span className="report-status">● VERIFIED</span>}

            </div>

            <div className="report-content">

              <ReactMarkdown
                remarkPlugins={[
                  remarkGfm
                ]}
                components={{

                  h1: ({ children }) => (
                    <h1 className="md-h1">
                      {children}
                    </h1>
                  ),

                  h2: ({ children }) => (
                    <h2 className="md-h2">
                      {children}
                    </h2>
                  ),

                  h3: ({ children }) => (
                    <h3 className="md-h3">
                      {children}
                    </h3>
                  ),

                  p: ({ children }) => (
                    <p className="md-p">
                      {children}
                    </p>
                  ),

                  strong: ({ children }) => (
                    <strong className="md-strong">
                      {children}
                    </strong>
                  ),

                  ul: ({ children }) => (
                    <ul className="md-ul">
                      {children}
                    </ul>
                  ),

                  ol: ({ children }) => (
                    <ol className="md-ol">
                      {children}
                    </ol>
                  ),

                  li: ({ children }) => (
                    <li className="md-li">
                      {children}
                    </li>
                  ),

                  blockquote: ({ children }) => (
                    <blockquote className="md-blockquote">
                      {children}
                    </blockquote>
                  ),

                  hr: () => (
                    <div className="md-divider"></div>
                  ),

                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="md-link"
                    >
                      {children}

                      <span>↗</span>
                    </a>
                  ),

                  table: ({ children }) => (
                    <div className="table-wrapper">

                      <table>
                        {children}
                      </table>

                    </div>
                  ),

                  thead: ({ children }) => (
                    <thead>
                      {children}
                    </thead>
                  ),

                  tbody: ({ children }) => (
                    <tbody>
                      {children}
                    </tbody>
                  ),

                  tr: ({ children }) => (
                    <tr>
                      {children}
                    </tr>
                  ),

                  th: ({ children }) => (
                    <th>
                      {children}
                    </th>
                  ),

                  td: ({ children }) => (
                    <td>
                      {children}
                    </td>
                  ),
                }}
              >
                {report}
              </ReactMarkdown>

            </div>
          </article>

          <section className="continue-chat" aria-label="Continue this chat">
            <div className="continue-chat-heading">
              <span>CONTINUE THIS CHAT</span>
              <p>Ask a follow-up or answer a clarification. Your conversation will stay together in history.</p>
            </div>
            <form className="research-box report-followup" onSubmit={submitFollowUp}>
              <textarea
                value={followUpQuestion}
                onChange={(event) => setFollowUpQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                placeholder="Ask a follow-up or clarify what you meant…"
                aria-label="Write a follow-up message"
                rows="2"
              />
              <button type="submit" disabled={!followUpQuestion.trim() || loading}>
                SEND <span>↗</span>
              </button>
            </form>
            <div className="shortcut">ENTER TO SEND · SHIFT + ENTER FOR A NEW LINE</div>
          </section>

          {/* BOTTOM CTA */}

          <section className="bottom-cta">

            <div className="cta-orb"></div>

            <div>

              <span>
                ANOTHER QUESTION?
              </span>

              <h2>
                Keep digging.
              </h2>

            </div>

            <button
              type="button"
              onClick={resetResearch}
            >
              START NEW RESEARCH

              <span>↗</span>
            </button>

          </section>

        </main>
      )}

      {/* =================================================
          FOOTER
      ================================================= */}

      <footer>

        <div className="footer-brand">
          CODEX<span>.</span>
        </div>

        <div className="footer-middle">
          SEARCH · READ · CRITIQUE · SYNTHESIZE
        </div>

        <div className="footer-right">
          MULTI-AGENT INTELLIGENCE
        </div>

      </footer>

    </div>
  );
}

export default App;
