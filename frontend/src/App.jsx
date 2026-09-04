import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./index.css";

import Login from "./login.jsx";
import Register from "./register.jsx";
import Individual from "./Individual.jsx";
import { API_URL } from "./config";

function App() {
  // ================= AUTH =================

  const [authPage, setAuthPage] = useState("login");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);

  const handleLogin = (loggedInUser) => {
    setUser(loggedInUser);
    setIsLoggedIn(true);
    setAuthPage("login");
  };

  const handleLogout = () => {
    setUser(null);
    setIsLoggedIn(false);
    setAuthPage("login");
  };

  // ================= MAIN TABS =================

  const [activeTab, setActiveTab] = useState("nexus");

  // ================= NEXUS RESEARCH =================

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

  // ---------------- RESEARCH PROGRESS ---------------- //

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

  // ---------------- RUN RESEARCH ---------------- //

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
        throw new Error("Backend returned an empty research report.");
      }

      setReport(data.report);
      setActiveStage(stages.length - 1);
    } catch (error) {
      console.error("Research error:", error);

      if (
        error instanceof TypeError &&
        error.message === "Failed to fetch"
      ) {
        setError(
          "Backend server is not connected. Please start the FastAPI server and try again."
        );
      } else {
        setError(
          error.message || "Something went wrong. Please try again."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // ---------------- KEYBOARD HANDLER ---------------- //

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      runResearch();
    }
  };

  // ---------------- RESET RESEARCH ---------------- //

  const resetResearch = () => {
    setTopic("");
    setReport("");
    setError("");
    setLoading(false);
    setActiveStage(0);
  };

  // ================= LOGIN / REGISTER =================

  if (!isLoggedIn) {
    if (authPage === "register") {
      return (
        <Register
          onBackToLogin={() => {
            setAuthPage("login");
          }}
        />
      );
    }

    return (
      <Login
        onLogin={handleLogin}
        onCreateAccount={() => {
          setAuthPage("register");
        }}
      />
    );
  }

  // ================= INDIVIDUAL TAB =================

  if (activeTab === "individual") {
    return (
      <div className="app">
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

        <nav className="navbar">
          <div className="logo">CODEX.</div>

          <div className="mode-tabs">
            <button
              className="mode-tab"
              onClick={() => setActiveTab("individual")}
            >
              INDIVIDUAL
            </button>

            <button
              className="mode-tab active"
              onClick={() => setActiveTab("nexus")}
            >
              NEXUS
            </button>
          </div>

          <div className="status">
            <span className="status-dot"></span>
            DOCUMENT ANALYZER ONLINE
          </div>
        </nav>

        <Individual />
      </div>
    );
  }

  // ================= NEXUS INTERFACE =================

  return (
    <div className="app">
      {/* ================= BACKGROUND ================= */}

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

      {/* ================= NAVBAR ================= */}

      <nav className="navbar">
        <div className="logo">NEXUS.</div>

        <div className="mode-tabs">
          <button
            className="mode-tab"
            onClick={() => setActiveTab("individual")}
          >
            INDIVIDUAL
          </button>

          <button
            className="mode-tab active"
            onClick={() => setActiveTab("nexus")}
          >
            NEXUS
          </button>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          RESEARCH ENGINE ONLINE
        </div>
      </nav>

      {/* ================= LANDING / LOADING ================= */}

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
              Ask a question. Let intelligent agents search, read,
              challenge, and synthesize the signal hidden inside the web.
            </p>

            {/* ================= ORBITAL OBJECT ================= */}

            <div
              className={`orbital-system ${loading ? "is-loading" : ""
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

            {/* ================= INPUT ================= */}

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

            {/* ================= LOADING STATE ================= */}

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
                          className={`agent-stage ${isActive ? "active" : ""
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
                            className={`pipeline-connector ${index < activeStage
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
                  Nexus is gathering evidence before generating your
                  report. This may take a moment.
                </p>
              </section>
            )}

            {/* ================= ERROR ================= */}

            {error && (
              <div className="error-box">
                <strong>Something went wrong.</strong>
                <span>{error}</span>
              </div>
            )}
          </section>
        </main>
      )}

      {/* ================= REPORT ================= */}

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
              className="new-research"
              onClick={resetResearch}
            >
              <span>+</span>
              NEW RESEARCH
            </button>
          </section>

          {/* ================= PIPELINE ================= */}

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

          {/* ================= REPORT CARD ================= */}

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

                  tr: ({ children }) => (
                    <tr>{children}</tr>
                  ),

                  th: ({ children }) => (
                    <th>{children}</th>
                  ),

                  td: ({ children }) => (
                    <td>{children}</td>
                  ),
                }}
              >
                {report}
              </ReactMarkdown>
            </div>
          </article>

          {/* ================= BOTTOM CTA ================= */}

          <section className="bottom-cta">
            <div className="cta-orb"></div>

            <div>
              <span>ANOTHER QUESTION?</span>

              <h2>Keep digging.</h2>
            </div>

            <button onClick={resetResearch}>
              START NEW RESEARCH
              <span>↗</span>
            </button>
          </section>
        </main>
      )}

      {/* ================= FOOTER ================= */}

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