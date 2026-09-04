import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import "./index.css";

import ForgotPassword from "./Forgotpassword.jsx";
import Login from "./login.jsx";
import Register from "./register.jsx";
import Individual from "./Individual.jsx";

import { API_URL } from "./config";

// =========================================================
// ADMIN CONFIGURATION
// =========================================================

const ADMIN_EMAIL = "codexproject9@gmail.com";


// =========================================================
// APP
// =========================================================

function App() {
  // =======================================================
  // AUTH
  // =======================================================

  const [authPage, setAuthPage] = useState("login");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);

  const handleLogin = (loggedInUser) => {
    setUser(loggedInUser);
    setIsLoggedIn(true);
    setAuthPage("login");
    setActiveTab("nexus");
  };

  const handleLogout = () => {
    setUser(null);
    setIsLoggedIn(false);
    setAuthPage("login");
    setActiveTab("nexus");
  };

  // =======================================================
  // ADMIN
  // =======================================================

  const isAdmin =
    user?.email?.trim().toLowerCase() ===
    ADMIN_EMAIL.trim().toLowerCase();

  // =======================================================
  // MAIN TABS
  // =======================================================

  const [activeTab, setActiveTab] = useState("nexus");

  // Never allow a non-admin to stay on the dashboard.
  useEffect(() => {
    if (activeTab === "dashboard" && !isAdmin) {
      setActiveTab("nexus");
    }
  }, [activeTab, isAdmin]);

  // =======================================================
  // NEXUS RESEARCH
  // =======================================================

  const [topic, setTopic] = useState("");
  const [report, setReport] = useState("");
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
      setActiveStage((current) =>
        current < stages.length - 1 ? current + 1 : current
      );
    }, 4500);

    return () => clearInterval(interval);
  }, [loading]);

  // =======================================================
  // RUN RESEARCH
  // =======================================================

  const runResearch = async () => {
    if (!topic.trim() || loading) return;

    setLoading(true);
    setError("");
    setReport("");
    setActiveStage(0);

    try {
      const response = await fetch(`${API_URL}/api/research`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic: topic.trim(),
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();

      if (!data.report) {
        throw new Error(
          "Backend returned an empty research report."
        );
      }

      setReport(data.report);
      setActiveStage(stages.length - 1);
    } catch (err) {
      console.error("Research error:", err);

      if (
        err instanceof TypeError &&
        err.message === "Failed to fetch"
      ) {
        setError(
          "Backend server is not connected. Please start the FastAPI server and try again."
        );
      } else {
        setError(
          err.message || "Something went wrong. Please try again."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // =======================================================
  // KEYBOARD HANDLER
  // =======================================================

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
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
    setError("");
    setLoading(false);
    setActiveStage(0);
    setActiveTab("nexus");
  };

  // =======================================================
  // AUTH SCREEN
  // =======================================================

  if (!isLoggedIn) {
    if (authPage === "register") {
      return (
        <Register
          onBackToLogin={() => setAuthPage("login")}
        />
      );
    }

    if (authPage === "forgot-password") {
      return (
        <ForgotPassword
          onBack={() => setAuthPage("login")}
        />
      );
    }

    return (
      <Login
        onLogin={handleLogin}
        onCreateAccount={() => setAuthPage("register")}
        onForgotPassword={() => setAuthPage("forgot-password")}
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
        {Array.from({ length: 28 }).map((_, index) => (
          <span
            key={index}
            className={`star star-${index % 5}`}
          ></span>
        ))}
      </div>
    </>
  );

  // =======================================================
  // SHARED NAVBAR
  // =======================================================

  const Navbar = () => (
    <nav className="navbar">
      <div className="logo">CODEX.</div>

      <div className="mode-tabs">
        <button
          type="button"
          className={`mode-tab ${
            activeTab === "nexus" ? "active" : ""
          }`}
          onClick={() => setActiveTab("nexus")}
        >
          NEXUS
        </button>

        <button
          type="button"
          className={`mode-tab ${
            activeTab === "individual" ? "active" : ""
          }`}
          onClick={() => setActiveTab("individual")}
        >
          INDIVIDUAL
        </button>

        {isAdmin && (
          <button
            type="button"
            className={`mode-tab admin-tab ${
              activeTab === "dashboard" ? "active" : ""
            }`}
            onClick={() => setActiveTab("dashboard")}
          >
            DASHBOARD
          </button>
        )}
      </div>

      <div className="status">
        <span className="status-dot"></span>
        RESEARCH ENGINE ONLINE
      </div>
    </nav>
  );

  // =======================================================
  // INDIVIDUAL
  // =======================================================

  if (activeTab === "individual") {
    return (
      <div className="app">
        <Background />
        <Navbar />

        <Individual />
      </div>
    );
  }

  // =======================================================
  // ADMIN DASHBOARD
  // =======================================================

  if (activeTab === "dashboard") {
    if (!isAdmin) {
      return null;
    }

    return (
      <div className="app">
        <Background />
        <Navbar />

        <main className="dashboard-placeholder">
          <div className="eyebrow">
            <span></span>
            ADMIN CONSOLE
          </div>

          <h1>
            Admin
            <br />
            <span>Dashboard.</span>
          </h1>

          <p>
            Administrative analytics, users, research activity,
            and system information will appear here.
          </p>
        </main>
      </div>
    );
  }

  // =======================================================
  // NEXUS
  // =======================================================

  return (
    <div className="app">
      <Background />
      <Navbar />

      {/* ===================================================
          LANDING / LOADING
      =================================================== */}

      {!report && (
        <main className="main-stage">
          <section className="hero">
            <div className="eyebrow">
              <span></span>
              MULTI-AGENT RESEARCH
            </div>

            <h1>
              Research,
              <br />
              <span>without the noise.</span>
            </h1>

            <p className="subtitle">
              Ask a question. Let intelligent agents search,
              read, challenge, and synthesize the signal hidden
              inside the web.
            </p>

            {/* ORBITAL OBJECT */}
            <div
              className={`orbital-system ${
                loading ? "is-loading" : ""
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

            {/* INPUT */}
            {!loading && (
              <>
                <div className="research-box">
                  <textarea
                    value={topic}
                    onChange={(event) =>
                      setTopic(event.target.value)
                    }
                    onKeyDown={handleKeyDown}
                    placeholder="What do you want to investigate?"
                    rows="2"
                  />

                  <button
                    type="button"
                    onClick={runResearch}
                    disabled={!topic.trim()}
                  >
                    EXPLORE
                    <span>↗</span>
                  </button>
                </div>

                <div className="shortcut">
                  <span>⌘</span>
                  ENTER TO RUN
                </div>
              </>
            )}

            {/* LOADING */}
            {loading && (
              <section className="research-progress">
                <div className="progress-header">
                  <div>
                    <span className="progress-label">
                      RESEARCH IN PROGRESS
                    </span>

                    <h2>
                      Investigating
                      <span>.</span>
                      <span>.</span>
                      <span>.</span>
                    </h2>
                  </div>

                  <div className="progress-topic">
                    "{topic}"
                  </div>
                </div>

                <div className="agent-pipeline">
                  {stages.map((stage, index) => {
                    const isActive = index === activeStage;
                    const isDone = index < activeStage;

                    return (
                      <React.Fragment key={stage.number}>
                        <div
                          className={`agent-stage ${
                            isActive ? "active" : ""
                          } ${isDone ? "done" : ""}`}
                        >
                          <div className="stage-number">
                            {isDone ? "✓" : stage.number}
                          </div>

                          <div className="stage-info">
                            <strong>{stage.title}</strong>

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

                        {index < stages.length - 1 && (
                          <div
                            className={`pipeline-connector ${
                              index < activeStage
                                ? "complete"
                                : ""
                            }`}
                          ></div>
                        )}
                      </React.Fragment>
                    );
                  })}
                </div>

                <p className="progress-note">
                  Nexus is gathering evidence before generating
                  your report. This may take a moment.
                </p>
              </section>
            )}

            {/* ERROR */}
            {error && (
              <div className="error-box">
                <strong>Something went wrong.</strong>
                <span>{error}</span>
              </div>
            )}
          </section>
        </main>
      )}

      {/* ===================================================
          REPORT
      =================================================== */}

      {report && !loading && (
        <main className="report-page">
          <section className="report-header">
            <div className="report-heading">
              <div className="eyebrow">
                <span></span>
                RESEARCH OUTPUT
              </div>

              <h1>{topic}</h1>

              <p>
                Synthesized by the Nexus multi-agent research
                pipeline.
              </p>
            </div>

            <button
              type="button"
              className="new-research"
              onClick={resetResearch}
            >
              <span>+</span>
              NEW RESEARCH
            </button>
          </section>

          <section className="report-pipeline">
            {stages.map((stage, index) => (
              <React.Fragment key={stage.number}>
                <div className="report-stage">
                  <span>{stage.number}</span>

                  <div>
                    <strong>{stage.title}</strong>
                    <small>{stage.description}</small>
                  </div>
                </div>

                {index < stages.length - 1 && (
                  <div className="report-line"></div>
                )}
              </React.Fragment>
            ))}
          </section>

          <article className="report-card">
            <div className="report-card-top">
              <span>FINAL RESEARCH REPORT</span>

              <span className="report-status">
                ● VERIFIED
              </span>
            </div>

            <div className="report-content">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => (
                    <h1 className="md-h1">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="md-h2">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="md-h3">{children}</h3>
                  ),
                  p: ({ children }) => (
                    <p className="md-p">{children}</p>
                  ),
                  strong: ({ children }) => (
                    <strong className="md-strong">
                      {children}
                    </strong>
                  ),
                  ul: ({ children }) => (
                    <ul className="md-ul">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="md-ol">{children}</ol>
                  ),
                  li: ({ children }) => (
                    <li className="md-li">{children}</li>
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
                      <table>{children}</table>
                    </div>
                  ),
                  thead: ({ children }) => (
                    <thead>{children}</thead>
                  ),
                  tbody: ({ children }) => (
                    <tbody>{children}</tbody>
                  ),
                  tr: ({ children }) => <tr>{children}</tr>,
                  th: ({ children }) => <th>{children}</th>,
                  td: ({ children }) => <td>{children}</td>,
                }}
              >
                {report}
              </ReactMarkdown>
            </div>
          </article>

          <section className="bottom-cta">
            <div className="cta-orb"></div>

            <div>
              <span>ANOTHER QUESTION?</span>

              <h2>Keep digging.</h2>
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

      {/* ===================================================
          FOOTER
      =================================================== */}

      <footer>
        <div className="footer-brand">
          NEXUS<span>.</span>
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
