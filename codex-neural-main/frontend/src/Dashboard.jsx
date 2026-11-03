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
    const [deleting, setDeleting] = useState(null);

    const adminEmail = user?.email || ADMIN_EMAIL;

    // =====================================================
    // LOAD DASHBOARD
    // =====================================================

    const loadDashboard = async () => {
        try {
            setLoading(true);
            setError("");

            const response = await fetch(
                `${API_URL}/api/admin/dashboard?email=${encodeURIComponent(
                    adminEmail
                )}`
            );

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail || "Unable to load dashboard."
                );
            }

            setData(result);
        } catch (err) {
            console.error(err);
            setError(err.message || "Something went wrong.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadDashboard();
    }, []);

    // =====================================================
    // REMOVE USER
    // =====================================================

    const removeUser = async (userId, email) => {
        if (email.toLowerCase() === ADMIN_EMAIL.toLowerCase()) {
            return;
        }

        const confirmed = window.confirm(
            `Remove ${email} from registered users?`
        );

        if (!confirmed) return;

        try {
            setDeleting(`user-${userId}`);

            const response = await fetch(
                `${API_URL}/api/admin/users/${userId}?email=${encodeURIComponent(
                    adminEmail
                )}`,
                {
                    method: "DELETE",
                }
            );

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail || "Unable to remove user."
                );
            }

            await loadDashboard();
        } catch (err) {
            alert(err.message);
        } finally {
            setDeleting(null);
        }
    };

    // =====================================================
    // REMOVE ONE LOGIN
    // =====================================================

    const removeLogin = async (activityId) => {
        const confirmed = window.confirm(
            "Remove this login activity?"
        );

        if (!confirmed) return;

        try {
            setDeleting(`login-${activityId}`);

            const response = await fetch(
                `${API_URL}/api/admin/logins/${activityId}?email=${encodeURIComponent(
                    adminEmail
                )}`,
                {
                    method: "DELETE",
                }
            );

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail || "Unable to remove login."
                );
            }

            await loadDashboard();
        } catch (err) {
            alert(err.message);
        } finally {
            setDeleting(null);
        }
    };

    // =====================================================
    // DELETE ALL LOGIN HISTORY
    // =====================================================

    const deleteAllLogins = async () => {
        if (data.recent_logins.length === 0) return;

        const confirmed = window.confirm(
            "Delete ALL recent login activity?\n\nThis action cannot be undone."
        );

        if (!confirmed) return;

        try {
            setDeleting("all-logins");

            const response = await fetch(
                `${API_URL}/api/admin/logins?email=${encodeURIComponent(
                    adminEmail
                )}`,
                {
                    method: "DELETE",
                }
            );

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail || "Unable to delete login history."
                );
            }

            await loadDashboard();
        } catch (err) {
            alert(err.message);
        } finally {
            setDeleting(null);
        }
    };

    // =====================================================
    // FORMAT DATE
    // =====================================================

    const formatDate = (value) => {
        if (!value) return "—";

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return value;
        }

        return date.toLocaleString("en-IN", {
            day: "numeric",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    // =====================================================
    // INITIAL
    // =====================================================

    const getInitial = (email) => {
        if (!email) return "U";
        return email.charAt(0).toUpperCase();
    };

    // =====================================================
    // LOADING
    // =====================================================

    if (loading) {
        return (
            <div className="dashboard-page">
                <div className="dashboard-loading">
                    <div className="loading-spinner"></div>
                    <span>Loading control center...</span>
                </div>
            </div>
        );
    }

    // =====================================================
    // ERROR
    // =====================================================

    if (error) {
        return (
            <div className="dashboard-page">
                <div className="dashboard-error">
                    <span>Unable to load dashboard</span>
                    <p>{error}</p>

                    <button
                        className="refresh-btn"
                        onClick={loadDashboard}
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    // =====================================================
    // DASHBOARD
    // =====================================================

    return (
        <div className="dashboard-page">

            {/* =========================================
                HERO
            ========================================= */}

            <section className="dashboard-hero">

                <div className="hero-top">

                    <div className="hero-admin">
                        <span className="admin-dot"></span>
                        <span>Administrator</span>
                    </div>

                    <button
                        className="refresh-btn"
                        onClick={loadDashboard}
                    >
                        ↻ &nbsp; Refresh
                    </button>

                </div>

                <div className="eyebrow">
                    ADMINISTRATION
                </div>

                <h1>
                    Control center.
                </h1>

                <p>
                    Monitor registered users and authentication
                    activity from one centralized dashboard.
                </p>

            </section>


            {/* =========================================
                STAT CARDS
            ========================================= */}

            <section className="stats-grid">

                <div className="stat-card">

                    <div className="stat-top">
                        <span>TOTAL USERS</span>
                        <span>01</span>
                    </div>

                    <div className="stat-number">
                        {data.total_users}
                    </div>

                    <div className="stat-description">
                        Registered accounts
                    </div>

                </div>


                <div className="stat-card">

                    <div className="stat-top">
                        <span>TOTAL LOGINS</span>
                        <span>02</span>
                    </div>

                    <div className="stat-number">
                        {data.total_logins}
                    </div>

                    <div className="stat-description">
                        Recorded authentication events
                    </div>

                </div>

            </section>


            {/* =========================================
                RECENT LOGIN ACTIVITY
            ========================================= */}

            <section className="dashboard-section">

                <div className="section-heading">

                    <div>
                        <div className="eyebrow">
                            AUTHENTICATION
                        </div>

                        <h2>
                            Recent login activity
                        </h2>
                    </div>

                    <div className="section-actions">

                        <span className="event-count">
                            {data.recent_logins.length} EVENTS
                        </span>

                        <button
                            className="delete-all-btn"
                            onClick={deleteAllLogins}
                            disabled={
                                deleting === "all-logins" ||
                                data.recent_logins.length === 0
                            }
                        >
                            {deleting === "all-logins"
                                ? "DELETING..."
                                : "DELETE ALL"}
                        </button>

                    </div>

                </div>


                <div className="table-card">

                    <div className="activity-table">

                        <div className="table-header">

                            <div>USER</div>
                            <div>DATE & TIME</div>
                            <div>ACTION</div>

                        </div>


                        <div className="activity-scroll">

                            {data.recent_logins.length === 0 ? (

                                <div className="empty-state">
                                    No login activity recorded.
                                </div>

                            ) : (

                                data.recent_logins.map((login) => (

                                    <div
                                        className="activity-row"
                                        key={login.id}
                                    >

                                        <div className="user-cell">

                                            <div className="avatar">
                                                {getInitial(login.email)}
                                            </div>

                                            <div className="user-email">
                                                {login.email}
                                            </div>

                                        </div>


                                        <div className="date-cell">
                                            {formatDate(
                                                login.login_time
                                            )}
                                        </div>


                                        <div className="action-cell">

                                            <button
                                                className="remove-btn"
                                                disabled={
                                                    deleting ===
                                                    `login-${login.id}`
                                                }
                                                onClick={() =>
                                                    removeLogin(
                                                        login.id
                                                    )
                                                }
                                            >
                                                {deleting ===
                                                `login-${login.id}`
                                                    ? "REMOVING..."
                                                    : "REMOVE"}
                                            </button>

                                        </div>

                                    </div>

                                ))

                            )}

                        </div>

                    </div>

                </div>

            </section>


            {/* =========================================
                REGISTERED USERS
            ========================================= */}

            <section className="dashboard-section users-section">

                <div className="section-heading">

                    <div>
                        <div className="eyebrow">
                            USER DIRECTORY
                        </div>

                        <h2>
                            Registered users
                        </h2>
                    </div>

                    <span className="event-count">
                        {data.users.length} USERS
                    </span>

                </div>


                <div className="table-card">

                    <div className="users-table">

                        <div className="table-header users-header">

                            <div>USER</div>
                            <div>REGISTERED</div>
                            <div>ACTION</div>

                        </div>


                        <div className="users-scroll">

                            {data.users.length === 0 ? (

                                <div className="empty-state">
                                    No registered users.
                                </div>

                            ) : (

                                data.users.map((registeredUser) => {

                                    const isAdmin =
                                        registeredUser.email
                                            .toLowerCase() ===
                                        ADMIN_EMAIL.toLowerCase();

                                    return (

                                        <div
                                            className="activity-row"
                                            key={registeredUser.id}
                                        >

                                            <div className="user-cell">

                                                <div className="avatar">
                                                    {getInitial(
                                                        registeredUser.email
                                                    )}
                                                </div>

                                                <div className="user-email">
                                                    {
                                                        registeredUser.email
                                                    }
                                                </div>

                                            </div>


                                            <div className="date-cell">
                                                {formatDate(
                                                    registeredUser.created_at
                                                )}
                                            </div>


                                            <div className="action-cell">

                                                {isAdmin ? (

                                                    <span className="admin-badge">
                                                        ADMIN
                                                    </span>

                                                ) : (

                                                    <button
                                                        className="remove-btn"
                                                        disabled={
                                                            deleting ===
                                                            `user-${registeredUser.id}`
                                                        }
                                                        onClick={() =>
                                                            removeUser(
                                                                registeredUser.id,
                                                                registeredUser.email
                                                            )
                                                        }
                                                    >
                                                        {deleting ===
                                                        `user-${registeredUser.id}`
                                                            ? "REMOVING..."
                                                            : "REMOVE"}
                                                    </button>

                                                )}

                                            </div>

                                        </div>

                                    );
                                })

                            )}

                        </div>

                    </div>

                </div>

            </section>

        </div>
    );
}

export default Dashboard;