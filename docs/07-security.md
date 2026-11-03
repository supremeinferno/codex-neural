# 7. Security

This page lists what CODEX does to protect users, and what is still missing. Being honest about the gaps is part of good engineering.

## What is in place

### Passwords
- Hashed with **PBKDF2-HMAC-SHA256**, a random 16-byte salt per user, and **600,000 iterations** (the OWASP 2023 recommendation). The salt means two users with the same password get different hashes. The iteration count makes guessing slow.
- Compared with `secrets.compare_digest` (constant time), so timing does not leak how many characters matched.
- **Migration:** early accounts used plain, unsalted SHA-256. These still work, and the hash is replaced with PBKDF2 the next time the user signs in. No one had to reset their password.
- Minimum length of 6 characters, checked on both frontend and backend.

### Sessions
- A sign-in returns a random 32-byte token (`secrets.token_urlsafe`).
- The database stores only the **SHA-256 of the token**. Someone who reads the database cannot use the stored values to sign in.
- Tokens expire after **7 days**. Sign-out deletes the session on the server.
- The frontend keeps the token in `sessionStorage`, which is cleared when the tab closes.

### Admin access
- The backend identifies the admin from the **signed-in session** (`require_admin`).
- Earlier, admin routes trusted an `?email=` query parameter, so anyone could add `?email=<admin email>` and get admin access. This was fixed on 30 Oct 2026.
- The admin account cannot be deleted through the API.

### Password reset
- OTPs come from the `secrets` module (cryptographically secure), not `random`.
- Valid for **5 minutes**. Deleted after use, after expiry, or after **5 wrong attempts**, which stops brute-forcing the 900,000 possible codes.
- If the email fails to send, the stored code is removed.

### Data isolation
- Every chat query includes the user's ID, so one user cannot read, rename or delete another user's chat (they get 404).
- PDFs are tied to users through `user_documents`. Opening or chatting with a PDF you did not upload returns 404.
- The document ID must match `[a-f0-9]{12}`, which blocks path tricks like `../../.env`.
- Uploads are capped at 25 MB.

### AI safety
- The writer prompt tells the model to treat scraped text as data and ignore any instructions inside it (basic prompt-injection defence).
- The research and writer prompts forbid inventing URLs, studies or quotes.
- API keys stay on the server in `.env`, which is in `.gitignore`.

## Known gaps and suggested fixes

| Gap | Risk | Suggested fix |
| --- | --- | --- |
| `users.db` is committed to git | Email addresses and password hashes are visible to anyone with repository access | Add it to `.gitignore`, remove it from tracking (`git rm --cached`), and create the database on first run |
| `allow_origins=["*"]` CORS | Any website can call the API from a browser (it still needs a token) | List only the real frontend URLs |
| `ADMIN_EMAIL` is hard-coded in three files | Changing the admin requires a code change; easy to get out of sync | Add an `is_admin` or `role` column to `users` |
| No rate limiting on login and forgot-password | Password guessing and email spam | Limit requests per IP and per email |
| Forgot-password says when an email has no account | Lets someone check which emails are registered | Always reply "If an account exists, a code was sent" |
| OTP stored in plain text | Someone who reads the database during the 5-minute window could reset a password | Store a hash of the OTP |
| Expired sessions are never deleted | The table grows over time | Delete expired rows on sign-in or on a schedule |
| Token in `sessionStorage` | Readable by JavaScript if the site ever has an XSS bug | Use an `HttpOnly` cookie |
| Minimum password length is 6 | Weak passwords allowed | Raise to 8+ and check against common-password lists |
| No automated tests | Security fixes could break silently later | Add pytest tests for auth and ownership checks |

## Reporting a problem

If you find a security issue, tell the team privately instead of opening a public GitHub issue.

Next: [08-setup-and-deployment.md](08-setup-and-deployment.md)
