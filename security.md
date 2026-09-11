# Security Overview

This document summarizes the security controls currently implemented in this repository as of September 2026.

It is intended to provide a clear snapshot of what is already built, what is partially implemented, and what still needs to be added before the application is considered production-grade.

## Current Security Features

### 1. Password hashing

Implemented in `backend/auth.py`.

Current controls:
- Passwords are hashed with Argon2 via `argon2-cffi`.
- Existing legacy SHA-256 hashes are detected and upgraded to Argon2 on the next successful login.
- Password verification uses constant-time comparison logic where applicable.

Benefits:
- Stronger password hashing than unsalted or weak SHA-256-only storage.
- Allows migration from older stored hashes without forcing a password reset.

### 2. Server-side sessions with cookie-based persistence

Implemented in `backend/auth.py` and `backend/main.py`.

Current controls:
- Server-side session records are stored in SQLite in a `sessions` table.
- A session ID is issued on login and stored in an `httponly` cookie.
- Session expiration is enforced using server-side `expires_at` timestamps.
- Session invalidation is supported via logout and session cleanup.
- Frontend session restoration is handled by calling `/api/session` on load.

Benefits:
- Session state is not stored only in browser localStorage.
- Server-side session validation allows revocation and expiry management.

### 3. Login rate limiting / brute-force protection

Implemented in `backend/auth.py` and `backend/main.py`.

Current controls:
- Failed login attempts are tracked per IP address and email.
- Login attempts are blocked after a configurable threshold is reached within a configurable time window.
- A clear retry message is returned when a client is rate limited.
- The backend now includes an HTTP middleware rate limiter for general request throttling.

Current configuration:
- `LOGIN_ATTEMPT_WINDOW_SECONDS` defaults to `900`
- `MAX_LOGIN_ATTEMPTS` defaults to `5`
- `RATE_LIMIT_WINDOW_SECONDS` defaults to `60`
- `RATE_LIMIT_MAX_REQUESTS` defaults to `120`

Benefits:
- Reduces exposure to brute-force password attacks and noisy request floods.
- Provides a basic layer of abuse mitigation.

Notes:
- The current limiter is in-memory and local to the running process.
- It is useful for development and basic protection, but not sufficient for multi-instance production deployments.

### 4. Logout and session invalidation

Implemented in `backend/main.py`.

Current controls:
- `POST /api/logout` invalidates the server-side session.
- The client cookie is removed with `delete_cookie`.
- Frontend logout clears local UI state after the server response.

Benefits:
- Users can actively terminate sessions.
- Invalidation is supported on the server side, which is important for security and account hygiene.

### 5. CORS hardening

Implemented in `backend/main.py`.

Current controls:
- CORS is no longer fully open.
- Allowed origins are loaded from `FRONTEND_ORIGINS` environment configuration.
- `allow_credentials=True` is preserved only for the configured origins.

Benefits:
- Reduces the chance of cross-origin misuse compared to wildcard `*` origins.

### 6. OTP-based password reset flow

Implemented in `backend/auth.py` and exposed through `backend/main.py`.

Current controls:
- Password reset requests generate temporary OTPs.
- OTPs expire after a fixed interval.
- OTPs are stored server-side and checked before allowing a password reset.
- Email sending is performed through SMTP.

Benefits:
- Provides an additional recovery mechanism beyond direct password changes.

### 7. Basic audit logging for login activity

Implemented in `backend/main.py` and `backend/auth.py`.

Current controls:
- Successful logins insert a record into the `login_activity` table.
- Admin dashboard endpoints expose recent login records and user totals.

Benefits:
- Provides a basic audit trail for login events.

### 8. Auth-aware frontend state management

Implemented in `frontend/src/App.jsx`.

Current controls:
- Frontend now restores auth state via `/api/session`.
- Session-backed requests send `credentials: "include"`.
- The UI now uses the server session instead of raw localStorage persistence for login state.

Benefits:
- Helps align frontend behavior with server-side session validity.

## Current Limitations / Gaps

The following important gaps still remain and should be treated as known limitations.

### 1. Centralized auth enforcement is not fully implemented

Current state:
- Sessions are created and restored.
- Some routes still rely on manual checks or client-provided values rather than a single centralized auth dependency.

Remaining issue:
- Sensitive endpoints should be protected by one shared auth guard / dependency layer, rather than ad hoc logic.

### 2. Admin authorization is still weak

Current state:
- The admin check in `backend/main.py` is still based on comparing the user email to a configured admin email.

Remaining issue:
- This is not a real role-based authorization model.
- Production systems should use explicit roles/permissions and protected route dependencies.

### 3. Event and incident tracking is still limited

Current state:
- The application records login events in `login_activity`.
- There is no comprehensive event bus, audit trail, or incident tracking for actions such as:
  - password reset requests
  - failed password reset attempts
  - PDF uploads
  - research requests
  - admin account changes
  - suspicious rate-limit events

Remaining issue:
- Event tracking needs to expand beyond simple login history to support operational monitoring and security investigations.

### 4. Rate limiting is still in-memory

Current state:
- Request throttling is implemented in-process.

Remaining issue:
- This is not suitable for multi-instance production deployment.
- A distributed rate-limiter (for example Redis-backed) is recommended for scale-out and reliability.

### 5. Scraping and URL-fetching are still high-risk areas

Current state:
- The research pipeline and scraping tools can fetch external URLs.

Remaining issue:
- This exposes the system to SSRF and abuse risks unless strict domain allowlists, URL validation, and network controls are added.

### 6. Upload handling needs production hardening

Current state:
- PDF uploads are accepted and indexed.

Remaining issue:
- There are no strong upload size limits, malware scanning, MIME validation, or resource caps yet.

### 7. Security observability still needs to improve

Current state:
- Basic login activity is stored.

Remaining issue:
- The project does not yet have structured, centralized incident/event logging, alerting, or a first-class monitoring pipeline.

## Recommended Next Security Priorities

### Priority 1: Central auth enforcement
- Add a shared dependency for authenticated requests.
- Enforce auth consistently for all protected endpoints.
- Move toward explicit role checks for admin-only operations.

### Priority 2: Production-grade rate limiting
- Replace in-memory limiter with Redis-backed rate limiting.
- Add endpoint-specific limits for login, password reset, PDF upload, and research requests.
- Apply stronger throttling rules per IP and per user account.

### Priority 3: Event and incident tracking
- Implement a structured event log for:
  - authentication attempts
  - password reset actions
  - PDF upload activity
  - admin actions
  - rate-limit violations
  - suspicious request patterns
- Make the event store queryable for investigation and alerting.

### Priority 4: Hardening for scraping and uploads
- Add URL allowlisting and safe-fetch logic.
- Add file upload size and content validation.
- Introduce resource limits and malicious-content checks for documents.

## Summary

The repository already includes several useful security foundations:
- Argon2 password hashing
- server-side session management
- cookie-based persistence
- login throttling
- logout/invalidation support
- CORS tightening
- OTP-based password recovery
- basic login auditing

However, it is not yet a fully production-grade secure application. The biggest remaining work is around:
- centralized auth enforcement,
- role-based authorization,
- production-grade distributed rate limiting,
- and broader event/incident tracking beyond login history.
