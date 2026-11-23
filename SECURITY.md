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

Only genuine AI Coach answers count. The offline reply (Gemini failed or timed out) and the
fallback reply (no API key, or Gemini returned no usable text) are shown to the user as before
but never count, so outages and empty responses don't use up a user's messages.

Simultaneous Coach requests from one user can't exceed the allowance: each request first
reserves a slot under a per-user lock (successful replies today + requests in flight), and
releases it when it finishes, whether it succeeded, Gemini failed, timed out, was cancelled or
an error occurred. Each release also bumps a per-user completion counter; if it changes while
a request is counting, the request counts again, so a reply saved during a count is never
missed. The per-user lock and counter are kept for the life of the process (a few hundred
bytes per Coach user) so they can never be reset mid-count.

The Gemini call has two timeouts: 90 seconds per stage (httpx: connect, send, each read) and
an overall 100-second deadline, so a slowly trickling response can't keep a request running.

The login lockout is per email *and* address, so nobody can lock a user (or the public demo
account) out from another network. The client address is the last `X-Forwarded-For` entry,
which Render adds itself (earlier entries can be faked by the client).

## In-memory state: limitations

The failed-login counters, the in-flight Coach reservations and the per-user Coach locks and
completion counters are kept in the backend process's memory. The daily Coach count itself is read from MongoDB, so it survives restarts.

**Current deployment (checked 23 Nov 2026): one process on one instance.**
- Render service: Free plan. Free web services can't scale beyond a single instance.
- Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT` (no `--workers`).
- Startup logs show a single `Started server process` and no `Started parent process`,
  so uvicorn runs one worker.

**What this means today**
- Login counters reset whenever the server restarts: on each deploy, after a crash, and
  when the free instance spins down after 15 idle minutes. Each restart gives an attacker a
  fresh 5 attempts per account and address. An attacker can't trigger restarts, though, and
  their own requests keep the free instance awake, so in practice the reset only helps them
  around deploys or crashes.
- In-flight Coach reservations are lost on restart, which is harmless: the requests they
  belonged to are also gone.

**When this stops being safe**
- Running more than one instance (a paid plan with scaling) or more than one uvicorn worker.
  Each process keeps its own counters, so an attacker gets 5 attempts *per process*, and
  simultaneous Coach requests landing on different processes could exceed the allowance by
  up to one per extra process.
- Watch out: uvicorn reads `WEB_CONCURRENCY` when `--workers` isn't given, and Render sets
  `WEB_CONCURRENCY` by default on newer services based on the plan's CPUs. Upgrading the plan
  could silently start several workers. Before upgrading, add `--workers 1` to the start
  command, or move to the shared design below.

**Planned replacement (no new service, uses the existing MongoDB)**
- `login_failures` collection: one document per key (`acct:<email>|<ip>`, `ip:<ip>`), updated
  with an atomic `find_one_and_update` (`$push` the timestamp, `upsert`), plus a TTL index so
  entries expire after the 15-minute window.
- `coach_usage` collection: one document per user per IST day. Reserve with an atomic
  `find_one_and_update({user_id, day, reserved: {$lt: limit}}, {$inc: {reserved: 1}}, upsert)`;
  release with `$inc: -1` on failure. A TTL index removes old days.
- Both need new collections and indexes, so they belong in a later phase. Redis isn't needed.

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
