import React, { useState } from "react";
import { API_URL } from "./config";
import Atmosphere from "./Atmosphere";

function Register({ onBackToLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setSuccess("");

    // Validation
    if (!email.trim() || !password || !confirmPassword) {
      setError("Please fill in all fields.");
      return;
    }

    if (password.length < 6) {
      setError("Password must contain at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/register`, {
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
        setError(data.message || "Unable to create account.");
        return;
      }

      setSuccess("Account created successfully.");

      // Clear form
      setEmail("");
      setPassword("");
      setConfirmPassword("");

      // Return to login
      setTimeout(() => {
        onBackToLogin();
      }, 1200);
    } catch (error) {
      console.error("Registration error:", error);

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
    <div className="login-page register-page">

      {/* Animated background */}
      <Atmosphere />

      {/* Register Card */}
      <div className="login-card register-card">

        {/* Brand */}
        <div className="login-brand">
          CODEX.
        </div>

        {/* Eyebrow */}
        <div className="login-eyebrow">
          <span></span>
          CREATE YOUR ACCOUNT
        </div>

        {/* Heading */}
        <h1>
          Join
          <br />
          <span>Codex.</span>
        </h1>

        {/* Description */}
        <p className="login-subtitle">
          Create an account to access your intelligent research
          workspace.
        </p>

        {/* Form */}
        <form onSubmit={handleSubmit}>

          {/* Email */}
          <div className="login-field">
            <label htmlFor="register-email">
              Email
            </label>

            <input
              id="register-email"
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              disabled={loading}
              autoComplete="email"
            />
          </div>

          {/* Password */}
          <div className="login-field">
            <label htmlFor="register-password">
              Password
            </label>

            <input
              id="register-password"
              type="password"
              placeholder="Create a password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              disabled={loading}
              autoComplete="new-password"
            />
          </div>

          {/* Confirm Password */}
          <div className="login-field">
            <label htmlFor="register-confirm-password">
              Confirm Password
            </label>

            <input
              id="register-confirm-password"
              type="password"
              placeholder="Confirm your password"
              value={confirmPassword}
              onChange={(event) =>
                setConfirmPassword(event.target.value)
              }
              disabled={loading}
              autoComplete="new-password"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          {/* Success */}
          {success && (
            <div className="login-success">
              {success}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? "CREATING..." : "CREATE ACCOUNT"}

            {!loading && (
              <span>↗</span>
            )}
          </button>
        </form>

        {/* Back to Login */}
        <button
          type="button"
          className="login-back-button"
          onClick={onBackToLogin}
          disabled={loading}
        >
          ← BACK TO LOGIN
        </button>

        {/* Footer */}
        <div className="login-footer">
          SECURE ACCESS · CODEX INTELLIGENCE
        </div>

      </div>
    </div>
  );
}

export default Register;