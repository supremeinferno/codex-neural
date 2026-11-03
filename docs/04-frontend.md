# 4. Frontend

The frontend is a single-page React 19 app built with Vite. It lives in `frontend/`. There is no router library: `App.jsx` decides which screen to show using state.

## Entry points

| File | Purpose |
| --- | --- |
| `index.html` | The HTML page. Sets the title, description, favicon (a gold "C") and loads `src/main.jsx`. |
| `src/main.jsx` | Mounts `<App />` into `#root`. |
| `src/config.js` | Exports `API_URL` = `VITE_API_URL` from `.env`, or `http://127.0.0.1:8000`. Every `fetch` uses it. |
| `src/index.css` | Imports all style files in order. |

## How screens are chosen

```
App
 ├─ not logged in
 │    ├─ authPage = "login"     → <Login>
 │    ├─ authPage = "register"  → <Register>
 │    └─ authPage = "forgot-password" → <ForgotPassword>
 └─ logged in
      ├─ activePage = "history"     → <ChatHistory>
      ├─ activeTab  = "individual"  → <Individual>
      ├─ activeTab  = "dashboard"   → <Dashboard>   (admins only)
      └─ activeTab  = "nexus"       → research page (inside App.jsx)
   + <NavigationDrawer> sidebar on every logged-in screen
```

## Components

### `App.jsx` — app shell and research page

The largest file. It holds the shared state and renders the research page itself.

**Important state**

| State | Meaning |
| --- | --- |
| `user`, `token`, `isLoggedIn` | The signed-in user and session token. Saved in `sessionStorage` so they survive a refresh but are cleared when the tab closes. |
| `activeTab` | `"nexus"`, `"individual"` or `"dashboard"`. Also saved in `sessionStorage`. |
| `activePage` | `"workspace"` or `"history"`. |
| `conversationId`, `openedConversation` | The chat being shown, for saving new messages and reopening old ones. |
| `historyVersion` | A counter. Bumping it tells the sidebar and history page to reload the chat list. |
| `topic`, `report`, `loading`, `error`, `activeStage` | The research form and its result. |

**Key functions**

| Function | What it does |
| --- | --- |
| `handleLogin(user, token)` | Saves the session and opens the research tab. |
| `handleLogout()` | Calls `POST /api/logout`, clears all state and `sessionStorage`. |
| Session check (`useEffect` on mount) | Calls `GET /api/session`; signs out if the token is no longer valid. |
| Research submit | Creates a chat, saves the topic, calls `POST /api/research` with a 3-minute timeout, shows the report, saves it. |
| Copy / Download | Copies the report to the clipboard, or downloads it as `<topic-slug>.md`. |
| `startNewChat()` | Clears the current chat and returns to the research tab. |
| `openSavedChat(chat)` | Loads a saved chat and switches to the right tab for its `kind`. |
| `Navbar()`, `Background()` | Shared top bar (with mode tabs and menu button) and animated background. |

**UI details:** suggested topic chips (`SUGGESTED_TOPICS`), a scrolling ticker (`TICKER_ITEMS`), and a four-stage progress display (Research, Read, Write, Critique) that advances on a timer while the request runs.

`isAdmin` compares the user's email with `ADMIN_EMAIL`. It only decides whether the Dashboard tab is shown. The backend enforces admin access separately.

### `login.jsx`

Email and password form. Calls `POST /api/login`, then `onLogin(user, token)`. Shows a clear message if the backend cannot be reached ("Failed to fetch"). Links to Register and Forgot Password.

### `register.jsx`

Email, password and confirm-password form. Checks in the browser that all fields are filled, the password is at least 6 characters, and both passwords match, then calls `POST /api/register`. The backend repeats the length check.

### `Forgotpassword.jsx`

A three-step wizard controlled by `step`:

1. Enter email → `POST /api/forgot-password`
2. Enter the 6-digit code → `POST /api/verify-otp`
3. Enter and confirm the new password → `POST /api/reset-password`

The Back button moves one step back.

### `Individual.jsx` — PDF analyzer

| Part | What it does |
| --- | --- |
| File picker | Accepts only `.pdf`. Picking a new file clears the previous chat. |
| Upload | `POST /api/individual/upload` as `multipart/form-data`. Shows pages and chunks when indexed. |
| Chat | Creates a `pdf` chat on the first question, saves each message, calls `POST /api/individual/chat`, and shows the answer as Markdown with page/section source chips. |
| View PDF | Downloads the file with the bearer token (`GET /api/individual/{id}/file`), turns it into a blob URL, and shows it in a side panel. A download button is included. The blob URL is released when no longer needed. |
| Reopen | If `openedConversation` is a PDF chat, reloads its document info and messages. |

### `Dashboard.jsx` — admin dashboard

Loads `GET /api/admin/dashboard` with the bearer token. Shows stat cards (total users, total logins), a users table, and a recent-logins table, each with a Refresh button. Delete actions ask for confirmation with `window.confirm` and then call the matching `DELETE` route.

### `NavigationDrawer.jsx` — sidebar

Slide-in panel with "New chat", the recent chats list, "View all & manage chats", a disabled Settings item (marked "SOON"), Sign out, and the user's email. Reloads chats each time it opens or `version` changes. Closes on Escape or by clicking the dark scrim. Uses `inert` and `aria-hidden` when closed so keyboard users cannot tab into it.

### `ChatHistory.jsx` — history page

Lists every saved chat with its type (Research or Document) and date. Each chat can be opened, renamed inline, or deleted after confirmation. Deleting the open chat starts a new one.

### `Atmosphere.jsx` — background

Purely decorative: glows, a moving grid, 70 floating particles with random positions, shooting stars and energy cores. Marked `aria-hidden`.

## Styles (`src/styles/`)

| File | Contents |
| --- | --- |
| `globals.css` | Design tokens: colours (black, off-white, gold), fonts (DM Sans, Manrope, JetBrains Mono), radii, the hard offset shadow, easing curves. Base element styles. |
| `system.css` | Shared states: tactile buttons (press/hover offset), focus rings, the ticker, reduced-motion handling. |
| `atmosphere.css` | Background animation. |
| `main.css` | Research page layout, report display, stage progress. |
| `auth.css` | Login, register and forgot-password pages. |
| `individual.css` | PDF analyzer layout, chat bubbles, PDF side panel. |
| `dashboard.css` | Admin stat cards and tables. |
| `navbar.css` | Top bar and mode tabs. |
| `navigation.css` | Sidebar drawer and history page. |

To change the look of the whole app, start with the variables in `globals.css`.

## Scripts

```bash
npm run dev      # start the dev server (http://localhost:5173)
npm run build    # production build into dist/
npm run preview  # serve the production build locally
```

Next: [05-api-reference.md](05-api-reference.md)
