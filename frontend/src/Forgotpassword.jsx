import React, { useState } from "react";
import { API_URL } from "./config";
import Atmosphere from "./Atmosphere";

function ForgotPassword({ onBack }) {
  const [step, setStep] = useState(1);

  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // =====================================================
  // SEND OTP
  // =====================================================

  const handleSendOTP = async (event) => {
    event.preventDefault();

    setError("");
    setMessage("");

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

      const data = await response.json();

      if (!response.ok || !data.success) {
        setError(
          data.message || "Unable to send verification code."
        );
        return;
      }

      setMessage(
        "Verification code sent to your email."
      );

      setStep(2);

    } catch (error) {
      console.error("Forgot password error:", error);

      setError(
        "Unable to connect to the server. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // VERIFY OTP
  // =====================================================

  const handleVerifyOTP = async (event) => {
    event.preventDefault();

    setError("");
    setMessage("");

    if (!otp.trim()) {
      setError("Please enter the verification code.");
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

      const data = await response.json();

      if (!response.ok || !data.success) {
        setError(
          data.message || "Invalid verification code."
        );
        return;
      }

      setMessage("Code verified successfully.");
      setStep(3);

    } catch (error) {
      console.error("OTP verification error:", error);

      setError(
        "Unable to connect to the server. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // RESET PASSWORD
  // =====================================================

  const handleResetPassword = async (event) => {
    event.preventDefault();

    setError("");
    setMessage("");

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

      const data = await response.json();

      if (!response.ok || !data.success) {
        setError(
          data.message || "Unable to reset password."
        );
        return;
      }

      setMessage(
        "Password reset successfully. You can now sign in."
      );

      setTimeout(() => {
        onBack();
      }, 1500);

    } catch (error) {
      console.error("Password reset error:", error);

      setError(
        "Unable to connect to the server. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // BACK
  // =====================================================

  const handleBack = () => {
    setError("");
    setMessage("");

    if (step === 1) {
      onBack();
    } else if (step === 2) {
      setStep(1);
      setOtp("");
    } else {
      setStep(2);
      setNewPassword("");
      setConfirmPassword("");
    }
  };

  // =====================================================
  // UI
  // =====================================================

  return (
    <div className="login-page">

      <Atmosphere />

      <div className="login-card forgot-card">

        <div className="login-brand">
          CODEX.
        </div>

        <div className="login-eyebrow">
          <span></span>
          ACCOUNT RECOVERY
        </div>

        <h1>
          {step === 1 && (
            <>
              Forgot
              <br />
              <span>password?</span>
            </>
          )}

          {step === 2 && (
            <>
              Verify
              <br />
              <span>your code.</span>
            </>
          )}

          {step === 3 && (
            <>
              Create a
              <br />
              <span>new password.</span>
            </>
          )}
        </h1>

        <p className="login-subtitle">
          {step === 1 &&
            "Enter your registered email and we'll send you a verification code."}

          {step === 2 &&
            `Enter the 6-digit code sent to ${email}.`}

          {step === 3 &&
            "Choose a strong password to secure your CODEX account."}
        </p>


        {/* =================================================
            STEP 1
        ================================================= */}

        {step === 1 && (
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
                autoFocus
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
              {loading
                ? "SENDING..."
                : "SEND VERIFICATION CODE"}

              {!loading && <span>↗</span>}
            </button>

          </form>
        )}


        {/* =================================================
            STEP 2
        ================================================= */}

        {step === 2 && (
          <form onSubmit={handleVerifyOTP}>

            <div className="login-field">
              <label>Verification Code</label>

              <input
                type="text"
                inputMode="numeric"
                maxLength="6"
                placeholder="Enter 6-digit code"
                value={otp}
                onChange={(event) =>
                  setOtp(
                    event.target.value.replace(/\D/g, "")
                  )
                }
                disabled={loading}
                autoFocus
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
              {loading
                ? "VERIFYING..."
                : "VERIFY CODE"}

              {!loading && <span>↗</span>}
            </button>

          </form>
        )}


        {/* =================================================
            STEP 3
        ================================================= */}

        {step === 3 && (
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
                autoFocus
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
              {loading
                ? "RESETTING..."
                : "RESET PASSWORD"}

              {!loading && <span>↗</span>}
            </button>

          </form>
        )}


        {/* =================================================
            BACK BUTTON
        ================================================= */}

        <div className="login-create">

          <span>
            {step === 1
              ? "Remember your password?"
              : "Want to go back?"}
          </span>

          <button
            type="button"
            className="login-create-button"
            onClick={handleBack}
            disabled={loading}
          >
            {step === 1 ? "SIGN IN" : "BACK"}
          </button>

        </div>


        {/* =================================================
            FOOTER
        ================================================= */}

        <div className="login-footer">
          SECURE ACCOUNT RECOVERY · CODEX INTELLIGENCE
        </div>

      </div>
    </div>
  );
}

export default ForgotPassword;