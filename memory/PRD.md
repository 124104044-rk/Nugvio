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
- 2026-06: Investment Dashboard shipped — portfolio holdings tracker (MF/Stock/Gold/FD/Bond/Crypto, CRUD + price update), SIP tracker (CRUD, pause/resume), summary stats (invested/current/gain/monthly SIP), allocation breakdown with best/worst performers, 10-year compounding SIP projection chart, seeded demo data. E2E tested 100% (iteration_2.json)
- 2026-06: Financial OS upgrade shipped (7 features, E2E tested 100% - iteration_3.json):
  - AI Action Center (/app/actions) — "What should I do today?" insights (spending spikes, savings potential, emergency gap, goal misses, debt interest cost, no-SIP), each with an Action button
  - Health Score Breakdown — component points (Savings/25, Spending/20, Debt/20, Emergency/15, Investments/10, Discipline/10) + "Get to {target}" top-3 actions; weights updated (emergency 15%, investments 10%)
  - Emergency Fund Planner (/app/emergency) — essentials calc, 3-12 month cushion selector, gap, 6/12/18-month saving plans, goal create/top-up
  - Net Worth Dashboard (/app/networth) — manual assets (bank/cash) CRUD + auto-pulled investments & goal savings vs debts; cashflow forecast now starts from real bank balance
  - Smart Alerts — unified bell (Red risk / Yellow spending / Green wins) via /api/alerts
  - Goal Autopilot — monthly commit + SIP linking per goal, ahead/on-track/behind status, projected delay
  - Weekly Money Recap (/app/recap) — saved/spent/budget %/goal progress/streak/health delta + copy-to-share; contributions now logged; health snapshots stored
  - Sidebar reorganized into Overview/Spend/Wealth/Grow sections
- 2026-06: Coach Superpowers — AI Coach now receives a live financial snapshot (health breakdown, totals, net worth, investments, emergency fund, top Action Center insights) injected into every chat prompt; Coach page shows "Sees your live numbers" chip and dynamic suggestion chips built from the user's top insights. Verified multi-turn grounded replies with real numbers.

## Backlog / Roadmap
- P1 (user-confirmed, later): Push Nudges — email/push reminders from Smart Alerts (retention; Phase 2)
- P1: CSV/statement upload with AI parse; Retirement Planner; Family Dashboard
- P2: Bank/UPI integration via Account Aggregator framework; Merchant partnerships for NugPoints
- P3: Co-branded FinPilot/Nugvio card (partner bank); Behavioural analytics
- P4: Streaming AI Coach via SSE (currently non-streaming); Push notifications for nudges

## Next Action Items
- Rewards Store partner perks polish (user: add after real users)
- CSV/statement upload with AI parse (P1)
- Split server.py into router modules (tech debt, ~1600 lines)
