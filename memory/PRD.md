# Nugvio — Product Requirements Document

## Problem
Young Indians (18-30) juggle 5-7 finance apps and still lack real decision guidance. Existing apps show data; they don't tell users what to do next. Rewards apps also incentivize spending, not discipline.

## Vision
Nugvio is India's AI Financial Operating System — an AI coach that tells young Indians what to do next with money, and rewards discipline (saving, budgeting, killing debt, learning) instead of spending.

## Tagline
"Nudge The Youth" · "Track Less. Grow More."

## Target Users
Primary: 18-30 — college students, fresh grads, young professionals, freelancers.
Secondary: young families, self-employed, small business owners.

## Core Requirements (MVP shipped)
- JWT email/password auth (seeded demo user)
- Bento-grid Dashboard with Financial Health Score, top nudge, NugPoints wallet, cashflow, recent activity, goals
- AI Expense Tracker with rule-based + Gemini 3 Flash fallback categorization
- Budget Planner with live spend vs limit + colored progress
- Goal Planner with contribution flow (earns NugPoints)
- AI Financial Coach chatbot (Gemini 3 Flash, multi-turn, session-scoped, persisted in Mongo)
- Debt Optimizer with Snowball/Avalanche simulation + extra-payment slider
- Gamified Financial Literacy — 6 seeded lessons with quizzes, XP, NugPoints
- Tax Assistant — Old vs New regime educational estimator (FY 25-26 slabs)
- 30-day Cashflow Prediction with warning markers
- NugPoints reward system — earn for saving/lessons, redeem catalog

## Stack
- Backend: FastAPI + MongoDB (motor) + bcrypt + PyJWT + emergentintegrations (Gemini 3 Flash)
- Frontend: React 19 + React Router 7 + Tailwind + Recharts + Framer + Lucide + Sonner

## Design System
- "Friendly-Serious" warm paper light theme, Outfit + DM Sans + Kalam
- Palette: brand blue #2563EB, nudge orange #F97316, growth green #16A34A, celebration coral #F43F5E
- Left sidebar + bento grid dashboard, pill buttons, sharp 1px card borders

## Implementation Log
- 2026-01: MVP built end-to-end — auth, all 10 feature areas, seeded demo data, live LLM coach
- 2026-01: Added Budget Alerts (dedicated endpoint + top-right bell + inline banner on Budgets) and Recurring Transactions tracker (CRUD, pause/resume, post-now, run-all-due, 5 seeded samples)

## Backlog / Roadmap
- P1: CSV/statement upload with AI parse; Investment Dashboard; Retirement Planner; Family Dashboard
- P2: Bank/UPI integration via Account Aggregator framework; Merchant partnerships for NugPoints
- P3: Co-branded FinPilot/Nugvio card (partner bank); Behavioural analytics
- P4: Streaming AI Coach via SSE (currently non-streaming); Push notifications for nudges

## Next Action Items
- Run testing_agent_v3 for backend + frontend flows
- Add unit tests for tax calculator edge cases
