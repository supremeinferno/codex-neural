# Security Overview

This document summarizes the security posture of the repository as of September 2026 and reflects the work completed during the recent auth, rate-limiting, and auditing improvements.

It is intended to capture the current implemented controls, what has changed recently, and which issues still remain before the project can be considered production-grade.

## Current Security Features

### 1. Password hashing

Implemented in `backend/auth.py`.

Current controls:
- Passwords are hashed with Argon2 via `argon2-cffi`.
- Existing legacy SHA-256 hashes are detected and upgraded on the next successful login.
- Password verification uses Argon2 verification with safe error handling and legacy fallback support.

Benefits:
- Stronger password storage than weak SHA-256-only hashing.
- Safe migration path for older users without forcing an immediate password reset.

### 2. Server-side sessions with HttpOnly cookie persistence

Implemented in `backend/auth.py` and `backend/main.py`.

Current controls:
- The backend creates server-side session records in SQLite.
- Session IDs are stored in an `HttpOnly` cookie for browser persistence.
- Session expiration is enforced server-side with `expires_at` timestamps.
- Sessions can be invalidated and cleaned up through logout or expiry.
- Frontend session restoration is handled via `/api/session`.

Benefits:
- Session state is managed server-side rather than relying only on browser-held values.
- Sessions can be revoked immediately when required.

### 3. Centralized authentication and authorization

Implemented in `backend/auth.py` and enforced in `backend/main.py`.

Current controls:
- `verify_session` is used as the shared authentication dependency.
- `require_permissions(...)` provides reusable permission checks for protected routes.
- `verify_admin` now delegates through the centralized role/permission layer.
- The session object now includes both `role` and resolved `permissions`.

Benefits:
- Authorization is no longer spread across ad hoc route checks.
- Routes can be protected consistently through a shared dependency layer.

### 4. Role and permission model

Implemented in `backend/auth.py` and `backend/main.py`.

Current controls:
- Users now have a stored `role` field in the `users` table.
- The app supports a simple `user` / `admin` model with a permission map.
- Default permissions currently include:
  - `research`
  - `document_chat`
  - `document_upload`
- `admin` receives wildcard access via `*`.

Benefits:
- The application is no longer limited to a single hardcoded admin email check.
- Authorization can be broadened from a simple admin gate into a permission-based system.

### 5. Login throttling and request rate limiting

Implemented in `backend/auth.py` and `backend/main.py`.

Current controls:
- Failed login attempts are tracked per IP address and email.
- Login attempts are throttled after a configured threshold is reached.
- Request rate limiting is applied through an HTTP middleware.
- Rate limiting now supports multiple algorithms through configuration:
  - `sliding_window` (default)
  - `fixed_window`
  - `token_bucket`
- The limiter is Redis-ready and will use Redis if available.
- If Redis is unavailable, the backend falls back to in-memory rate limiting.

Current configuration examples:
- `LOGIN_ATTEMPT_WINDOW_SECONDS` defaults to `900`
- `MAX_LOGIN_ATTEMPTS` defaults to `5`
- `RATE_LIMIT_WINDOW_SECONDS` defaults to `60`
- `RATE_LIMIT_MAX_REQUESTS` defaults to `120`
- `RATE_LIMIT_ALGORITHM` defaults to `sliding_window`
- `RATE_LIMIT_USE_REDIS` defaults to `true`
- `REDIS_URL` defaults to `redis://localhost:6379/0`

Benefits:
- Reduces exposure to brute-force attacks and noisy request floods.
- Provides an upgrade path to a distributed production limiter.

### 6. Logout and session invalidation

Implemented in `backend/main.py`.

Current controls:
- `POST /api/logout` invalidates the server-side session.
- The client cookie is removed with `delete_cookie`.
- Frontend logout now clears local UI state after the server response.

Benefits:
- Users can actively terminate sessions.
- Session revocation is enforced on the server side.

### 7. OTP-based password reset flow

Implemented in `backend/auth.py` and exposed through `backend/main.py`.

Current controls:
- Password reset requests generate time-limited OTPs.
- OTPs are validated before allowing a password reset.
- OTPs are stored server-side and removed on successful completion.
- Password reset emails are sent through SMTP credentials from environment configuration.

Benefits:
- Improves user recovery options while keeping verification in the backend.

### 8. Audit/event logging

Implemented in `backend/auth.py` and `backend/main.py`.

Current controls:
- Security and operational events are stored in the `events` table.
- The logger records events such as:
  - login success / failure
  - logout
  - password reset requests and resets
  - OTP verification
  - rate-limit hits
  - admin operations such as user deletion and login-history cleanup
- Admin dashboard responses now include recent events in addition to login activity.

Benefits:
- Improves visibility for incident review and security investigation.
- Provides an audit trail beyond basic login history.

### 9. Auth-aware frontend state management

Implemented in `frontend/src/App.jsx` and related frontend files.

Current controls:
- Frontend restores auth state through `/api/session`.
- Requests now send `credentials: "include"` where necessary.
- UI state is aligned with server-side session validity.

Benefits:
- Reduces reliance on insecure client-only session assumptions.
- Better aligns frontend behavior with backend session verification.

### 10. CORS hardening

Implemented in `backend/main.py`.

Current controls:
- Allowed origins are loaded from `FRONTEND_ORIGINS` env configuration.
- `allow_credentials=True` is preserved only for configured origins.

Benefits:
- Avoids fully open cross-origin access.

## Recent Untracked / Completed Changes

The following work was completed recently and should be treated as part of the current security baseline:

- Centralized authentication and admin checking into shared auth dependencies.
- Added role and permission support to the backend.
- Added Redis-ready request rate limiting with algorithm selection and fallback behavior.
- Expanded event logging beyond login records.
- Updated the admin dashboard to expose role and event information.
- Added migration logic for legacy users and legacy admin email fallback handling.

## Current Limitations / Gaps

The following areas still require attention before this can be treated as fully production-grade.

### 1. Roles are still a simple model

Current state:
- The system supports `user` and `admin`, plus a static permission map.

Remaining issue:
- Permissions are still coded centrally and not yet fully admin-manageable from the database or dashboard.
- A more mature RBAC design would use a dedicated permission or role-assignment table.

### 2. Admin fallback still exists for older accounts

Current state:
- Older users can still be recognized through the configured admin email allowlist during migration.

Remaining issue:
- This should eventually be fully replaced by persisted role data for all users.

### 3. Redis is required for true shared rate limiting

Current state:
- The limiter is Redis-capable and will fall back to memory if Redis is unavailable.

Remaining issue:
- In production, Redis should be running and reachable for multi-instance consistency.
- Memory fallback is only suitable for development or single-instance deployments.

### 4. Upload handling needs stronger hardening

Current state:
- PDF uploads are accepted and indexed.

Remaining issue:
- There is no strong file-size cap, malware scan, content-type validation, or resource limit enforcement yet.

### 5. SSRF / safe-fetch protections are still incomplete

Current state:
- The research pipeline can fetch external URLs.

Remaining issue:
- Domain allowlisting, URL validation, and safer network controls are still required to reduce SSRF and external abuse risk.

### 6. Observability is still basic

Current state:
- Events are stored and visible from the admin dashboard.

Remaining issue:
- There is still no dedicated alerting, metrics pipeline, or richer incident investigation system.

### 7. Code organization remains large

Current state:
- The auth and main backend files have grown significantly.

Remaining issue:
- The project would benefit from splitting auth, session management, rate limiting, and event logging into separate modules or services.

## Recommended Next Security Priorities

### Priority 1: Harden the role and permission model
- Add persistent role and permission management in the database.
- Allow admin-driven assignment of permissions or roles.
- Remove the remaining email-based fallback after migration is complete.

### Priority 2: Deploy and validate Redis-backed rate limiting
- Run Redis in the deployment environment.
- Validate the shared limiter across multiple app instances.
- Tune rate limits per endpoint and per client class.

### Priority 3: Strengthen uploads and external fetch safety
- Add upload size limits and content validation.
- Introduce SSRF-safe URL restrictions and allowlists.
- Consider document scanning or content inspection where appropriate.

### Priority 4: Expand monitoring and incident response
- Add structured alerting for repeated failures and suspicious patterns.
- Track more security-related actions in a queryable, operationally useful way.
- Improve dashboard visibility and audit drill-down capabilities.

## Summary

The repository now includes a much stronger baseline than it had at the start of the project:
- Argon2 password hashing
- server-side session management
- centralized auth and authorization checks
- role and permission support
- Redis-ready rate limiting with multiple algorithms
- expanded audit/event logging
- improved frontend session handling

