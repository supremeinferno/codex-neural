import React from "react";

function Dashboard({ user }) {
  const adminEmail = "codeproject9@gmail.com";

  const isAdmin = user?.email?.toLowerCase() === adminEmail.toLowerCase();

  if (!isAdmin) {
    return (
      <div className="dashboard-access-denied">
        <div className="dashboard-denied-card">
          <div className="dashboard-denied-icon">×</div>

          <span className="dashboard-eyebrow">
            RESTRICTED ACCESS
          </span>

          <h1>Access denied.</h1>

          <p>
            The CODEX administrative console is available only to
            authorized administrators.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-page">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <section className="dashboard-header">

        <div>
          <div className="dashboard-eyebrow">
            <span className="dashboard-status-dot"></span>
            ADMINISTRATIVE CONSOLE
          </div>

          <h1>
            System
            <span> overview.</span>
          </h1>

          <p>
            Monitor CODEX research activity, users, documents,
            and system performance from one place.
          </p>
        </div>

        <div className="dashboard-admin">
          <div className="dashboard-admin-avatar">
            {user?.email?.charAt(0).toUpperCase() || "A"}
          </div>

          <div>
            <strong>Administrator</strong>
            <small>{user?.email}</small>
          </div>
        </div>

      </section>


      {/* =====================================================
          SYSTEM STATUS
      ===================================================== */}

      <section className="dashboard-status">

        <div className="dashboard-status-item">
          <span className="status-live"></span>
          <div>
            <small>RESEARCH ENGINE</small>
            <strong>Operational</strong>
          </div>
        </div>

        <div className="dashboard-status-item">
          <span className="status-live"></span>
          <div>
            <small>DOCUMENT ENGINE</small>
            <strong>Operational</strong>
          </div>
        </div>

        <div className="dashboard-status-item">
          <span className="status-live"></span>
          <div>
            <small>DATABASE</small>
            <strong>Operational</strong>
          </div>
        </div>

        <div className="dashboard-status-item">
          <span className="status-live"></span>
          <div>
            <small>API</small>
            <strong>Connected</strong>
          </div>
        </div>

      </section>


      {/* =====================================================
          METRICS
      ===================================================== */}

      <section className="dashboard-grid">

        <div className="dashboard-card metric-card">
          <span className="metric-label">
            TOTAL USERS
          </span>

          <strong>128</strong>

          <small>
            Registered accounts
          </small>
        </div>


        <div className="dashboard-card metric-card">
          <span className="metric-label">
            RESEARCH QUERIES
          </span>

          <strong>1,842</strong>

          <small>
            Queries processed
          </small>
        </div>


        <div className="dashboard-card metric-card">
          <span className="metric-label">
            DOCUMENTS
          </span>

          <strong>376</strong>

          <small>
            PDFs analyzed
          </small>
        </div>


        <div className="dashboard-card metric-card">
          <span className="metric-label">
            SUCCESS RATE
          </span>

          <strong>98.7%</strong>

          <small>
            Successful operations
          </small>
        </div>

      </section>


      {/* =====================================================
          MAIN DASHBOARD
      ===================================================== */}

      <section className="dashboard-main-grid">

        {/* -----------------------------------------------
            ACTIVITY
        ------------------------------------------------ */}

        <div className="dashboard-card activity-card">

          <div className="card-heading">
            <div>
              <span>RESEARCH ACTIVITY</span>
              <h2>Recent operations</h2>
            </div>

            <button className="dashboard-small-button">
              VIEW ALL ↗
            </button>
          </div>


          <div className="activity-list">

            <div className="activity-row">
              <div className="activity-icon">
                R
              </div>

              <div className="activity-content">
                <strong>Research query completed</strong>
                <span>
                  Multi-agent web research
                </span>
              </div>

              <time>2 min ago</time>
            </div>


            <div className="activity-row">
              <div className="activity-icon">
                P
              </div>

              <div className="activity-content">
                <strong>PDF analysis completed</strong>
                <span>
                  Individual document analyzer
                </span>
              </div>

              <time>8 min ago</time>
            </div>


            <div className="activity-row">
              <div className="activity-icon">
                R
              </div>

              <div className="activity-content">
                <strong>New user registered</strong>
                <span>
                  Account creation
                </span>
              </div>

              <time>21 min ago</time>
            </div>


            <div className="activity-row">
              <div className="activity-icon">
                S
              </div>

              <div className="activity-content">
                <strong>Research pipeline completed</strong>
                <span>
                  Search → Read → Write → Critique
                </span>
              </div>

              <time>34 min ago</time>
            </div>

          </div>

        </div>


        {/* -----------------------------------------------
            PIPELINE
        ------------------------------------------------ */}

        <div className="dashboard-card pipeline-card">

          <div className="card-heading">
            <div>
              <span>AI PIPELINE</span>
              <h2>System agents</h2>
            </div>
          </div>


          <div className="pipeline">

            <div className="pipeline-item">
              <div className="pipeline-number">
                01
              </div>

              <div>
                <strong>Research Agent</strong>
                <span>Web discovery</span>
              </div>

              <b>ONLINE</b>
            </div>


            <div className="pipeline-line"></div>


            <div className="pipeline-item">
              <div className="pipeline-number">
                02
              </div>

              <div>
                <strong>Reader Agent</strong>
                <span>Source extraction</span>
              </div>

              <b>ONLINE</b>
            </div>


            <div className="pipeline-line"></div>


            <div className="pipeline-item">
              <div className="pipeline-number">
                03
              </div>

              <div>
                <strong>Writer Agent</strong>
                <span>Report synthesis</span>
              </div>

              <b>ONLINE</b>
            </div>


            <div className="pipeline-line"></div>


            <div className="pipeline-item">
              <div className="pipeline-number">
                04
              </div>

              <div>
                <strong>Critic Agent</strong>
                <span>Quality evaluation</span>
              </div>

              <b>ONLINE</b>
            </div>

          </div>

        </div>

      </section>


      {/* =====================================================
          BOTTOM SECTION
      ===================================================== */}

      <section className="dashboard-bottom-grid">

        <div className="dashboard-card system-card">

          <span className="metric-label">
            SYSTEM INFORMATION
          </span>

          <div className="system-info-row">
            <span>Platform</span>
            <strong>CODEX Intelligence</strong>
          </div>

          <div className="system-info-row">
            <span>Version</span>
            <strong>1.0.0</strong>
          </div>

          <div className="system-info-row">
            <span>Research Engine</span>
            <strong>Multi-Agent</strong>
          </div>

          <div className="system-info-row">
            <span>Document Engine</span>
            <strong>RAG</strong>
          </div>

        </div>


        <div className="dashboard-card architecture-card">

          <span className="metric-label">
            ARCHITECTURE
          </span>

          <h2>
            Search.
            <br />
            Read.
            <br />
            Synthesize.
          </h2>

          <p>
            CODEX coordinates multiple AI agents to transform
            raw information into structured research intelligence.
          </p>

        </div>

      </section>

    </div>
  );
}

export default Dashboard;