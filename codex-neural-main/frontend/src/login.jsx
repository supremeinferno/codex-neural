import React, { useState } from "react";
import { API_URL } from "./config";
import Atmosphere from "./Atmosphere";

function Login({ onLogin, onCreateAccount, onForgotPassword }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");

    if (!email.trim() || !password.trim()) {
      setError("Please enter your email and password.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        setError(data.message || "Invalid email or password.");
        return;
      }

      onLogin(data.user);
    } catch (error) {
      console.error("Login error:", error);

      if (
        error instanceof TypeError &&
        error.message === "Failed to fetch"
      ) {
        setError(
          "Unable to connect to the server. Please make sure the backend is running."
        );
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">

      {/* Background */}
      <div className="star-field">
        <span className="star star-1"></span>
        <span className="star star-2"></span>
        <span className="star star-3"></span>
        <span className="star star-4"></span>
        <span className="star star-5"></span>
        <span className="star star-6"></span>
      </div>

      <div className="login-glow login-glow-1"></div>
      <div className="login-glow login-glow-2"></div>

      <Atmosphere />

      <div className="login-card">

        <div className="login-top">
          <div className="login-brand">CODEX.</div>

          <div className="login-status">
            <span></span>
            SECURE ACCESS
          </div>
        </div>

        <div className="login-eyebrow">
          <span></span>
          DOCUMENT INTELLIGENCE
        </div>

        <h1>
          Welcome
          <br />
          <span>back.</span>
        </h1>

        <p className="login-subtitle">
          Sign in to continue to your intelligent research workspace.
        </p>

        <form onSubmit={handleSubmit}>

          <div className="login-field">
            <label>Email</label>

            <input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={loading}
            />
          </div>

          <div className="login-field">
            <div className="login-label-row">
              <label>Password</label>

              <button
                type="button"
                className="forgot-button"
                onClick={onForgotPassword}
                disabled={loading}
              >
                Forgot password?
              </button>
            </div>

            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={loading}
            />
          </div>

          {error && (
            <div className="login-error">
              <span>!</span>
              {error}
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            <span>
              {loading ? "SIGNING IN..." : "SIGN IN"}
            </span>

            {!loading && <span className="login-arrow">↗</span>}
          </button>

        </form>

        <div className="login-create">
          <span>Don't have an account?</span>

          <button
            type="button"
            className="login-create-button"
            onClick={onCreateAccount}
            disabled={loading}
          >
            CREATE ACCOUNT
          </button>
        </div>

        <div className="login-footer">
          <span>CODEX INTELLIGENCE</span>
          <span>•</span>
          <span>RESEARCH WORKSPACE</span>
        </div>

      </div>
    </div>
  );
}

export default Login;