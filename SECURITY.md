# NugVio security notes

Secrets live only in the Render environment (`GEMINI_API_KEY`, `JWT_SECRET`, `MONGO_URL`, `DB_NAME`).
Never commit `.env` files, keys, passwords or tokens. The frontend holds no secrets: its only build
variable is `REACT_APP_BACKEND_URL`, which is public.

## Limits (backend/server.py)

| Protection | Default | How to change |
|---|---|---|
| AI Coach messages per user per day (resets at midnight IST) | 5 | `COACH_DAILY_LIMIT` env var |
| AI Coach messages per day for the demo account (`ADMIN_EMAIL`) | 50 | `COACH_DEMO_DAILY_LIMIT` env var |
| AI Coach message length | 1,000 characters | `COACH_MAX_CHARS` (keep `frontend/src/pages/Coach.jsx` in step) |
| Failed logins for one email from one address | 5 per 15 min | `LOGIN_MAX_FAILS_PER_ACCOUNT_IP` |
| Failed logins from one address, any email | 50 per 15 min | `LOGIN_MAX_FAILS_PER_IP` |
| Password length for new accounts | 8–128 characters | `RegisterIn` |

Only successful AI Coach replies count, so a Gemini outage doesn't use up a user's messages.
The login lockout is per email *and* address, so nobody can lock a user (or the public demo
account) out from another network. It is held in memory and resets when the server restarts.
The client address is the last `X-Forwarded-For` entry, which Render adds itself.

## Frontend (frontend/vercel.json, frontend/craco.config.js)

- Security headers on every page: Content-Security-Policy, X-Frame-Options, X-Content-Type-Options,
  Referrer-Policy, Permissions-Policy. Vercel adds HSTS.
- The CSP allows scripts only from the site itself. **If you add a new external service** (another
  API, image host, analytics, font), add its address to the matching directive in `vercel.json`,
  for example a new backend URL to `connect-src`.
- Production builds don't publish source maps.
- No third-party analytics or session recording (the Emergent PostHog snippet was removed).

## Known, accepted risks

- The login token is kept in `localStorage`, because the frontend (vercel.app) and backend
  (onrender.com) are different sites and browsers block cross-site cookies. The CSP limits what
  scripts can run. Revisit if both move to one custom domain.
- Logins last 7 days and logging out doesn't revoke a token already issued.
- Google sign-in is verified through Emergent's service (`demobackend.emergentagent.com`).
- The demo account's password is public by design. It has no admin privileges.
- The AI Coach sends a summary of the user's finances to Google Gemini; the Coach page says so.
