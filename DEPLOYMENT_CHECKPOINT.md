# NUGVIO — COMPETITION DEPLOYMENT CHECKPOINT

## Goal

Get a public live URL for the competition as quickly as possible.

Do NOT change NUGVIO product logic, UI, financial calculations, or existing features unnecessarily.

## Git

GitHub:
https://github.com/124104044-rk/Nugvio

Local repository:
D:\NUDGEVIO\Nugvio

Known-good branch:
main

Competition branch:
competition-deployment

Current branch should be:
competition-deployment

Main must remain untouched.

## Verified facts

### Authentication

backend/server.py contains independent email/password endpoints:

POST /auth/register
POST /auth/login
POST /auth/logout
GET /auth/me

These are implemented in the NUGVIO backend and are NOT inherently dependent on Emergent LLM.

Google login is Emergent-dependent through:

/auth/google/session

which calls an Emergent session-data endpoint.

### MongoDB

Backend uses:

from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

The database layer uses standard MongoDB/Motor APIs.

Current MONGO_URL is Emergent-managed/internal in the Emergent environment.

Collections found: 17
users
user_sessions
expenses
budgets
goals
contributions
nug_events
debts
debt_payments
health_snapshots
recurring
holdings
sips
assets
coach_messages
lessons
checkins

### Emergent-specific dependencies

backend/server.py includes:

from emergentintegrations.llm.chat import LlmChat, UserMessage

EMERGENT_LLM_KEY

Emergent OAuth session-data URL.

Do NOT replace the Emergent LLM unless technically necessary for external deployment.

Gemini was discussed as a possible Cline provider only.
It is NOT an instruction to replace NUGVIO's LLM.

### Current deployment strategy

Competition branch may replace ONLY infrastructure that is actually required to run outside Emergent.

Potential external architecture:

GitHub
→ Render backend
→ external MongoDB if required
→ frontend on Vercel/Render

Possible temporary competition approach:
- Keep email/password auth
- Google login may be temporarily disabled if necessary
- Preserve NUGVIO features/business logic

## Cline rules

Cline must NOT make independent architectural decisions.

Workflow:

Cline proposes
→ user shows proposal
→ ChatGPT/user decides
→ Cline executes only approved changes.

Never approve:
- database deletion/reset
- force push
- destructive migrations
- unrelated rewrites
- replacing NUGVIO product logic
- changing authentication without approval

## Important previous mistakes

Cline repeatedly:
- used wrong paths
- confused Cline's Gemini provider with NUGVIO's LLM provider
- incorrectly proposed google-cloud-dialogflow
- incorrectly proposed package "google"
- proposed unsafe/simple text replacement of emergentintegrations
- produced inaccurate dependency conclusions

Therefore all future Cline changes must be reviewed before execution.

## Current status

No code migration has been intentionally approved/applied for the competition deployment yet.

Next task:
Determine the MINIMUM actual infrastructure changes needed to obtain a public live URL, then implement them one at a time.