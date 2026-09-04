import React, { useState } from "react";

const API_URL = "http://127.0.0.1:8000";

function Login({ onLogin, onCreateAccount }) {
  const [mode, setMode] = useState("login");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  // =========================================================
  // RESET ALL MESSAGES
  // =========================================================

  const clearMessages = () => {
    setError("");
    setMessage("");
  };

  // =========================================================
  // LOGIN
  // =========================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    clearMessages();

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

  // =========================================================
  // OPEN FORGOT PASSWORD
  // =========================================================

  const openForgotPassword = () => {
    clearMessages();
    setPassword("");
    setOtp("");
    setNewPassword("");
    setConfirmPassword("");

    setMode("forgot");
  };

  // =========================================================
  // SEND OTP
  // =========================================================

  const handleSendOTP = async (event) => {
    event.preventDefault();

    clearMessages();

    if (!email.trim()) {
      setError("Please enter your email address.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/api/forgot-password`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email.trim(),
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        setError(
          data.message || "Unable to send OTP."
        );
        return;
      }

      setMessage(
        "OTP sent successfully. Check your email."
      );

      setMode("otp");
    } catch (error) {
      console.error("Send OTP error:", error);

      if (
        error instanceof TypeError &&
        error.message === "Failed to fetch"
      ) {
        setError(
          "Unable to connect to the server. Please make sure the backend is running."
        );
      } else {
        setError(
          "Unable to send OTP. Please try again."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // VERIFY OTP
  // =========================================================

  const handleVerifyOTP = async (event) => {
    event.preventDefault();

    clearMessages();

    if (!otp.trim()) {
      setError("Please enter the OTP.");
      return;
    }

    if (!/^\d{6}$/.test(otp.trim())) {
      setError("OTP must contain exactly 6 digits.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/api/verify-otp`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email.trim(),
            otp: otp.trim(),
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        setError(
          data.message || "Invalid OTP."
        );
        return;
      }

      setMessage("OTP verified successfully.");
      setMode("reset");
    } catch (error) {
      console.error("OTP verification error:", error);

      if (
        error instanceof TypeError &&
        error.message === "Failed to fetch"
      ) {
        setError(
          "Unable to connect to the server. Please make sure the backend is running."
        );
      } else {
        setError(
          "Unable to verify OTP. Please try again."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // RESET PASSWORD
  // =========================================================

  const handleResetPassword = async (event) => {
    event.preventDefault();

    clearMessages();

    if (!newPassword || !confirmPassword) {
      setError("Please enter and confirm your new password.");
      return;
    }

    if (newPassword.length < 6) {
      setError(
        "Password must be at least 6 characters."
      );
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/api/reset-password`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email.trim(),
            otp: otp.trim(),
            new_password: newPassword,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        setError(
          data.message || "Unable to reset password."
        );
        return;
      }

      setMessage(
        "Password reset successfully. You can now sign in."
      );

      setMode("success");
    } catch (error) {
      console.error("Password reset error:", error);

      if (
        error instanceof TypeError &&
        error.message === "Failed to fetch"
      ) {
        setError(
          "Unable to connect to the server. Please make sure the backend is running."
        );
      } else {
        setError(
          "Unable to reset password. Please try again."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // BACK TO LOGIN
  // =========================================================

  const backToLogin = () => {
    clearMessages();

    setMode("login");

    setOtp("");
    setNewPassword("");
    setConfirmPassword("");
    setPassword("");
  };

  // =========================================================
  // RENDER LOGIN
  // =========================================================

  const renderLogin = () => {
    return (
      <>
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
              onChange={(event) =>
                setEmail(event.target.value)
              }
              disabled={loading}
            />
          </div>

          <div className="login-field">
            <label>Password</label>

            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              disabled={loading}
            />
          </div>

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? "SIGNING IN..." : "SIGN IN"}

            {!loading && <span>↗</span>}
          </button>
        </form>

        <button
          type="button"
          className="forgot-password-button"
          onClick={openForgotPassword}
          disabled={loading}
        >
          FORGOT PASSWORD?
        </button>

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
      </>
    );
  };

  // =========================================================
  // RENDER FORGOT PASSWORD
  // =========================================================

  const renderForgotPassword = () => {
    return (
      <>
        <div className="reset-step">
          <span>01</span>
          ACCOUNT RECOVERY
        </div>

        <h1>
          Reset your
          <br />
          <span>password.</span>
        </h1>

        <p className="login-subtitle">
          Enter your registered email and we'll send you
          a secure verification code.
        </p>

        <form onSubmit={handleSendOTP}>
          <div className="login-field">
            <label>Email</label>

            <input
              type="email"
              placeholder="Enter your registered email"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              disabled={loading}
            />
          </div>

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          {message && (
            <div className="login-success">
              {message}
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? "SENDING OTP..." : "SEND OTP"}

            {!loading && <span>↗</span>}
          </button>
        </form>

        <button
          type="button"
          className="reset-back-button"
          onClick={backToLogin}
          disabled={loading}
        >
          ← BACK TO LOGIN
        </button>
      </>
    );
  };

  // =========================================================
  // RENDER OTP
  // =========================================================

  const renderOTP = () => {
    return (
      <>
        <div className="reset-step">
          <span>02</span>
          VERIFY IDENTITY
        </div>

        <h1>
          Check your
          <br />
          <span>email.</span>
        </h1>

        <p className="login-subtitle">
          We sent a 6-digit verification code to your
          registered email address.
        </p>

        <form onSubmit={handleVerifyOTP}>
          <div className="login-field">
            <label>Verification Code</label>

            <input
              type="text"
              inputMode="numeric"
              maxLength="6"
              placeholder="Enter 6-digit OTP"
              value={otp}
              onChange={(event) =>
                setOtp(
                  event.target.value
                    .replace(/\D/g, "")
                    .slice(0, 6)
                )
              }
              disabled={loading}
            />
          </div>

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          {message && (
            <div className="login-success">
              {message}
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? "VERIFYING..." : "VERIFY OTP"}

            {!loading && <span>↗</span>}
          </button>
        </form>

        <button
          type="button"
          className="reset-back-button"
          onClick={() => {
            clearMessages();
            setMode("forgot");
            setOtp("");
          }}
          disabled={loading}
        >
          ← CHANGE EMAIL
        </button>
      </>
    );
  };

  // =========================================================
  // RENDER RESET PASSWORD
  // =========================================================

  const renderResetPassword = () => {
    return (
      <>
        <div className="reset-step">
          <span>03</span>
          CREATE PASSWORD
        </div>

        <h1>
          Choose a new
          <br />
          <span>password.</span>
        </h1>

        <p className="login-subtitle">
          Create a new password for your CODEX account.
        </p>

        <form onSubmit={handleResetPassword}>
          <div className="login-field">
            <label>New Password</label>

            <input
              type="password"
              placeholder="Enter new password"
              value={newPassword}
              onChange={(event) =>
                setNewPassword(event.target.value)
              }
              disabled={loading}
            />
          </div>

          <div className="login-field">
            <label>Confirm Password</label>

            <input
              type="password"
              placeholder="Confirm new password"
              value={confirmPassword}
              onChange={(event) =>
                setConfirmPassword(event.target.value)
              }
              disabled={loading}
            />
          </div>

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          {message && (
            <div className="login-success">
              {message}
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? "RESETTING..." : "RESET PASSWORD"}

            {!loading && <span>↗</span>}
          </button>
        </form>
      </>
    );
  };

  // =========================================================
  // RENDER SUCCESS
  // =========================================================

  const renderSuccess = () => {
    return (
      <>
        <div className="reset-success-icon">
          ✓
        </div>

        <div className="reset-step">
          <span>04</span>
          COMPLETE
        </div>

        <h1>
          You're all
          <br />
          <span>set.</span>
        </h1>

        <p className="login-subtitle">
          Your password has been successfully updated.
          You can now sign in with your new password.
        </p>

        {message && (
          <div className="login-success">
            {message}
          </div>
        )}

        <button
          type="button"
          className="login-button"
          onClick={backToLogin}
        >
          BACK TO LOGIN
          <span>↗</span>
        </button>
      </>
    );
  };

  // =========================================================
  // MAIN UI
  // =========================================================

  return (
    <div className="login-page">
      <div className="login-glow login-glow-one"></div>
      <div className="login-glow login-glow-two"></div>

      <div className="login-card">

        <div className="login-brand">
          CODEX.
        </div>

        {mode === "login" && (
          <div className="login-eyebrow">
            <span></span>
            DOCUMENT INTELLIGENCE
          </div>
        )}

        {mode === "login" && renderLogin()}

        {mode === "forgot" &&
          renderForgotPassword()}

        {mode === "otp" &&
          renderOTP()}

        {mode === "reset" &&
          renderResetPassword()}

        {mode === "success" &&
          renderSuccess()}

        {mode === "login" && (
          <div className="login-footer">
            SECURE ACCESS · CODEX INTELLIGENCE
          </div>
        )}

        {mode !== "login" && (
          <div className="login-footer">
            SECURE RECOVERY · CODEX INTELLIGENCE
          </div>
        )}

      </div>
    </div>
  );
}

export default Login;