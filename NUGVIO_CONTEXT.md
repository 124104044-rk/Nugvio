# NUGVIO — PROJECT CONTEXT

## WHAT IS NUGVIO?

NUGVIO is an AI-powered personal Financial Operating System for young adults.

Core idea:

NUGVIO does not just track money. It understands the user's financial situation and helps them decide what to do next.

## CORE WORKFLOW

Financial Data
→ Financial Health Score
→ Personalized Insight
→ AI Coach Explanation
→ Recommended Action
→ Track Improvement

The goal is to move users from:

Track → Understand → Decide → Act → Improve

## MAIN FEATURES

- Dashboard
- Income
- Expenses / Transactions
- Budgets
- Savings & Goals
- Debt Tracking
- Investment Tracking where implemented
- Financial Health Score
- AI Coach
- Financial Insights
- Charts / Analytics
- Settings / Profile
- Light / Dark / System theme
- Responsive desktop, tablet and mobile UI

## MAIN USP

NUGVIO is a decision layer on top of personal finance data.

Most finance tools help answer:

"Where did my money go?"

NUGVIO should additionally help answer:

"What does my financial situation mean?"
"What should I do next?"
"Can I afford this?"
"Should I save, invest, pay debt, or spend?"

## KEY DIFFERENTIATION

NUGVIO should NOT position itself simply as another expense tracker.

The differentiation is the integration of financial tracking, analysis, AI explanation, scenario planning and recommended actions into one workflow.

### Key differentiators

1. Personalized financial decision-making rather than only tracking.
2. "What Should I Do With My Money?" recommendations.
3. Financial What-If scenarios.
4. AI Coach that uses the user's financial context.
5. Financial Health Score connecting multiple financial signals.
6. Complete loop:
   Track → Understand → Decide → Act → Improve.

## POSITIONING

Do NOT claim that AI chat, budgeting, charts or expense tracking are completely new.

The defensible differentiation is:

Financial Data
+ Financial Context
+ Health Score
+ Personalized Insight
+ AI Explanation
+ Recommendation
+ Action
+ Improvement Tracking

## SIGNATURE EXPERIENCE

### "What Should I Do With My Money?"

NUGVIO should help users decide how available money could be allocated across appropriate priorities such as:

- Emergency savings
- Financial goals
- Debt repayment
- Investments
- Flexible spending

Recommendations should be explainable and based on the user's financial context.

NUGVIO should NOT automatically move money or execute transactions.

## FINANCIAL WHAT-IF

NUGVIO should support practical questions such as:

- Can I afford a ₹60,000 purchase?
- What happens if I save ₹5,000 more every month?
- Should I prioritize debt repayment or savings?
- How long will it take to reach my goal?
- Can I afford to invest ₹10,000 this month?

Use the user's available financial information for personalized calculations.

Do not provide speculative guaranteed investment advice.

## AI COACH

The AI Coach should NOT behave like a generic chatbot.

It should use relevant user financial context where available, including:

- Income
- Expenses
- Savings
- Debt
- Goals
- Investments

It should explain WHY an insight or recommendation is relevant.

## FINANCIAL HEALTH SCORE

The score should help users quickly understand their financial position.

Relevant contributing categories may include:

- Spending
- Savings
- Debt
- Emergency fund
- Goals
- Investments

Where possible, explain:

- Why the score changed
- What factors contributed
- 2–3 practical actions that could improve it

## INVESTMENT TRACKING

Investment functionality should remain simple and safe.

Supported tracking may include:

- Stocks
- Mutual funds
- ETFs

Possible information:

- Investment name
- Amount invested
- Current value
- Gain/loss
- Portfolio allocation

Do NOT build:

- Brokerage functionality
- Trade execution
- Buy/sell execution
- Trading platform
- Live market-data infrastructure unless already available

## TARGET USERS

Primary users:

- Students
- First-time salary earners
- Young professionals
- Young adults beginning to manage money independently

The product should use simple language and avoid unnecessary financial jargon.

## UI / UX

NUGVIO should feel:

- Clean
- Modern
- Professional
- Trustworthy
- Simple
- Premium

Prioritize:

- Clear visual hierarchy
- Important financial signals
- Recommended actions
- Consistent cards/components
- Useful charts
- Good loading/empty/error/success states
- Responsive desktop/tablet/mobile design
- Clean mobile navigation

Do not copy CRED, Walnut or another product's design.

## DEVELOPMENT RULES

NUGVIO is an EXISTING application.

DO NOT rebuild the application from scratch.

Before changing anything:

1. Inspect the existing implementation.
2. Understand the architecture.
3. Identify affected files and dependencies.
4. Explain the planned change.
5. Make the smallest safe change.
6. Test the result.
7. Report exactly what changed.

Always preserve:

- Existing working features
- Existing user data
- Database structure
- Financial calculations
- Business logic
- Authentication
- Existing AI functionality where possible

NEVER:

- Reset the database
- Delete user data
- Replace the database without approval
- Perform destructive migrations without a verified backup
- Expose API keys, passwords or secrets
- Add unnecessary integrations
- Add features only to increase feature count

When unsure about existing behavior, inspect the code first.

## SECURITY

Treat financial information as sensitive.

Never commit:

- API keys
- Passwords
- MongoDB connection strings
- `.env` files
- Authentication tokens
- Other secrets

Use environment variables / secure deployment secrets.

## CURRENT ARCHITECTURE NOTES

The application currently contains:

- React frontend
- FastAPI/Python backend
- MongoDB database
- Authentication
- AI functionality

Some current implementation details are Emergent-specific.

Before external deployment, identify and document all Emergent dependencies instead of replacing them blindly.

## LONG-TERM VISION

NUGVIO can eventually expand into a broader financial platform with:

- Bank partnerships
- Deeper financial connectivity
- More intelligent financial planning
- Financial products
- Potential NUGVIO Card

These are long-term goals and should not be added unnecessarily to the current application.

## PRODUCT PRINCIPLE

NUGVIO should feel like:

"An intelligent layer that turns personal financial data into better financial decisions."

Not simply:

"Another app that records expenses."

## YOUR ROLE AS AN AI BUILDER

Act as a senior software engineer and product engineer.

Never assume a feature is missing until you inspect the existing project.

Never rewrite working code unnecessarily.

Prioritize:

1. Data safety
2. Existing functionality
3. Reliability
4. Product coherence
5. UX quality
6. New features