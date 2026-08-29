from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import re
import json
import uuid
import logging
import bcrypt
import jwt as pyjwt
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict

# LLM
from emergentintegrations.llm.chat import LlmChat, UserMessage

# ------------------ CONFIG ------------------
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGO = "HS256"
ACCESS_TTL_MIN = 60 * 24 * 7  # 7 days for demo comfort
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="Nugvio API")
api = APIRouter(prefix="/api")

# ------------------ UTILS ------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def now_iso() -> str:
    return now_utc().isoformat()

def new_id() -> str:
    return str(uuid.uuid4())

def hash_pw(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_pw(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

def make_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": now_utc() + timedelta(minutes=ACCESS_TTL_MIN),
        "iat": now_utc(),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user

# ------------------ MODELS ------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=60)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ExpenseIn(BaseModel):
    description: str
    amount: float = Field(gt=0)
    category: Optional[str] = None
    date: Optional[str] = None  # ISO date

class ExpenseUpdate(BaseModel):
    category: Optional[str] = None

class BudgetIn(BaseModel):
    category: str
    monthly_limit: float = Field(gt=0)

class GoalIn(BaseModel):
    title: str
    target_amount: float = Field(gt=0)
    target_date: str  # YYYY-MM-DD
    icon: Optional[str] = "target"
    saved_amount: Optional[float] = 0.0

class GoalContribute(BaseModel):
    amount: float = Field(gt=0)

class DebtIn(BaseModel):
    name: str
    balance: float = Field(gt=0)
    apr: float = Field(ge=0)  # annual %
    min_payment: float = Field(gt=0)

class CoachMsgIn(BaseModel):
    session_id: str
    text: str

class LessonCompleteIn(BaseModel):
    lesson_id: str
    score: int = Field(ge=0, le=100)

class TaxIn(BaseModel):
    annual_income: float = Field(ge=0)
    regime: Literal["new", "old"] = "new"
    deductions_80c: float = Field(default=0, ge=0)
    hra: float = Field(default=0, ge=0)
    other_deductions: float = Field(default=0, ge=0)

class CategorizeIn(BaseModel):
    description: str
    amount: Optional[float] = None

class RecurringIn(BaseModel):
    name: str
    amount: float = Field(gt=0)
    category: str
    frequency: Literal["daily", "weekly", "monthly"]
    next_due: str  # YYYY-MM-DD
    active: bool = True

class RecurringUpdate(BaseModel):
    active: Optional[bool] = None
    amount: Optional[float] = None
    next_due: Optional[str] = None

CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Healthcare", "Entertainment", "Rent", "Investments", "Other"]

# ------------------ AUTH ------------------
@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    uid = new_id()
    doc = {
        "id": uid,
        "email": email,
        "name": body.name.strip(),
        "password_hash": hash_pw(body.password),
        "nug_points": 100,  # welcome bonus
        "streak_days": 1,
        "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    token = make_token(uid, email)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=ACCESS_TTL_MIN * 60, path="/")
    return {"id": uid, "email": email, "name": doc["name"], "nug_points": 100, "token": token}

@api.post("/auth/login")
async def login(body: LoginIn, response: Response):
    email = body.email.lower().strip()
    u = await db.users.find_one({"email": email})
    if not u or not verify_pw(body.password, u["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = make_token(u["id"], email)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=ACCESS_TTL_MIN * 60, path="/")
    return {"id": u["id"], "email": u["email"], "name": u["name"], "nug_points": u.get("nug_points", 0), "token": token}

@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ------------------ EXPENSES ------------------
KEYWORD_MAP = {
    "Food": ["zomato", "swiggy", "restaurant", "cafe", "coffee", "food", "dominos", "pizza", "meal", "lunch", "dinner", "breakfast", "starbucks", "mcdonald", "kfc", "chai", "biryani"],
    "Travel": ["uber", "ola", "rapido", "flight", "irctc", "train", "bus", "petrol", "fuel", "metro", "auto", "taxi", "indigo", "airasia", "makemytrip"],
    "Shopping": ["amazon", "flipkart", "myntra", "ajio", "nykaa", "meesho", "shirt", "clothes", "shopping", "shoes", "dress"],
    "Bills": ["electricity", "water", "gas", "airtel", "jio", "vi ", "vodafone", "bill", "recharge", "wifi", "broadband", "dth"],
    "Healthcare": ["pharmacy", "doctor", "hospital", "medicine", "medical", "apollo", "1mg", "pharmeasy", "clinic", "checkup"],
    "Entertainment": ["netflix", "prime", "hotstar", "spotify", "youtube", "movie", "bookmyshow", "pvr", "inox", "game", "concert"],
    "Rent": ["rent", "landlord", "pg fee", "hostel"],
    "Investments": ["mutual fund", "sip", "stock", "zerodha", "groww", "kuvera", "invest", "fd ", "rd ", "bond", "gold"],
}

def rule_categorize(desc: str) -> Optional[str]:
    d = desc.lower()
    for cat, kws in KEYWORD_MAP.items():
        for kw in kws:
            if kw in d:
                return cat
    return None

async def ai_categorize(desc: str) -> str:
    hit = rule_categorize(desc)
    if hit:
        return hit
    if not EMERGENT_LLM_KEY:
        return "Other"
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"cat-{new_id()}",
            system_message=(
                "You classify Indian expense descriptions into ONE category from: "
                + ", ".join(CATEGORIES)
                + ". Return ONLY a JSON object like {\"category\":\"Food\"}. No prose."
            ),
        ).with_model("gemini", "gemini-3-flash-preview")
        res = await chat.send_message(UserMessage(text=f"Expense: {desc}. Classify."))
        text = res if isinstance(res, str) else str(res)
        m = re.search(r'\{[^{}]*"category"\s*:\s*"([^"]+)"[^{}]*\}', text)
        if m:
            cat = m.group(1).strip().title()
            if cat in CATEGORIES:
                return cat
    except Exception as e:
        logging.warning(f"AI categorize failed: {e}")
    return "Other"

@api.post("/expenses/categorize")
async def categorize(body: CategorizeIn, user: dict = Depends(get_current_user)):
    cat = await ai_categorize(body.description)
    return {"category": cat}

@api.post("/expenses")
async def add_expense(body: ExpenseIn, user: dict = Depends(get_current_user)):
    cat = body.category or await ai_categorize(body.description)
    doc = {
        "id": new_id(),
        "user_id": user["id"],
        "description": body.description.strip(),
        "amount": float(body.amount),
        "category": cat,
        "date": body.date or now_iso(),
        "created_at": now_iso(),
    }
    await db.expenses.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.get("/expenses")
async def list_expenses(user: dict = Depends(get_current_user), limit: int = 200):
    rows = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).sort("date", -1).to_list(limit)
    return rows

@api.delete("/expenses/{eid}")
async def del_expense(eid: str, user: dict = Depends(get_current_user)):
    r = await db.expenses.delete_one({"id": eid, "user_id": user["id"]})
    return {"deleted": r.deleted_count}

# ------------------ BUDGETS ------------------
@api.get("/budgets")
async def list_budgets(user: dict = Depends(get_current_user)):
    rows = await db.budgets.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    # compute spend for current month
    ym = now_utc().strftime("%Y-%m")
    exps = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)
    spent_by = {}
    for e in exps:
        if str(e.get("date", ""))[:7] == ym:
            spent_by[e["category"]] = spent_by.get(e["category"], 0) + e["amount"]
    for b in rows:
        b["spent"] = round(spent_by.get(b["category"], 0), 2)
    return rows

@api.post("/budgets")
async def upsert_budget(body: BudgetIn, user: dict = Depends(get_current_user)):
    doc = {"user_id": user["id"], "category": body.category, "monthly_limit": float(body.monthly_limit)}
    await db.budgets.update_one(
        {"user_id": user["id"], "category": body.category},
        {"$set": doc, "$setOnInsert": {"id": new_id(), "created_at": now_iso()}},
        upsert=True,
    )
    return {"ok": True}

@api.delete("/budgets/{category}")
async def del_budget(category: str, user: dict = Depends(get_current_user)):
    await db.budgets.delete_one({"user_id": user["id"], "category": category})
    return {"ok": True}

# ------------------ GOALS ------------------
@api.get("/goals")
async def list_goals(user: dict = Depends(get_current_user)):
    return await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)

@api.post("/goals")
async def add_goal(body: GoalIn, user: dict = Depends(get_current_user)):
    doc = {
        "id": new_id(),
        "user_id": user["id"],
        "title": body.title.strip(),
        "target_amount": float(body.target_amount),
        "saved_amount": float(body.saved_amount or 0),
        "target_date": body.target_date,
        "icon": body.icon or "target",
        "created_at": now_iso(),
    }
    await db.goals.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.post("/goals/{gid}/contribute")
async def contribute(gid: str, body: GoalContribute, user: dict = Depends(get_current_user)):
    g = await db.goals.find_one({"id": gid, "user_id": user["id"]})
    if not g:
        raise HTTPException(404, "Goal not found")
    new_saved = g.get("saved_amount", 0) + body.amount
    await db.goals.update_one({"id": gid}, {"$set": {"saved_amount": new_saved}})
    # reward NugPoints for saving
    pts = int(body.amount // 100)
    if pts > 0:
        await db.users.update_one({"id": user["id"]}, {"$inc": {"nug_points": pts}})
        await db.nug_events.insert_one({
            "id": new_id(), "user_id": user["id"], "kind": "goal_contribution",
            "points": pts, "note": f"Contributed ₹{body.amount} to {g['title']}", "at": now_iso()
        })
    return {"saved_amount": new_saved, "earned_points": pts}

@api.delete("/goals/{gid}")
async def del_goal(gid: str, user: dict = Depends(get_current_user)):
    await db.goals.delete_one({"id": gid, "user_id": user["id"]})
    return {"ok": True}

# ------------------ DEBTS ------------------
@api.get("/debts")
async def list_debts(user: dict = Depends(get_current_user)):
    return await db.debts.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)

@api.post("/debts")
async def add_debt(body: DebtIn, user: dict = Depends(get_current_user)):
    doc = {"id": new_id(), "user_id": user["id"], **body.model_dump(), "created_at": now_iso()}
    await db.debts.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.delete("/debts/{did}")
async def del_debt(did: str, user: dict = Depends(get_current_user)):
    await db.debts.delete_one({"id": did, "user_id": user["id"]})
    return {"ok": True}

@api.get("/debts/strategy")
async def debt_strategy(user: dict = Depends(get_current_user), method: str = "avalanche", extra_payment: float = 0.0):
    debts = await db.debts.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    if not debts:
        return {"method": method, "months": 0, "total_interest": 0, "order": [], "schedule": []}
    # Simulate month-by-month
    working = [dict(d) for d in debts]
    for d in working:
        d["balance"] = float(d["balance"])
    # order by strategy
    if method == "snowball":
        working.sort(key=lambda x: x["balance"])
    else:
        working.sort(key=lambda x: -x["apr"])
    total_min = sum(d["min_payment"] for d in working)
    monthly_pool = total_min + max(0.0, extra_payment)
    months = 0
    total_interest = 0.0
    schedule = []
    while any(d["balance"] > 0 for d in working) and months < 600:
        months += 1
        # accrue interest
        for d in working:
            if d["balance"] > 0:
                interest = d["balance"] * (d["apr"] / 100 / 12)
                d["balance"] += interest
                total_interest += interest
        # pay minimums
        remaining = monthly_pool
        for d in working:
            if d["balance"] > 0:
                pay = min(d["min_payment"], d["balance"])
                d["balance"] -= pay
                remaining -= pay
        # extra to focused debt (first non-zero by strategy order)
        for d in working:
            if d["balance"] > 0 and remaining > 0:
                pay = min(remaining, d["balance"])
                d["balance"] -= pay
                remaining -= pay
                break
        schedule.append({"month": months, "remaining_total": round(sum(d["balance"] for d in working), 2)})
    return {
        "method": method,
        "months": months,
        "total_interest": round(total_interest, 2),
        "order": [d["name"] for d in working],
        "schedule": schedule[:120],
    }

# ------------------ HEALTH SCORE ------------------
@api.get("/health-score")
async def health_score(user: dict = Depends(get_current_user)):
    ym = now_utc().strftime("%Y-%m")
    exps = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    debts = await db.debts.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    budgets = await db.budgets.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)

    month_spend = sum(e["amount"] for e in exps if str(e.get("date", ""))[:7] == ym)
    total_saved = sum(g.get("saved_amount", 0) for g in goals)
    total_debt = sum(d["balance"] for d in debts)
    investment_spend = sum(e["amount"] for e in exps if e.get("category") == "Investments" and str(e.get("date", ""))[:7] == ym)

    # Sub-scores (each out of 100)
    savings_rate = min(100, int((total_saved / max(1, month_spend + total_saved)) * 100))
    budget_adherence = 100
    if budgets:
        breaches = 0
        for b in budgets:
            spent = sum(e["amount"] for e in exps if e.get("category") == b["category"] and str(e.get("date", ""))[:7] == ym)
            if spent > b["monthly_limit"]:
                breaches += 1
        budget_adherence = max(0, 100 - (breaches * 20))
    debt_health = 100 if total_debt == 0 else max(0, int(100 - min(100, total_debt / 5000)))
    investment_score = min(100, int(investment_spend / 100))
    emergency_score = min(100, int(total_saved / 500))
    discipline = min(100, user.get("streak_days", 1) * 5)

    overall = int(0.25 * savings_rate + 0.2 * budget_adherence + 0.2 * debt_health + 0.15 * investment_score + 0.1 * emergency_score + 0.1 * discipline)
    return {
        "overall": overall,
        "sub_scores": {
            "savings_rate": savings_rate,
            "budget_adherence": budget_adherence,
            "debt_health": debt_health,
            "investment_score": investment_score,
            "emergency_fund": emergency_score,
            "discipline": discipline,
        },
        "totals": {
            "month_spend": round(month_spend, 2),
            "total_saved": round(total_saved, 2),
            "total_debt": round(total_debt, 2),
        }
    }

# ------------------ NUDGES ------------------
@api.get("/nudges")
async def nudges(user: dict = Depends(get_current_user)):
    ym = now_utc().strftime("%Y-%m")
    exps = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)
    budgets = await db.budgets.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    debts = await db.debts.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    out = []
    # budget breaches
    for b in budgets:
        spent = sum(e["amount"] for e in exps if e.get("category") == b["category"] and str(e.get("date", ""))[:7] == ym)
        pct = (spent / b["monthly_limit"]) * 100 if b["monthly_limit"] else 0
        if pct >= 90:
            out.append({
                "id": f"budget-{b['category']}",
                "tone": "warning" if pct < 100 else "danger",
                "title": f"{b['category']} budget almost gone",
                "message": f"You've spent ₹{int(spent)} of ₹{int(b['monthly_limit'])} ({int(pct)}%). Cool it for the rest of the month.",
            })
    # goal delays
    for g in goals:
        try:
            td = datetime.fromisoformat(g["target_date"])
            days_left = max(1, (td.replace(tzinfo=timezone.utc) - now_utc()).days)
        except Exception:
            days_left = 30
        remaining = g["target_amount"] - g.get("saved_amount", 0)
        needed_per_month = remaining / max(1, days_left / 30)
        if remaining > 0 and days_left < 60 and g.get("saved_amount", 0) / g["target_amount"] < 0.5:
            out.append({
                "id": f"goal-{g['id']}",
                "tone": "warning",
                "title": f"Goal '{g['title']}' is at risk",
                "message": f"Save ₹{int(needed_per_month)}/month to hit it in time.",
            })
    # high APR debt
    high_apr = [d for d in debts if d["apr"] >= 20]
    if high_apr:
        d = max(high_apr, key=lambda x: x["apr"])
        out.append({
            "id": f"debt-{d['id']}",
            "tone": "danger",
            "title": f"Kill '{d['name']}' first",
            "message": f"{d['apr']}% APR is eating you alive. Prioritize it with the Avalanche method.",
        })
    # positive nudge
    total_saved = sum(g.get("saved_amount", 0) for g in goals)
    if total_saved > 0:
        out.append({
            "id": "pos-savings",
            "tone": "positive",
            "title": "Discipline is compounding",
            "message": f"You've saved ₹{int(total_saved)} toward your goals. Keep the streak alive.",
        })
    if not out:
        out.append({
            "id": "welcome",
            "tone": "info",
            "title": "Start with one small win",
            "message": "Add a monthly budget for Food. Tiny structure creates big freedom.",
        })
    return out[:6]

# ------------------ BUDGET ALERTS ------------------
@api.get("/budget-alerts")
async def budget_alerts(user: dict = Depends(get_current_user)):
    """Detailed per-category alerts based on current-month spend vs limits."""
    ym = now_utc().strftime("%Y-%m")
    budgets = await db.budgets.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    exps = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)
    alerts = []
    for b in budgets:
        spent = sum(e["amount"] for e in exps if e.get("category") == b["category"] and str(e.get("date", ""))[:7] == ym)
        pct = (spent / b["monthly_limit"]) * 100 if b["monthly_limit"] else 0
        if pct >= 100:
            level = "exceeded"
            msg = f"You've blown past ₹{int(b['monthly_limit'])} — currently at ₹{int(spent)} ({int(pct)}%)."
        elif pct >= 80:
            level = "warning"
            msg = f"{int(pct)}% of your ₹{int(b['monthly_limit'])} {b['category']} budget is gone. Ease up."
        elif pct >= 60:
            level = "info"
            msg = f"You're at {int(pct)}% of your {b['category']} budget."
        else:
            continue
        alerts.append({
            "id": f"alert-{b['category']}",
            "category": b["category"],
            "level": level,
            "message": msg,
            "spent": round(spent, 2),
            "limit": b["monthly_limit"],
            "pct": round(pct, 1),
        })
    # sort: exceeded > warning > info
    order = {"exceeded": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: order[a["level"]])
    return {"alerts": alerts, "count": len(alerts), "critical": sum(1 for a in alerts if a["level"] in ("exceeded", "warning"))}

# ------------------ RECURRING TRANSACTIONS ------------------
def _advance_date(iso_date: str, freq: str) -> str:
    dt = datetime.fromisoformat(iso_date).date() if "T" not in iso_date else datetime.fromisoformat(iso_date).date()
    if freq == "daily":
        dt = dt + timedelta(days=1)
    elif freq == "weekly":
        dt = dt + timedelta(days=7)
    else:  # monthly
        # add ~30 days approximation; roll month if possible
        y, m = dt.year, dt.month
        m += 1
        if m > 12:
            m = 1; y += 1
        try:
            dt = dt.replace(year=y, month=m)
        except ValueError:
            dt = (dt + timedelta(days=30))
    return dt.isoformat()

@api.get("/recurring")
async def list_recurring(user: dict = Depends(get_current_user)):
    rows = await db.recurring.find({"user_id": user["id"]}, {"_id": 0}).sort("next_due", 1).to_list(100)
    today = now_utc().date().isoformat()
    for r in rows:
        r["is_due"] = r["active"] and r["next_due"] <= today
    monthly_total = 0.0
    for r in rows:
        if not r["active"]:
            continue
        if r["frequency"] == "monthly":
            monthly_total += r["amount"]
        elif r["frequency"] == "weekly":
            monthly_total += r["amount"] * 4.33
        elif r["frequency"] == "daily":
            monthly_total += r["amount"] * 30
    return {"items": rows, "monthly_committed": round(monthly_total, 2)}

@api.post("/recurring")
async def add_recurring(body: RecurringIn, user: dict = Depends(get_current_user)):
    doc = {
        "id": new_id(),
        "user_id": user["id"],
        "name": body.name.strip(),
        "amount": float(body.amount),
        "category": body.category,
        "frequency": body.frequency,
        "next_due": body.next_due,
        "active": body.active,
        "created_at": now_iso(),
    }
    await db.recurring.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/recurring/{rid}")
async def update_recurring(rid: str, body: RecurringUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"ok": True}
    await db.recurring.update_one({"id": rid, "user_id": user["id"]}, {"$set": updates})
    return {"ok": True}

@api.delete("/recurring/{rid}")
async def del_recurring(rid: str, user: dict = Depends(get_current_user)):
    await db.recurring.delete_one({"id": rid, "user_id": user["id"]})
    return {"ok": True}

@api.post("/recurring/{rid}/post")
async def post_recurring(rid: str, user: dict = Depends(get_current_user)):
    """Materialize a recurring txn as an expense and advance next_due."""
    r = await db.recurring.find_one({"id": rid, "user_id": user["id"]}, {"_id": 0})
    if not r:
        raise HTTPException(404, "Recurring not found")
    exp = {
        "id": new_id(),
        "user_id": user["id"],
        "description": r["name"] + " (recurring)",
        "amount": float(r["amount"]),
        "category": r["category"],
        "date": now_iso(),
        "created_at": now_iso(),
    }
    await db.expenses.insert_one(exp)
    new_due = _advance_date(r["next_due"], r["frequency"])
    await db.recurring.update_one({"id": rid}, {"$set": {"next_due": new_due, "last_posted": now_iso()}})
    exp.pop("_id", None)
    return {"expense": exp, "next_due": new_due}

@api.post("/recurring/run-due")
async def run_due(user: dict = Depends(get_current_user)):
    """Post all due recurring transactions in one shot."""
    today = now_utc().date().isoformat()
    due = await db.recurring.find({"user_id": user["id"], "active": True, "next_due": {"$lte": today}}, {"_id": 0}).to_list(100)
    posted = 0
    for r in due:
        # roll forward until next_due > today (handles missed cycles)
        current_due = r["next_due"]
        while current_due <= today:
            await db.expenses.insert_one({
                "id": new_id(), "user_id": user["id"],
                "description": r["name"] + " (recurring)",
                "amount": float(r["amount"]),
                "category": r["category"],
                "date": current_due + "T00:00:00+00:00",
                "created_at": now_iso(),
            })
            posted += 1
            current_due = _advance_date(current_due, r["frequency"])
        await db.recurring.update_one({"id": r["id"]}, {"$set": {"next_due": current_due, "last_posted": now_iso()}})
    return {"posted": posted}

# ------------------ CASHFLOW PREDICT ------------------
@api.get("/cashflow/predict")
async def cashflow_predict(user: dict = Depends(get_current_user)):
    exps = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)
    # avg daily spend last 30 days
    cutoff = now_utc() - timedelta(days=30)
    recent = [e for e in exps if datetime.fromisoformat(e["date"].replace("Z", "+00:00")) >= cutoff] if exps else []
    total = sum(e["amount"] for e in recent)
    days = max(1, len(set(e["date"][:10] for e in recent))) if recent else 30
    avg_daily = total / days if recent else 300
    # 30-day forecast
    forecast = []
    starting = 30000.0  # illustrative opening balance
    bal = starting
    warnings = []
    for i in range(1, 31):
        bal -= avg_daily
        if i % 7 == 0:
            bal += 8000  # weekly income assumption
        forecast.append({"day": i, "balance": round(bal, 2)})
        if bal < 2000 and not warnings:
            warnings.append({"day": i, "message": "Cash likely below ₹2,000 — reduce dining out this week"})
    return {"avg_daily_spend": round(avg_daily, 2), "forecast": forecast, "warnings": warnings}

# ------------------ NUGPOINTS / REWARDS ------------------
REWARDS_CATALOG = [
    {"id": "amz-100", "brand": "Amazon", "title": "₹100 Amazon Voucher", "points": 500, "color": "orange"},
    {"id": "bms-2", "brand": "BookMyShow", "title": "2 Movie Tickets", "points": 1200, "color": "coral"},
    {"id": "starbucks", "brand": "Starbucks", "title": "Free Latte", "points": 300, "color": "green"},
    {"id": "myntra-200", "brand": "Myntra", "title": "₹200 Fashion Voucher", "points": 800, "color": "blue"},
    {"id": "irctc-500", "brand": "IRCTC", "title": "₹500 Travel Credit", "points": 2000, "color": "orange"},
    {"id": "prem-1m", "brand": "Nugvio", "title": "1 Month Premium", "points": 1500, "color": "coral"},
]

@api.get("/rewards")
async def get_rewards(user: dict = Depends(get_current_user)):
    events = await db.nug_events.find({"user_id": user["id"]}, {"_id": 0}).sort("at", -1).to_list(20)
    return {"points": user.get("nug_points", 0), "catalog": REWARDS_CATALOG, "history": events}

@api.post("/rewards/redeem/{reward_id}")
async def redeem(reward_id: str, user: dict = Depends(get_current_user)):
    reward = next((r for r in REWARDS_CATALOG if r["id"] == reward_id), None)
    if not reward:
        raise HTTPException(404, "Reward not found")
    if user.get("nug_points", 0) < reward["points"]:
        raise HTTPException(400, "Not enough NugPoints")
    await db.users.update_one({"id": user["id"]}, {"$inc": {"nug_points": -reward["points"]}})
    await db.nug_events.insert_one({
        "id": new_id(), "user_id": user["id"], "kind": "redemption",
        "points": -reward["points"], "note": f"Redeemed {reward['title']}", "at": now_iso()
    })
    return {"ok": True, "reward": reward}

# ------------------ LEARN (Literacy) ------------------
LESSONS = [
    {"id": "l1", "title": "What is a SIP?", "minutes": 3, "xp": 20,
     "body": "A Systematic Investment Plan (SIP) lets you invest a fixed amount in mutual funds every month. It builds discipline and averages your buying cost across market ups and downs — this is called rupee-cost averaging.",
     "quiz": [{"q": "SIP means investing __?", "options": ["Once a year", "A fixed amount monthly", "Only in stocks", "Only during bear markets"], "answer": 1}]},
    {"id": "l2", "title": "Emergency Fund 101", "minutes": 4, "xp": 25,
     "body": "An emergency fund is 3-6 months of essential expenses parked in a liquid account. It's your shield against job loss, medical bills, or sudden family needs. Build it before you invest aggressively.",
     "quiz": [{"q": "Ideal emergency fund size?", "options": ["1 week of income", "3-6 months of expenses", "12 months of income", "Just ₹5,000"], "answer": 1}]},
    {"id": "l3", "title": "Credit Cards: Friend or Foe?", "minutes": 5, "xp": 30,
     "body": "Credit cards charge 30-45% APR if you don't pay in full each month. Use them for rewards, but ALWAYS pay the full statement — not just the minimum. Minimum payment traps you in compounding interest.",
     "quiz": [{"q": "Paying only minimum due leads to?", "options": ["Zero interest", "High compounding interest", "Free rewards", "Better credit score"], "answer": 1}]},
    {"id": "l4", "title": "The 50-30-20 Rule", "minutes": 3, "xp": 20,
     "body": "Spend 50% on needs, 30% on wants, save/invest 20%. It's not rigid — but if your 'wants' regularly exceed 30%, your future self is subsidizing your present self.",
     "quiz": [{"q": "50-30-20 stands for?", "options": ["Needs-Wants-Savings", "Food-Rent-Bills", "Debt-Rent-Fun", "Stocks-Gold-FD"], "answer": 0}]},
    {"id": "l5", "title": "Compound Interest Magic", "minutes": 4, "xp": 25,
     "body": "₹5,000/month invested at 12% for 30 years becomes ~₹1.75 crore. The first 10 years feel slow. The next 20 explode. Time in the market beats timing the market.",
     "quiz": [{"q": "Compounding rewards?", "options": ["Timing perfectly", "Starting early & staying long", "Frequent trading", "Only lump-sum"], "answer": 1}]},
    {"id": "l6", "title": "Old vs New Tax Regime", "minutes": 5, "xp": 30,
     "body": "The New Regime has lower rates but almost no deductions. Old Regime has higher rates but lets you claim 80C, HRA, home loan interest. Do a quick calc every year — your income and investments change the answer.",
     "quiz": [{"q": "New Regime advantage?", "options": ["More deductions", "Lower slab rates", "No tax", "Only for freelancers"], "answer": 1}]},
]

@api.get("/lessons")
async def list_lessons(user: dict = Depends(get_current_user)):
    progress = await db.lesson_progress.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    done_map = {p["lesson_id"]: p for p in progress}
    out = []
    total_xp = 0
    for l in LESSONS:
        p = done_map.get(l["id"])
        out.append({**l, "completed": bool(p), "score": p["score"] if p else None})
        if p:
            total_xp += l["xp"]
    return {"lessons": out, "total_xp": total_xp}

@api.post("/lessons/complete")
async def complete_lesson(body: LessonCompleteIn, user: dict = Depends(get_current_user)):
    lesson = next((l for l in LESSONS if l["id"] == body.lesson_id), None)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    existing = await db.lesson_progress.find_one({"user_id": user["id"], "lesson_id": body.lesson_id})
    if existing:
        return {"already_completed": True}
    await db.lesson_progress.insert_one({
        "id": new_id(), "user_id": user["id"], "lesson_id": body.lesson_id,
        "score": body.score, "completed_at": now_iso()
    })
    pts = lesson["xp"] + (10 if body.score >= 80 else 0)
    await db.users.update_one({"id": user["id"]}, {"$inc": {"nug_points": pts}})
    await db.nug_events.insert_one({
        "id": new_id(), "user_id": user["id"], "kind": "lesson",
        "points": pts, "note": f"Completed lesson: {lesson['title']}", "at": now_iso()
    })
    return {"earned_points": pts}

# ------------------ TAX ------------------
def tax_new_regime(income: float) -> float:
    # FY 2025-26 approx new regime slabs
    slabs = [(300000, 0), (700000, 0.05), (1000000, 0.10), (1200000, 0.15), (1500000, 0.20), (float("inf"), 0.30)]
    remaining = max(0.0, income - 75000)  # standard deduction
    tax = 0.0
    lower = 0.0
    for upper, rate in slabs:
        if remaining <= 0:
            break
        band = min(remaining, upper - lower)
        tax += band * rate
        remaining -= band
        lower = upper
    # section 87A rebate approx (income up to 7L pays 0)
    if income - 75000 <= 700000:
        tax = 0.0
    return round(tax * 1.04, 2)  # +4% cess

def tax_old_regime(income: float, ded_80c: float, hra: float, other: float) -> float:
    ded_80c = min(ded_80c, 150000)
    taxable = max(0.0, income - 50000 - ded_80c - hra - other)  # 50k std ded
    slabs = [(250000, 0), (500000, 0.05), (1000000, 0.20), (float("inf"), 0.30)]
    tax = 0.0
    lower = 0.0
    for upper, rate in slabs:
        if taxable <= 0:
            break
        band = min(taxable - lower, upper - lower)
        if band <= 0:
            lower = upper
            continue
        tax += band * rate
        lower = upper
    if taxable <= 500000:
        tax = 0.0
    return round(tax * 1.04, 2)

@api.post("/tax/estimate")
async def tax_estimate(body: TaxIn, user: dict = Depends(get_current_user)):
    new_t = tax_new_regime(body.annual_income)
    old_t = tax_old_regime(body.annual_income, body.deductions_80c, body.hra, body.other_deductions)
    better = "new" if new_t <= old_t else "old"
    return {
        "new_regime_tax": new_t,
        "old_regime_tax": old_t,
        "recommended": better,
        "savings": round(abs(new_t - old_t), 2),
        "note": "Educational estimate only. Not tax advice.",
    }

# ------------------ AI COACH ------------------
COACH_SYSTEM = (
    "You are Nugvio Coach — a friendly, plain-spoken AI financial coach for young Indians (18-30). "
    "Rules: (1) Give clear, decisive answers in 2-4 short sentences. (2) Use ₹ and Indian context (SIP, PPF, NPS, HDFC, ICICI, Groww). "
    "(3) NEVER recommend specific stocks or crypto. (4) Nudge users toward saving, budgeting, investing in index funds/SIPs, killing high-APR debt. "
    "(5) Tone: like a smart friend — warm, honest, occasionally cheeky. No jargon. No disclaimers unless asked."
)

@api.post("/coach/chat")
async def coach_chat(body: CoachMsgIn, user: dict = Depends(get_current_user)):
    sid = f"{user['id']}::{body.session_id}"
    # persist user msg
    await db.coach_messages.insert_one({
        "id": new_id(), "user_id": user["id"], "session_id": body.session_id,
        "role": "user", "text": body.text, "at": now_iso()
    })
    # Pull history for context (last 20)
    hist = await db.coach_messages.find(
        {"user_id": user["id"], "session_id": body.session_id}, {"_id": 0}
    ).sort("at", 1).to_list(20)
    # Compose message with brief history embedded (LlmChat sessions are per-request here)
    convo = "\n".join([f"{m['role'].upper()}: {m['text']}" for m in hist[-8:]])
    prompt = f"Conversation so far:\n{convo}\n\nRespond to the latest USER message as Nugvio Coach."
    reply = "I'm here — ask me anything about money."
    if EMERGENT_LLM_KEY:
        try:
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=sid,
                system_message=COACH_SYSTEM,
            ).with_model("gemini", "gemini-3-flash-preview")
            res = await chat.send_message(UserMessage(text=prompt))
            reply = res if isinstance(res, str) else str(res)
        except Exception as e:
            logging.warning(f"Coach LLM failed: {e}")
            reply = "My brain is offline for a sec. Try again in a moment — meanwhile, what specific money question is on your mind?"
    await db.coach_messages.insert_one({
        "id": new_id(), "user_id": user["id"], "session_id": body.session_id,
        "role": "coach", "text": reply, "at": now_iso()
    })
    return {"reply": reply}

@api.get("/coach/history")
async def coach_history(session_id: str, user: dict = Depends(get_current_user)):
    msgs = await db.coach_messages.find(
        {"user_id": user["id"], "session_id": session_id}, {"_id": 0}
    ).sort("at", 1).to_list(200)
    return msgs

# ------------------ SEED DEMO ------------------
async def seed_demo():
    admin_email = os.environ.get("ADMIN_EMAIL", "demo@nugvio.in")
    admin_pw = os.environ.get("ADMIN_PASSWORD", "Nugvio@123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        uid = new_id()
        await db.users.insert_one({
            "id": uid, "email": admin_email, "name": "Demo User",
            "password_hash": hash_pw(admin_pw), "nug_points": 850, "streak_days": 7,
            "created_at": now_iso(),
        })
        # sample expenses
        samples = [
            ("Zomato dinner", 420, "Food"),
            ("Uber to office", 180, "Travel"),
            ("Amazon shirt", 899, "Shopping"),
            ("Airtel recharge", 299, "Bills"),
            ("Netflix subscription", 199, "Entertainment"),
            ("Groww SIP", 2500, "Investments"),
            ("PG Rent", 12000, "Rent"),
            ("Swiggy lunch", 260, "Food"),
            ("BookMyShow movie", 350, "Entertainment"),
            ("1mg medicines", 540, "Healthcare"),
        ]
        for i, (desc, amt, cat) in enumerate(samples):
            d = (now_utc() - timedelta(days=i)).isoformat()
            await db.expenses.insert_one({
                "id": new_id(), "user_id": uid, "description": desc,
                "amount": amt, "category": cat, "date": d, "created_at": d
            })
        # budgets
        for cat, lim in [("Food", 5000), ("Entertainment", 1500), ("Shopping", 3000), ("Travel", 3000)]:
            await db.budgets.insert_one({
                "id": new_id(), "user_id": uid, "category": cat,
                "monthly_limit": lim, "created_at": now_iso()
            })
        # goals
        goal_samples = [
            ("New MacBook", 120000, 35000, "laptop", 180),
            ("Bali Trip", 60000, 12000, "vacation", 120),
            ("Emergency Fund", 90000, 40000, "shield", 365),
        ]
        for title, tgt, saved, icon, days in goal_samples:
            await db.goals.insert_one({
                "id": new_id(), "user_id": uid, "title": title,
                "target_amount": tgt, "saved_amount": saved,
                "target_date": (now_utc() + timedelta(days=days)).date().isoformat(),
                "icon": icon, "created_at": now_iso()
            })
        # debts
        for name, bal, apr, minp in [("HDFC Credit Card", 45000, 38.0, 2500), ("Education Loan", 180000, 9.5, 4500)]:
            await db.debts.insert_one({
                "id": new_id(), "user_id": uid, "name": name,
                "balance": bal, "apr": apr, "min_payment": minp, "created_at": now_iso()
            })
    else:
        # keep password in sync with env
        if not verify_pw(admin_pw, existing["password_hash"]):
            await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_pw(admin_pw)}})

async def seed_recurring_demo():
    admin_email = os.environ.get("ADMIN_EMAIL", "demo@nugvio.in")
    u = await db.users.find_one({"email": admin_email})
    if not u:
        return
    exists = await db.recurring.find_one({"user_id": u["id"]})
    if exists:
        return
    today = now_utc().date()
    samples = [
        ("Netflix", 199, "Entertainment", "monthly", (today + timedelta(days=5)).isoformat()),
        ("Spotify Premium", 119, "Entertainment", "monthly", (today + timedelta(days=12)).isoformat()),
        ("PG Rent", 12000, "Rent", "monthly", (today + timedelta(days=2)).isoformat()),
        ("Groww SIP", 2500, "Investments", "monthly", (today + timedelta(days=8)).isoformat()),
        ("Airtel Postpaid", 499, "Bills", "monthly", (today + timedelta(days=18)).isoformat()),
    ]
    for name, amt, cat, freq, nd in samples:
        await db.recurring.insert_one({
            "id": new_id(), "user_id": u["id"], "name": name,
            "amount": amt, "category": cat, "frequency": freq,
            "next_due": nd, "active": True, "created_at": now_iso()
        })

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.expenses.create_index("user_id")
    await db.goals.create_index("user_id")
    await db.debts.create_index("user_id")
    await db.budgets.create_index([("user_id", 1), ("category", 1)], unique=True)
    await db.coach_messages.create_index([("user_id", 1), ("session_id", 1)])
    await db.recurring.create_index("user_id")
    await seed_demo()
    await seed_recurring_demo()

@app.on_event("shutdown")
async def shutdown():
    client.close()

@api.get("/")
async def root():
    return {"app": "Nugvio", "tagline": "Nudge The Youth", "status": "ok"}

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
