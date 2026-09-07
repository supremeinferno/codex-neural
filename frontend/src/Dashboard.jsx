import React, { useEffect, useState } from "react";
import { API_URL } from "./config";

const ADMIN_EMAIL = "codexproject9@gmail.com";

function Dashboard({ user }) {
  const [data, setData] = useState({
    total_users: 0,
    total_logins: 0,
    users: [],
    recent_logins: [],
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [actionLoading, setActionLoading] = useState(false);

  const isAdmin =
    user?.email?.trim().toLowerCase() ===
    ADMIN_EMAIL.toLowerCase();

  // ==========================================================
  // LOAD DASHBOARD
  // ==========================================================

  const loadDashboard = async () => {
    if (!isAdmin) return;

    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_URL}/api/admin/dashboard?email=${encodeURIComponent(
          user.email
        )}`
      );

      if (!response.ok) {
        const result = await response.json().catch(() => ({}));

        throw new Error(
          result.detail || "Unable to load dashboard."
        );
      }

      const result = await response.json();

      setData({
        total_users: result.total_users || 0,
        total_logins: result.total_logins || 0,
        users: result.users || [],
        recent_logins: result.recent_logins || [],
      });
    } catch (err) {
      console.error("Dashboard error:", err);

      setError(
        err.message ||
          "Something went wrong while loading dashboard."
      );
    } finally {
      setLoading(false);
    }
  };

  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

  useEffect(() => {
    loadDashboard();
  }, [isAdmin, user?.email]);

  // ==========================================================
  // REMOVE USER
  // ==========================================================

  const removeUser = async (userId, email) => {
    const confirmed = window.confirm(
      `Remove ${email}?\n\nThis will also remove this user's login history.`
    );

    if (!confirmed) return;

    try {
      setActionLoading(true);

      const response = await fetch(
        `${API_URL}/api/admin/users/${userId}?email=${encodeURIComponent(
          user.email
        )}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          result.detail || "Unable to remove user."
        );
      }

      await loadDashboard();
    } catch (err) {
      console.error("Remove user error:", err);

      alert(
        err.message ||
          "Failed to remove user."
      );
    } finally {
      setActionLoading(false);
    }
  };

  // ==========================================================
  // REMOVE SINGLE LOGIN
  // ==========================================================

  const removeLogin = async (activityId) => {
    const confirmed = window.confirm(
      "Remove this login record?"
    );

    if (!confirmed) return;

    try {
      setActionLoading(true);

      const response = await fetch(
        `${API_URL}/api/admin/logins/${activityId}?email=${encodeURIComponent(
          user.email
        )}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          result.detail || "Unable to remove login."
        );
      }

      await loadDashboard();
    } catch (err) {
      console.error("Remove login error:", err);

      alert(
        err.message ||
          "Failed to remove login."
      );
    } finally {
      setActionLoading(false);
    }
  };

  // ==========================================================
  // DELETE ALL LOGIN HISTORY
  // ==========================================================

  const deleteAllLogins = async () => {
    const confirmed = window.confirm(
      "Delete ALL recent login history?\n\nThis cannot be undone."
    );

    if (!confirmed) return;

    try {
      setActionLoading(true);

      const response = await fetch(
        `${API_URL}/api/admin/logins?email=${encodeURIComponent(
          user.email
        )}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          result.detail ||
            "Unable to delete login history."
        );
      }

      await loadDashboard();
    } catch (err) {
      console.error(
        "Delete login history error:",
        err
      );

      alert(
        err.message ||
          "Failed to delete login history."
      );
    } finally {
      setActionLoading(false);
    }
  };

  // ==========================================================
  // FORMAT DATE
  // ==========================================================

  const formatDate = (value) => {
    if (!value) return "—";

    const date = new Date(
      value.includes("T")
        ? value
        : value.replace(" ", "T") + "Z"
    );

    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString([], {
      dateStyle: "medium",
      timeStyle: "short",
    });
  };

  // ==========================================================
  // ACCESS DENIED
  // ==========================================================

  if (!isAdmin) {
    return (
      <div className="dashboard-access-denied">

        <div className="dashboard-denied-card">

          <div className="dashboard-denied-icon">
            ×
          </div>

          <span className="dashboard-eyebrow">
            RESTRICTED ACCESS
          </span>

          <h1>
            Access denied.
          </h1>

          <p>
            The CODEX administrative console is
            available only to authorized administrators.
          </p>

        </div>

      </div>
    );
  }

  // ==========================================================
  // LOADING
  // ==========================================================

  if (loading) {
    return (
      <div className="dashboard-page">

        <div className="dashboard-loading">

          <div className="dashboard-loader"></div>

          <span>
            LOADING ADMIN CONSOLE
          </span>

        </div>

      </div>
    );
  }

  // ==========================================================
  // DASHBOARD
  // ==========================================================

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
            Monitor CODEX users, authentication activity,
            and system operations.
          </p>

        </div>


        <div className="dashboard-admin">

          <div className="dashboard-admin-avatar">
            {user?.email?.charAt(0).toUpperCase() || "A"}
          </div>

          <div>

            <strong>
              Administrator
            </strong>

            <small>
              {user?.email}
            </small>

          </div>

        </div>

      </section>


      {/* =====================================================
          ACTION BAR
      ===================================================== */}

      <section className="dashboard-action-bar">

        <div>

          <span className="dashboard-live-indicator">
            ●
          </span>

          SYSTEM LIVE

        </div>

        <div className="dashboard-actions">

          <button
            className="dashboard-action-button"
            onClick={loadDashboard}
            disabled={loading || actionLoading}
          >
            ↻ REFRESH
          </button>

          <button
            className="dashboard-action-button danger"
            onClick={deleteAllLogins}
            disabled={
              actionLoading ||
              data.recent_logins.length === 0
            }
          >
            DELETE ALL LOGINS
          </button>

        </div>

      </section>


      {/* =====================================================
          ERROR
      ===================================================== */}

      {error && (
        <div className="dashboard-error">
          {error}
        </div>
      )}


      {/* =====================================================
          METRICS
      ===================================================== */}

      <section className="dashboard-grid">

        <div className="dashboard-card metric-card">

          <span className="metric-label">
            TOTAL USERS
          </span>

          <strong>
            {data.total_users}
          </strong>

          <small>
            Registered accounts
          </small>

        </div>


        <div className="dashboard-card metric-card">

          <span className="metric-label">
            TOTAL LOGINS
          </span>

          <strong>
            {data.total_logins}
          </strong>

          <small>
            Successful login events
          </small>

        </div>


        <div className="dashboard-card metric-card">

          <span className="metric-label">
            RECENT OPERATIONS
          </span>

          <strong>
            {data.recent_logins.length}
          </strong>

          <small>
            Recorded login activity
          </small>

        </div>


        <div className="dashboard-card metric-card">

          <span className="metric-label">
            SYSTEM STATUS
          </span>

          <strong className="metric-online">
            ONLINE
          </strong>

          <small>
            All services operational
          </small>

        </div>

      </section>


      {/* =====================================================
          RECENT LOGINS
      ===================================================== */}

      <section className="dashboard-card dashboard-table-card">

        <div className="dashboard-section-heading">

          <div>

            <span className="metric-label">
              RECENT OPERATIONS
            </span>

            <h2>
              Login activity
            </h2>

          </div>

          <span className="dashboard-count">
            {data.recent_logins.length} EVENTS
          </span>

        </div>


        {data.recent_logins.length === 0 ? (

          <div className="dashboard-empty">
            No login activity recorded.
          </div>

        ) : (

          <div className="dashboard-table-wrapper">

            <table className="dashboard-table">

              <thead>

                <tr>

                  <th>
                    USER
                  </th>

                  <th>
                    DATE & TIME
                  </th>

                  <th>
                    ACTIVITY ID
                  </th>

                  <th>
                    ACTION
                  </th>

                </tr>

              </thead>

              <tbody>

                {data.recent_logins.map(
                  (login) => (

                    <tr key={login.id}>

                      <td>

                        <div className="dashboard-user-cell">

                          <div className="dashboard-table-avatar">
                            {login.email
                              ?.charAt(0)
                              .toUpperCase()}
                          </div>

                          <span>
                            {login.email}
                          </span>

                        </div>

                      </td>


                      <td>
                        {formatDate(
                          login.login_time
                        )}
                      </td>


                      <td>
                        #{login.id}
                      </td>


                      <td>

                        <button
                          className="table-delete-button"
                          onClick={() =>
                            removeLogin(login.id)
                          }
                          disabled={actionLoading}
                        >
                          REMOVE
                        </button>

                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        )}

      </section>


      {/* =====================================================
          REGISTERED USERS
      ===================================================== */}

      <section className="dashboard-card dashboard-table-card">

        <div className="dashboard-section-heading">

          <div>

            <span className="metric-label">
              USER DIRECTORY
            </span>

            <h2>
              Registered users
            </h2>

          </div>

          <span className="dashboard-count">
            {data.users.length} USERS
          </span>

        </div>


        {data.users.length === 0 ? (

          <div className="dashboard-empty">
            No registered users.
          </div>

        ) : (

          <div className="dashboard-table-wrapper">

            <table className="dashboard-table">

              <thead>

                <tr>

                  <th>
                    USER
                  </th>

                  <th>
                    REGISTERED
                  </th>

                  <th>
                    USER ID
                  </th>

                  <th>
                    ACTION
                  </th>

                </tr>

              </thead>

              <tbody>

                {data.users.map(
                  (registeredUser) => (

                    <tr key={registeredUser.id}>

                      <td>

                        <div className="dashboard-user-cell">

                          <div className="dashboard-table-avatar">
                            {registeredUser.email
                              ?.charAt(0)
                              .toUpperCase()}
                          </div>

                          <span>
                            {registeredUser.email}
                          </span>

                        </div>

                      </td>


                      <td>
                        {formatDate(
                          registeredUser.created_at
                        )}
                      </td>


                      <td>
                        #{registeredUser.id}
                      </td>


                      <td>

                        <button
                          className="table-delete-button"
                          onClick={() =>
                            removeUser(
                              registeredUser.id,
                              registeredUser.email
                            )
                          }
                          disabled={
                            actionLoading ||
                            registeredUser.email
                              ?.toLowerCase() ===
                              ADMIN_EMAIL.toLowerCase()
                          }
                        >
                          {registeredUser.email
                            ?.toLowerCase() ===
                          ADMIN_EMAIL.toLowerCase()
                            ? "ADMIN"
                            : "REMOVE"}
                        </button>

                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        )}

      </section>


      {/* =====================================================
          SYSTEM INFORMATION
      ===================================================== */}

      <section className="dashboard-bottom-grid">

        <div className="dashboard-card system-card">

          <span className="metric-label">
            SYSTEM INFORMATION
          </span>

          <div className="system-info-row">
            <span>
              Platform
            </span>

            <strong>
              CODEX Intelligence
            </strong>
          </div>

          <div className="system-info-row">
            <span>
              Authentication
            </span>

            <strong>
              SQLite
            </strong>
          </div>

          <div className="system-info-row">
            <span>
              Research Engine
            </span>

            <strong>
              Multi-Agent
            </strong>
          </div>

          <div className="system-info-row">
            <span>
              Document Engine
            </span>

            <strong>
              RAG
            </strong>
          </div>

        </div>


        <div className="dashboard-card architecture-card">

          <span className="metric-label">
            ARCHITECTURE
          </span>

          <h2>
            Observe.
            <br />
            Analyze.
            <br />
            Control.
          </h2>

          <p>
            CODEX provides administrators with a
            centralized view of authentication,
            research activity, and system usage.
          </p>

        </div>

      </section>

    </div>
  );
}

export default Dashboard;