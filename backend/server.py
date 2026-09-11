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
import httpx
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict

# LLM


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

async def _session_user(token: str):
    s = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not s:
        return None
    exp = s["expires_at"]
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now_utc():
        await db.user_sessions.delete_one({"session_token": token})
        return None
    return await db.users.find_one({"id": s["user_id"]}, {"_id": 0, "password_hash": 0})

async def get_current_user(request: Request) -> dict:
    st = request.cookies.get("session_token")
    if st:
        u = await _session_user(st)
        if u:
            return u
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
        u = await _session_user(token)
        if u:
            return u
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
    type: Literal["expense", "income"] = "expense"

class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)
    category: Optional[str] = None
    date: Optional[str] = None
    type: Optional[Literal["expense", "income"]] = None

class MeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    currency: Optional[Literal["INR", "USD", "EUR", "GBP"]] = None
    notif_prefs: Optional[dict] = None

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

class HoldingIn(BaseModel):
    name: str
    kind: Literal["MF", "Stock", "Gold", "FD", "Bond", "Crypto"]
    units: float = Field(gt=0)
    avg_price: float = Field(gt=0)
    current_price: float = Field(gt=0)

class HoldingUpdate(BaseModel):
    current_price: Optional[float] = None
    units: Optional[float] = None

class SIPIn(BaseModel):
    name: str
    monthly_amount: float = Field(gt=0)
    start_date: str  # YYYY-MM-DD
    expected_return: float = Field(ge=0, le=40)  # percent

class SIPUpdate(BaseModel):
    monthly_amount: Optional[float] = None
    expected_return: Optional[float] = None
    active: Optional[bool] = None

class AssetIn(BaseModel):
    name: str
    kind: Literal["Bank", "Savings", "Cash", "Other"]
    value: float = Field(ge=0)

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = None

class GoalAutopilotIn(BaseModel):
    monthly_commit: Optional[float] = Field(default=None, ge=0)
    linked_sip_id: Optional[str] = None

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
async def logout(request: Request, response: Response):
    st = request.cookies.get("session_token")
    if st:
        await db.user_sessions.delete_one({"session_token": st})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("session_token", path="/", secure=True, samesite="none")
    return {"ok": True}

class GoogleSessionIn(BaseModel):
    session_id: str

@api.post("/auth/google/session")
async def google_session(body: GoogleSessionIn, response: Response):
    # Exchange session_id with Emergent Auth (must happen server-side)
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": body.session_id}, timeout=15.0)
    if r.status_code != 200:
        raise HTTPException(401, "Invalid or expired session")
    data = r.json()
    email = data["email"].lower().strip()
    u = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    if not u:
        u = {
            "id": new_id(),
            "email": email,
            "name": data.get("name") or email.split("@")[0],
            "picture": data.get("picture"),
            "auth_provider": "google",
            "nug_points": 100,
            "streak_days": 1,
            "created_at": now_iso(),
        }
        await db.users.insert_one(dict(u))
    elif data.get("picture") and not u.get("picture"):
        await db.users.update_one({"id": u["id"]}, {"$set": {"picture": data["picture"]}})
    session_token = data["session_token"]
    await db.user_sessions.insert_one({
        "id": new_id(), "user_id": u["id"], "session_token": session_token,
        "expires_at": (now_utc() + timedelta(days=7)).isoformat(), "created_at": now_iso(),
    })
    response.set_cookie("session_token", session_token, httponly=True, secure=True,
                        samesite="none", max_age=7 * 24 * 3600, path="/")
    u.pop("_id", None)
    return u

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

@api.patch("/me")
async def update_me(body: MeUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "name" in updates:
        updates["name"] = updates["name"].strip()
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    return await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})

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
  
    return "Other"

@api.post("/expenses/categorize")
async def categorize(body: CategorizeIn, user: dict = Depends(get_current_user)):
    cat = await ai_categorize(body.description)
    return {"category": cat}

@api.post("/expenses")
async def add_expense(body: ExpenseIn, user: dict = Depends(get_current_user)):
    if body.type == "income":
        cat = body.category or "Income"
    else:
        cat = body.category or await ai_categorize(body.description)
    doc = {
        "id": new_id(),
        "user_id": user["id"],
        "description": body.description.strip(),
        "amount": float(body.amount),
        "category": cat,
        "type": body.type,
        "date": body.date or now_iso(),
        "created_at": now_iso(),
    }
    await db.expenses.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.get("/expenses")
async def list_expenses(user: dict = Depends(get_current_user), limit: int = 200,
                        q: Optional[str] = None, type: Optional[str] = None,
                        category: Optional[str] = None,
                        date_from: Optional[str] = None, date_to: Optional[str] = None):
    query = {"user_id": user["id"]}
    if q:
        query["description"] = {"$regex": re.escape(q), "$options": "i"}
    if type == "income":
        query["type"] = "income"
    elif type == "expense":
        query["type"] = {"$ne": "income"}
    if category:
        query["category"] = category
    if date_from or date_to:
        dr = {}
        if date_from:
            dr["$gte"] = date_from
        if date_to:
            dr["$lte"] = date_to + "\uffff"
        query["date"] = dr
    rows = await db.expenses.find(query, {"_id": 0}).sort("date", -1).to_list(limit)
    return rows

@api.patch("/expenses/{eid}")
async def update_expense(eid: str, body: ExpenseUpdate, user: dict = Depends(get_current_user)):
    e = await db.expenses.find_one({"id": eid, "user_id": user["id"]})
    if not e:
        raise HTTPException(404, "Transaction not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "description" in updates:
        updates["description"] = updates["description"].strip()
    if updates:
        await db.expenses.update_one({"id": eid}, {"$set": updates})
    doc = await db.expenses.find_one({"id": eid}, {"_id": 0})
    return doc

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
    exps = await db.expenses.find({"user_id": user["id"], "type": {"$ne": "income"}}, {"_id": 0}).to_list(2000)
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
    await db.contributions.insert_one({
        "id": new_id(), "user_id": user["id"], "goal_id": gid,
        "goal_title": g["title"], "amount": body.amount, "at": now_iso()
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

def _simulate_debts(debts: list, method: str = "avalanche", extra_payment: float = 0.0):
    debts = [d for d in debts if d["balance"] > 0]
    if not debts:
        return {"method": method, "months": 0, "total_interest": 0, "order": [], "schedule": []}
    working = [dict(d) for d in debts]
    for d in working:
        d["balance"] = float(d["balance"])
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
        for d in working:
            if d["balance"] > 0:
                interest = d["balance"] * (d["apr"] / 100 / 12)
                d["balance"] += interest
                total_interest += interest
        remaining = monthly_pool
        for d in working:
            if d["balance"] > 0:
                pay = min(d["min_payment"], d["balance"])
                d["balance"] -= pay
                remaining -= pay
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

@api.get("/debts/strategy")
async def debt_strategy(user: dict = Depends(get_current_user), method: str = "avalanche", extra_payment: float = 0.0):
    debts = await db.debts.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    return _simulate_debts(debts, method, extra_payment)

class DebtPayIn(BaseModel):
    amount: float = Field(gt=0)

@api.post("/debts/{did}/pay")
async def pay_debt(did: str, body: DebtPayIn, user: dict = Depends(get_current_user)):
    d = await db.debts.find_one({"id": did, "user_id": user["id"]}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Debt not found")
    if d["balance"] <= 0:
        raise HTTPException(400, "This debt is already paid off")
    debts = await db.debts.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    before = _simulate_debts(debts)
    pay = round(min(body.amount, d["balance"]), 2)
    new_bal = round(d["balance"] - pay, 2)
    await db.debts.update_one({"id": did}, {"$set": {"balance": new_bal}})
    after = _simulate_debts([{**x, "balance": new_bal if x["id"] == did else x["balance"]} for x in debts])
    months_saved = max(0, before["months"] - after["months"])
    interest_saved = max(0.0, round(before["total_interest"] - after["total_interest"], 2))
    pts = int(pay // 100)
    if pts > 0:
        await db.users.update_one({"id": user["id"]}, {"$inc": {"nug_points": pts}})
        await db.nug_events.insert_one({
            "id": new_id(), "user_id": user["id"], "kind": "debt_payment",
            "points": pts, "note": f"Paid ₹{int(pay)} extra on {d['name']}", "at": now_iso()})
    await db.debt_payments.insert_one({
        "id": new_id(), "user_id": user["id"], "debt_id": did, "debt_name": d["name"],
        "amount": pay, "interest_saved": interest_saved, "months_saved": months_saved, "at": now_iso()})
    return {
        "paid": pay, "new_balance": new_bal, "paid_off": new_bal <= 0,
        "months_saved": months_saved, "interest_saved": interest_saved, "earned_points": pts,
    }

# ------------------ HEALTH SCORE ------------------
def _parse_dt(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return now_utc()

SCORE_COMPONENTS = [
    ("savings", "Savings", "savings_rate", 25),
    ("spending", "Spending", "budget_adherence", 20),
    ("debt", "Debt", "debt_health", 20),
    ("emergency", "Emergency Fund", "emergency_fund", 15),
    ("investments", "Investments", "investment_score", 10),
    ("discipline", "Discipline", "discipline", 10),
]

SCORE_ACTIONS = {
    "savings": {"title": "Boost your savings", "message": "Contribute to a goal this week — even ₹500 moves the needle.", "route": "/app/goals", "label": "Add to a goal"},
    "spending": {"title": "Rein in spending", "message": "You're close to (or past) budget limits. Trim the top overspent category.", "route": "/app/budgets", "label": "Review budgets"},
    "debt": {"title": "Attack high-interest debt", "message": "Put extra cash on your highest-APR debt using the Avalanche method.", "route": "/app/debts", "label": "Open debt plan"},
    "emergency": {"title": "Grow your emergency fund", "message": "Your safety net is below target. Start a monthly top-up plan.", "route": "/app/emergency", "label": "Plan my fund"},
    "investments": {"title": "Invest something monthly", "message": "Start or increase a SIP — consistency beats timing.", "route": "/app/investments", "label": "Set up SIP"},
    "discipline": {"title": "Keep the streak alive", "message": "Log expenses daily and complete a lesson to build discipline.", "route": "/app/learn", "label": "Take a lesson"},
}

async def _health_data(user: dict):
    ym = now_utc().strftime("%Y-%m")
    exps = await db.expenses.find({"user_id": user["id"], "type": {"$ne": "income"}}, {"_id": 0}).to_list(2000)
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

    overall = int(0.25 * savings_rate + 0.2 * budget_adherence + 0.2 * debt_health + 0.15 * emergency_score + 0.1 * investment_score + 0.1 * discipline)
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

@api.get("/health-score")
async def health_score(user: dict = Depends(get_current_user)):
    return await _health_data(user)

@api.get("/health-score/breakdown")
async def health_breakdown(user: dict = Depends(get_current_user)):
    d = await _health_data(user)
    comps = []
    for key, label, sub_key, mx in SCORE_COMPONENTS:
        pts = round(d["sub_scores"][sub_key] / 100 * mx)
        comps.append({"key": key, "label": label, "points": pts, "max": mx, "pct": round(pts / mx * 100)})
    overall = d["overall"]
    target = min(100, ((overall // 10) + 1) * 10)
    weakest = sorted(comps, key=lambda c: c["pct"])[:3]
    actions = []
    for c in weakest:
        a = SCORE_ACTIONS[c["key"]]
        actions.append({**a, "component": c["label"], "potential_gain": c["max"] - c["points"]})
    today = now_utc().date().isoformat()
    snaps = await db.health_snapshots.find({"user_id": user["id"]}, {"_id": 0}).sort("date", -1).to_list(60)
    prev = next((s for s in snaps if s["date"] <= (now_utc() - timedelta(days=6)).date().isoformat()), None)
    delta = (overall - prev["score"]) if prev else None
    change_reason = None
    if prev and prev.get("components"):
        diffs = [(c["label"], c["points"] - prev["components"].get(c["key"], c["points"])) for c in comps]
        diffs = [x for x in diffs if x[1] != 0]
        if diffs:
            top = max(diffs, key=lambda x: abs(x[1]))
            change_reason = f"{top[0]} {'improved' if top[1] > 0 else 'dropped'} {'+' if top[1] > 0 else ''}{top[1]} pts"
    await db.health_snapshots.update_one(
        {"user_id": user["id"], "date": today},
        {"$set": {"user_id": user["id"], "date": today, "score": overall,
                  "components": {c["key"]: c["points"] for c in comps}}}, upsert=True)
    return {"overall": overall, "target": target, "components": comps, "actions": actions,
            "totals": d["totals"], "delta": delta, "change_reason": change_reason}

# ------------------ NUDGES ------------------
@api.get("/nudges")
async def nudges(user: dict = Depends(get_current_user)):
    ym = now_utc().strftime("%Y-%m")
    exps = await db.expenses.find({"user_id": user["id"], "type": {"$ne": "income"}}, {"_id": 0}).to_list(2000)
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
    exps = await db.expenses.find({"user_id": user["id"], "type": {"$ne": "income"}}, {"_id": 0}).to_list(2000)
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

# ------------------ INVESTMENTS ------------------
@api.get("/investments/summary")
async def invest_summary(user: dict = Depends(get_current_user)):
    holdings = await db.holdings.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    sips = await db.sips.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    invested = sum(h["units"] * h["avg_price"] for h in holdings)
    current = sum(h["units"] * h["current_price"] for h in holdings)
    gain = current - invested
    gain_pct = (gain / invested * 100) if invested else 0
    monthly_sip = sum(s["monthly_amount"] for s in sips if s.get("active", True))
    # Allocation by kind
    alloc = {}
    for h in holdings:
        v = h["units"] * h["current_price"]
        alloc[h["kind"]] = alloc.get(h["kind"], 0) + v
    allocation = [{"kind": k, "value": round(v, 2), "pct": round((v/current*100) if current else 0, 1)} for k, v in alloc.items()]
    # Best & worst performer
    perf = []
    for h in holdings:
        inv = h["units"] * h["avg_price"]
        cur = h["units"] * h["current_price"]
        p = (cur - inv) / inv * 100 if inv else 0
        perf.append({"name": h["name"], "pct": round(p, 2), "gain": round(cur - inv, 2)})
    perf.sort(key=lambda x: x["pct"], reverse=True)
    best = perf[0] if perf else None
    worst = perf[-1] if perf and len(perf) > 1 else None
    return {
        "invested": round(invested, 2),
        "current_value": round(current, 2),
        "gain": round(gain, 2),
        "gain_pct": round(gain_pct, 2),
        "monthly_sip": round(monthly_sip, 2),
        "allocation": allocation,
        "best": best,
        "worst": worst,
        "holdings_count": len(holdings),
        "sips_count": sum(1 for s in sips if s.get("active", True)),
    }

@api.get("/investments/holdings")
async def list_holdings(user: dict = Depends(get_current_user)):
    rows = await db.holdings.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    for h in rows:
        h["invested"] = round(h["units"] * h["avg_price"], 2)
        h["current"] = round(h["units"] * h["current_price"], 2)
        h["gain"] = round(h["current"] - h["invested"], 2)
        h["gain_pct"] = round((h["gain"] / h["invested"] * 100) if h["invested"] else 0, 2)
    return rows

@api.post("/investments/holdings")
async def add_holding(body: HoldingIn, user: dict = Depends(get_current_user)):
    doc = {"id": new_id(), "user_id": user["id"], **body.model_dump(), "created_at": now_iso()}
    await db.holdings.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/investments/holdings/{hid}")
async def update_holding(hid: str, body: HoldingUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.holdings.update_one({"id": hid, "user_id": user["id"]}, {"$set": updates})
    return {"ok": True}

@api.delete("/investments/holdings/{hid}")
async def del_holding(hid: str, user: dict = Depends(get_current_user)):
    await db.holdings.delete_one({"id": hid, "user_id": user["id"]})
    return {"ok": True}

@api.get("/investments/sips")
async def list_sips(user: dict = Depends(get_current_user)):
    rows = await db.sips.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    today = now_utc().date()
    for s in rows:
        try:
            start = datetime.fromisoformat(s["start_date"]).date() if "T" not in s["start_date"] else datetime.fromisoformat(s["start_date"]).date()
        except Exception:
            start = today
        months_run = max(0, (today.year - start.year) * 12 + (today.month - start.month))
        s["months_run"] = months_run
        s["invested_so_far"] = round(months_run * s["monthly_amount"], 2)
    return rows

@api.post("/investments/sips")
async def add_sip(body: SIPIn, user: dict = Depends(get_current_user)):
    doc = {"id": new_id(), "user_id": user["id"], **body.model_dump(), "active": True, "created_at": now_iso()}
    await db.sips.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/investments/sips/{sid}")
async def update_sip(sid: str, body: SIPUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.sips.update_one({"id": sid, "user_id": user["id"]}, {"$set": updates})
    return {"ok": True}

@api.delete("/investments/sips/{sid}")
async def del_sip(sid: str, user: dict = Depends(get_current_user)):
    await db.sips.delete_one({"id": sid, "user_id": user["id"]})
    return {"ok": True}

@api.get("/investments/projection")
async def projection(user: dict = Depends(get_current_user), years: int = 10):
    """Monthly compounding projection of all active SIPs combined."""
    sips = await db.sips.find({"user_id": user["id"], "active": True}, {"_id": 0}).to_list(50)
    total_monthly = sum(s["monthly_amount"] for s in sips)
    # weighted avg return
    weighted = sum(s["monthly_amount"] * s["expected_return"] for s in sips)
    avg_return = (weighted / total_monthly) if total_monthly else 12.0
    r = avg_return / 100 / 12
    series = []
    invested = 0.0
    value = 0.0
    for m in range(1, years * 12 + 1):
        invested += total_monthly
        value = (value + total_monthly) * (1 + r)
        if m % 12 == 0:
            series.append({
                "year": m // 12,
                "invested": round(invested, 2),
                "value": round(value, 2),
                "gain": round(value - invested, 2),
            })
    return {
        "monthly_sip": round(total_monthly, 2),
        "avg_return_pct": round(avg_return, 2),
        "series": series,
        "final_value": round(value, 2),
        "total_invested": round(invested, 2),
    }

# ------------------ CASHFLOW PREDICT ------------------
@api.get("/cashflow/predict")
async def cashflow_predict(user: dict = Depends(get_current_user)):
    exps = await db.expenses.find({"user_id": user["id"], "type": {"$ne": "income"}}, {"_id": 0}).to_list(2000)
    # avg daily spend last 30 days
    cutoff = now_utc() - timedelta(days=30)
    recent = [e for e in exps if _parse_dt(e["date"]) >= cutoff] if exps else []
    total = sum(e["amount"] for e in recent)
    days = max(1, len(set(str(e["date"])[:10] for e in recent))) if recent else 30
    avg_daily = total / days if recent else 300
    # 30-day forecast
    forecast = []
    assets = await db.assets.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    bank = sum(a["value"] for a in assets if a.get("kind") in ("Bank", "Cash", "Savings"))
    starting = bank if bank > 0 else 30000.0
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
    "(5) Tone: like a smart friend — warm, honest, occasionally cheeky. No jargon. No disclaimers unless asked. "
    "(6) You are given a LIVE FINANCIAL SNAPSHOT of this user. When their question touches money they actually have — spending, debts, goals, investments, emergency fund — ground your advice in those real numbers instead of generic advice. "
    "(7) After your reply, output ONE final line exactly in this format: ACTIONS: [{\"label\": \"...\", \"route\": \"...\"}] — 1 to 3 short tap-to-do buttons that let the user act on your advice inside the app. "
    "Allowed routes ONLY: /app/debts (debt payoff plan), /app/budgets, /app/goals, /app/investments (SIPs & portfolio), /app/emergency (emergency fund planner), /app/expenses, /app/networth, /app/learn (lessons), /app/tax, /app/recap. "
    "Labels must be specific and include amounts when possible, e.g. \"Pay ₹2,000 extra on HDFC card\". If no action fits, output ACTIONS: [] "
    "(8) For what-if questions (Can I afford X? What if I save ₹Y more monthly? Debt vs savings? How long to a goal?), do the actual arithmetic from the snapshot and show it simply — e.g. '₹60,000 is 2.1× your monthly surplus of ₹28,400, so...'. Give a clear verdict, never vague hedging."
)

COACH_ACTION_ROUTES = {"/app/debts", "/app/budgets", "/app/goals", "/app/investments", "/app/emergency",
                       "/app/expenses", "/app/networth", "/app/learn", "/app/tax", "/app/recap", "/app/actions"}

def _parse_coach_actions(text: str):
    m = re.search(r"ACTIONS:\s*(\[.*\])", text, re.S)
    actions = []
    if m:
        try:
            for a in json.loads(m.group(1))[:3]:
                if isinstance(a, dict) and a.get("route") in COACH_ACTION_ROUTES and a.get("label"):
                    actions.append({"label": str(a["label"])[:60], "route": a["route"]})
        except Exception:
            pass
        text = text[:m.start()].rstrip().rstrip("`").rstrip()
    return text, actions

async def _coach_context(user: dict) -> str:
    hb = await health_breakdown(user=user)
    ac = await action_center(user=user)
    ef = await _emergency_stats(user)
    nw = await networth(user=user)
    inv = await invest_summary(user=user)
    lines = [
        f"Financial Health Score: {hb['overall']}/100 (next target {hb['target']}). Components: "
        + ", ".join(f"{c['label']} {c['points']}/{c['max']}" for c in hb["components"]),
    ]
    t = hb["totals"]
    ym = now_utc().strftime("%Y-%m")
    exps = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)
    income_m = sum(e["amount"] for e in exps if e.get("type") == "income" and str(e.get("date", ""))[:7] == ym)
    surplus = income_m - t["month_spend"]
    lines.append(f"This month: income ₹{int(income_m)}, spend ₹{int(t['month_spend'])}, surplus ₹{int(surplus)}. Total goal savings ₹{int(t['total_saved'])}, total debt ₹{int(t['total_debt'])}.")
    lines.append(f"Net worth ₹{int(nw['net_worth'])} (assets ₹{int(nw['assets']['total'])}, liabilities ₹{int(nw['liabilities']['total'])}).")
    lines.append(f"Investments: current value ₹{int(inv['current_value'])} on ₹{int(inv['invested'])} invested, monthly SIP ₹{int(inv['monthly_sip'])} across {inv['sips_count']} active SIPs.")
    lines.append(f"Emergency fund: ₹{int(ef['current'])} of recommended ₹{int(ef['recommended'])} ({ef['coverage_pct']}% covered).")
    tops = [i for i in ac["insights"] if i["severity"] in ("high", "medium")][:4]
    if tops:
        lines.append("Top issues right now: " + " | ".join(f"[{i['severity']}] {i['title']} — {i['message']}" for i in tops))
    wins = [i for i in ac["insights"] if i["severity"] == "win"][:2]
    if wins:
        lines.append("Recent wins: " + " | ".join(i["title"] for i in wins))
    return "\n".join(lines)

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
    ctx = ""
    try:
        ctx = await _coach_context(user)
    except Exception as e:
        logging.warning(f"Coach context failed: {e}")
    prompt = (
        (f"LIVE FINANCIAL SNAPSHOT of this user (real numbers — use them when relevant):\n{ctx}\n\n" if ctx else "")
        + f"Conversation so far:\n{convo}\n\nRespond to the latest USER message as Nugvio Coach."
    )
    reply = "I'm here — ask me anything about money."
    actions = []
   
    await db.coach_messages.insert_one({
        "id": new_id(), "user_id": user["id"], "session_id": body.session_id,
        "role": "coach", "text": reply, "actions": actions, "at": now_iso()
    })
    return {"reply": reply, "actions": actions}

@api.get("/coach/history")
async def coach_history(session_id: str, user: dict = Depends(get_current_user)):
    msgs = await db.coach_messages.find(
        {"user_id": user["id"], "session_id": session_id}, {"_id": 0}
    ).sort("at", 1).to_list(200)
    return msgs

# ------------------ GOAL PACE / AUTOPILOT ------------------
def _goal_pace(g: dict):
    target_dt = _parse_dt(g.get("target_date"))
    created = _parse_dt(g.get("created_at"))
    now = now_utc()
    total_days = max(1, (target_dt - created).days)
    elapsed = min(total_days, max(0, (now - created).days))
    days_left = max(0, (target_dt - now).days)
    target = g["target_amount"]
    saved = g.get("saved_amount", 0)
    expected = target * elapsed / total_days
    variance = saved - expected
    monthly_pace = target / max(1, total_days / 30.44)
    months_off = round(variance / monthly_pace, 1) if monthly_pace else 0
    remaining = max(0, target - saved)
    required_monthly = remaining / max(0.5, days_left / 30.44) if days_left > 0 else remaining
    if variance >= 0.05 * target:
        status = "ahead"
    elif variance <= -0.05 * target:
        status = "behind"
    else:
        status = "on_track"
    return {
        "expected_saved": round(expected, 2), "variance": round(variance, 2),
        "months_off": months_off, "required_monthly": round(required_monthly, 2),
        "days_left": days_left, "status": status,
    }

@api.get("/goals-autopilot")
async def goals_autopilot(user: dict = Depends(get_current_user)):
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    sips = await db.sips.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    sip_map = {s["id"]: s for s in sips}
    out = []
    for g in goals:
        pace = _goal_pace(g)
        commit = g.get("monthly_commit") or 0
        sip = sip_map.get(g.get("linked_sip_id"))
        sip_amt = sip["monthly_amount"] if sip and sip.get("active", True) else 0
        committed = commit + sip_amt
        remaining = max(0, g["target_amount"] - g.get("saved_amount", 0))
        months_left = pace["days_left"] / 30.44
        projected_delay = None
        if committed > 0 and remaining > 0:
            projected_delay = round(remaining / committed - months_left, 1)
        out.append({
            **{k: g.get(k) for k in ("id", "title", "target_amount", "saved_amount", "target_date")},
            **pace,
            "monthly_commit": commit,
            "linked_sip_id": g.get("linked_sip_id"),
            "linked_sip_name": sip["name"] if sip else None,
            "committed_monthly": round(committed, 2),
            "projected_delay_months": projected_delay,
        })
    active_sips = [{"id": s["id"], "name": s["name"], "monthly_amount": s["monthly_amount"]} for s in sips if s.get("active", True)]
    return {"goals": out, "sips": active_sips}

@api.patch("/goals/{gid}/autopilot")
async def set_goal_autopilot(gid: str, body: GoalAutopilotIn, user: dict = Depends(get_current_user)):
    g = await db.goals.find_one({"id": gid, "user_id": user["id"]})
    if not g:
        raise HTTPException(404, "Goal not found")
    updates = {}
    if body.monthly_commit is not None:
        updates["monthly_commit"] = body.monthly_commit
    if body.linked_sip_id is not None:
        updates["linked_sip_id"] = body.linked_sip_id or None
    if updates:
        await db.goals.update_one({"id": gid}, {"$set": updates})
    return {"ok": True}

# ------------------ EMERGENCY FUND ------------------
ESSENTIAL_CATS = {"Rent", "Bills", "Food", "Healthcare"}

async def _emergency_stats(user: dict, months: int = 6):
    exps = await db.expenses.find({"user_id": user["id"], "type": {"$ne": "income"}}, {"_id": 0}).to_list(2000)
    cutoff = now_utc() - timedelta(days=90)
    ess = [e for e in exps if e.get("category") in ESSENTIAL_CATS and _parse_dt(e.get("date")) >= cutoff]
    monthly_essentials = sum(e["amount"] for e in ess) / 3 if ess else 0
    if monthly_essentials == 0:
        ym = now_utc().strftime("%Y-%m")
        monthly_essentials = sum(e["amount"] for e in exps if str(e.get("date", ""))[:7] == ym)
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    ef_goal = next((g for g in goals if "emergency" in g["title"].lower()), None)
    current = ef_goal.get("saved_amount", 0) if ef_goal else 0
    recommended = monthly_essentials * months
    gap = max(0, recommended - current)
    return {
        "monthly_essentials": round(monthly_essentials, 2),
        "months": months,
        "recommended": round(recommended, 2),
        "current": round(current, 2),
        "gap": round(gap, 2),
        "coverage_pct": round(min(100, (current / recommended * 100) if recommended else 100), 1),
        "goal_id": ef_goal["id"] if ef_goal else None,
        "goal_title": ef_goal["title"] if ef_goal else None,
    }

@api.get("/emergency-fund")
async def emergency_fund(user: dict = Depends(get_current_user), months: int = 6):
    months = max(3, min(12, months))
    stats = await _emergency_stats(user, months)
    plans = [{"months": m, "monthly_saving": round(stats["gap"] / m, 2)} for m in (6, 12, 18)] if stats["gap"] > 0 else []
    return {**stats, "plans": plans}

# ------------------ NET WORTH & ASSETS ------------------
@api.get("/assets")
async def list_assets(user: dict = Depends(get_current_user)):
    return await db.assets.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)

@api.post("/assets")
async def add_asset(body: AssetIn, user: dict = Depends(get_current_user)):
    doc = {"id": new_id(), "user_id": user["id"], **body.model_dump(), "created_at": now_iso()}
    await db.assets.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/assets/{aid}")
async def update_asset(aid: str, body: AssetUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.assets.update_one({"id": aid, "user_id": user["id"]}, {"$set": updates})
    return {"ok": True}

@api.delete("/assets/{aid}")
async def del_asset(aid: str, user: dict = Depends(get_current_user)):
    await db.assets.delete_one({"id": aid, "user_id": user["id"]})
    return {"ok": True}

@api.get("/networth")
async def networth(user: dict = Depends(get_current_user)):
    assets = await db.assets.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    holdings = await db.holdings.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    debts = await db.debts.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    invest_value = sum(h["units"] * h["current_price"] for h in holdings)
    goal_savings = sum(g.get("saved_amount", 0) for g in goals)
    auto_assets = []
    if invest_value > 0:
        auto_assets.append({"id": "auto-investments", "name": "Investment portfolio", "kind": "Investments", "value": round(invest_value, 2), "auto": True})
    if goal_savings > 0:
        auto_assets.append({"id": "auto-goals", "name": "Goal savings", "kind": "Savings", "value": round(goal_savings, 2), "auto": True})
    manual_total = sum(a["value"] for a in assets)
    assets_total = manual_total + invest_value + goal_savings
    liabilities = [{"id": d["id"], "name": d["name"], "value": d["balance"], "apr": d.get("apr")} for d in debts]
    liab_total = sum(d["balance"] for d in debts)
    return {
        "assets": {"manual": assets, "auto": auto_assets, "total": round(assets_total, 2)},
        "liabilities": {"items": liabilities, "total": round(liab_total, 2)},
        "net_worth": round(assets_total - liab_total, 2),
    }

# ------------------ SMART ALERTS ------------------
@api.get("/alerts")
async def smart_alerts(user: dict = Depends(get_current_user)):
    alerts = []
    cf = await cashflow_predict(user=user)
    for w in cf.get("warnings", [])[:1]:
        dstr = (now_utc() + timedelta(days=w["day"])).strftime("%b %d")
        alerts.append({"id": "risk-balance", "level": "risk", "title": "Balance risk ahead",
                       "message": f"Your balance may fall below ₹2,000 around {dstr}.", "route": "/app/cashflow"})
    ba = await budget_alerts(user=user)
    for a in ba["alerts"]:
        if a["level"] == "exceeded":
            alerts.append({"id": a["id"], "level": "risk", "title": f"{a['category']} budget exceeded",
                           "message": a["message"], "route": "/app/budgets", "pct": a["pct"]})
        elif a["level"] == "warning":
            alerts.append({"id": a["id"], "level": "spending", "title": f"{a['category']} budget at {int(a['pct'])}%",
                           "message": a["message"], "route": "/app/budgets", "pct": a["pct"]})
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    for g in goals:
        pace = _goal_pace(g)
        if pace["status"] == "ahead" and pace["variance"] > 0.02 * g["target_amount"]:
            alerts.append({"id": f"goal-win-{g['id']}", "level": "goal", "title": f"'{g['title']}' is ahead of schedule",
                           "message": f"You've saved ₹{int(pace['variance'])} more than required so far. Keep it up.", "route": "/app/goals"})
    week_ago = now_utc() - timedelta(days=7)
    contribs = await db.contributions.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    saved_week = sum(c["amount"] for c in contribs if _parse_dt(c["at"]) >= week_ago)
    if saved_week > 0:
        alerts.append({"id": "goal-week-save", "level": "goal", "title": "Great saving week",
                       "message": f"You put ₹{int(saved_week)} toward your goals in the last 7 days.", "route": "/app/recap"})
    prefs = user.get("notif_prefs") or {}
    allow = {"risk": prefs.get("risk_alerts", True), "spending": prefs.get("spending_alerts", True), "goal": prefs.get("goal_alerts", True)}
    alerts = [a for a in alerts if allow.get(a["level"], True)]
    order = {"risk": 0, "spending": 1, "goal": 2}
    alerts.sort(key=lambda a: order.get(a["level"], 3))
    return {"alerts": alerts, "count": len(alerts), "critical": sum(1 for a in alerts if a["level"] == "risk")}

# ------------------ AI ACTION CENTER ------------------
@api.get("/action-center")
async def action_center(user: dict = Depends(get_current_user)):
    now = now_utc()
    ym = now.strftime("%Y-%m")
    last_ym = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    exps = await db.expenses.find({"user_id": user["id"], "type": {"$ne": "income"}}, {"_id": 0}).to_list(2000)
    budgets = await db.budgets.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    debts = await db.debts.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    sips = await db.sips.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    insights = []

    cur, prev = {}, {}
    for e in exps:
        m = str(e.get("date", ""))[:7]
        if m == ym:
            cur[e["category"]] = cur.get(e["category"], 0) + e["amount"]
        elif m == last_ym:
            prev[e["category"]] = prev.get(e["category"], 0) + e["amount"]
    for cat, amt in cur.items():
        p = prev.get(cat, 0)
        if p >= 200 and amt >= 500 and amt > p * 1.25:
            pct = round((amt - p) / p * 100)
            insights.append({"id": f"spike-{cat}", "severity": "medium",
                             "title": f"Your {cat} spending is {pct}% higher this month",
                             "message": f"₹{int(amt)} so far vs ₹{int(p)} last month. Worth a quick look at where it went.",
                             "action_label": "Review expenses", "route": "/app/expenses"})

    over, near = [], []
    for b in budgets:
        spent = cur.get(b["category"], 0)
        pct = (spent / b["monthly_limit"] * 100) if b["monthly_limit"] else 0
        if spent > b["monthly_limit"]:
            over.append((b["category"], spent - b["monthly_limit"]))
        elif pct >= 85:
            near.append((b["category"], pct))
    if over:
        total_over = sum(o[1] for o in over)
        cats = ", ".join(o[0] for o in over[:3])
        insights.append({"id": "save-potential", "severity": "high",
                         "title": f"You can save ₹{int(total_over)} this month",
                         "message": f"You're over budget on {cats}. Pausing non-essentials there gets you back on track.",
                         "action_label": "Fix budgets", "route": "/app/budgets"})
    for cat, pct in near:
        insights.append({"id": f"near-{cat}", "severity": "medium",
                         "title": f"You've used {int(pct)}% of your {cat} budget",
                         "message": "Slow down here for the rest of the month to stay green.",
                         "action_label": "See budget", "route": "/app/budgets"})

    ef = await _emergency_stats(user)
    if ef["gap"] > 0:
        sev = "high" if ef["current"] < ef["recommended"] * 0.5 else "medium"
        insights.append({"id": "emergency-gap", "severity": sev,
                         "title": "Your emergency fund is below your target",
                         "message": f"You have ₹{int(ef['current'])} of the recommended ₹{int(ef['recommended'])} ({ef['coverage_pct']}%). Gap: ₹{int(ef['gap'])}.",
                         "action_label": "Plan my fund", "route": "/app/emergency"})

    for g in goals:
        pace = _goal_pace(g)
        if pace["status"] == "behind" and pace["months_off"] <= -1:
            insights.append({"id": f"goal-behind-{g['id']}", "severity": "high",
                             "title": f"On track to miss '{g['title']}' by {abs(int(round(pace['months_off'])))} months",
                             "message": f"Save ₹{int(pace['required_monthly'])}/month from now to still hit the deadline.",
                             "action_label": "Open goal", "route": "/app/goals"})
        elif pace["status"] == "ahead" and pace["variance"] > 0.02 * g["target_amount"]:
            insights.append({"id": f"goal-ahead-{g['id']}", "severity": "win",
                             "title": f"'{g['title']}' is ahead of schedule",
                             "message": f"₹{int(pace['variance'])} ahead of pace. Discipline pays.",
                             "action_label": "View goals", "route": "/app/goals"})

    high_apr = [d for d in debts if d.get("apr", 0) >= 20]
    if high_apr:
        d = max(high_apr, key=lambda x: x["apr"])
        monthly_interest = d["balance"] * d["apr"] / 100 / 12
        insights.append({"id": f"debt-{d['id']}", "severity": "high",
                         "title": f"'{d['name']}' is costing you ₹{int(monthly_interest)}/month in interest",
                         "message": f"{d['apr']}% APR on ₹{int(d['balance'])}. Every extra rupee here beats any investment.",
                         "action_label": "Kill this debt", "route": "/app/debts"})

    if not any(s.get("active", True) for s in sips):
        insights.append({"id": "no-sip", "severity": "low",
                         "title": "No active SIP running",
                         "message": "Even ₹500/month compounds into lakhs. Start small, start now.",
                         "action_label": "Start a SIP", "route": "/app/investments"})

    if not insights:
        insights.append({"id": "all-clear", "severity": "win",
                         "title": "All clear today",
                         "message": "Budgets healthy, goals on pace, no risks detected. Enjoy it — that's rare.",
                         "action_label": "See recap", "route": "/app/recap"})

    order = {"high": 0, "medium": 1, "low": 2, "win": 3}
    insights.sort(key=lambda i: order.get(i["severity"], 4))
    counts = {k: sum(1 for i in insights if i["severity"] == k) for k in ("high", "medium", "low", "win")}
    return {"insights": insights[:12], "counts": counts, "generated_at": now_iso()}

# ------------------ WEEKLY RECAP ------------------
@api.get("/recap/weekly")
async def weekly_recap(user: dict = Depends(get_current_user)):
    now = now_utc()
    wk = now - timedelta(days=7)
    prev_wk = now - timedelta(days=14)
    exps = await db.expenses.find({"user_id": user["id"], "type": {"$ne": "income"}}, {"_id": 0}).to_list(2000)
    week_exps = [e for e in exps if _parse_dt(e.get("date")) >= wk]
    prev_exps = [e for e in exps if prev_wk <= _parse_dt(e.get("date")) < wk]
    spent_week = sum(e["amount"] for e in week_exps)
    spent_prev = sum(e["amount"] for e in prev_exps)
    by_cat = {}
    for e in week_exps:
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + e["amount"]
    top_cat = max(by_cat.items(), key=lambda x: x[1]) if by_cat else None

    contribs = await db.contributions.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    saved_week = sum(c["amount"] for c in contribs if _parse_dt(c["at"]) >= wk)

    ym = now.strftime("%Y-%m")
    budgets = await db.budgets.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    total_limit = sum(b["monthly_limit"] for b in budgets)
    month_spend_budgeted = sum(e["amount"] for e in exps if str(e.get("date", ""))[:7] == ym and e["category"] in {b["category"] for b in budgets})
    budget_used_pct = round(month_spend_budgeted / total_limit * 100, 1) if total_limit else None

    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    total_target = sum(g["target_amount"] for g in goals)
    goal_delta_pct = round(saved_week / total_target * 100, 1) if total_target else 0

    health = await _health_data(user)
    score = health["overall"]
    today = now.date().isoformat()
    snaps = await db.health_snapshots.find({"user_id": user["id"]}, {"_id": 0}).sort("date", -1).to_list(60)
    prev_snap = next((s for s in snaps if s["date"] <= (now - timedelta(days=6)).date().isoformat()), None)
    score_delta = (score - prev_snap["score"]) if prev_snap else None
    await db.health_snapshots.update_one(
        {"user_id": user["id"], "date": today},
        {"$set": {"score": score, "user_id": user["id"], "date": today}}, upsert=True)

    return {
        "period": {"from": wk.date().isoformat(), "to": now.date().isoformat()},
        "saved": round(saved_week, 2),
        "spent": round(spent_week, 2),
        "spent_prev_week": round(spent_prev, 2),
        "spend_delta": round(spent_week - spent_prev, 2),
        "top_category": {"name": top_cat[0], "amount": round(top_cat[1], 2)} if top_cat else None,
        "budget_used_pct": budget_used_pct,
        "goal_progress_pct": goal_delta_pct,
        "streak_days": user.get("streak_days", 0),
        "health_score": score,
        "health_delta": score_delta,
        "nug_points": user.get("nug_points", 0),
    }

# ------------------ STREAK CHECK-IN ------------------
@api.post("/checkin")
async def daily_checkin(user: dict = Depends(get_current_user)):
    today = now_utc().date()
    last = user.get("last_checkin")
    if last == today.isoformat():
        raise HTTPException(400, "Already checked in today")
    streak = user.get("streak_days", 0)
    savers = user.get("streak_savers", 0)
    saver_used = False
    if last:
        gap = (today - datetime.fromisoformat(last).date()).days
        if gap == 1:
            streak += 1
        elif gap == 2 and savers > 0:
            savers -= 1
            saver_used = True
            streak += 1
        else:
            streak = 1
    else:
        streak += 1
    milestone_bonus = 0
    saver_earned = False
    if streak % 7 == 0:
        milestone_bonus = 50
        if savers < 3:
            savers += 1
            saver_earned = True
    total = 10 + milestone_bonus
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"streak_days": streak, "last_checkin": today.isoformat(), "streak_savers": savers},
         "$inc": {"nug_points": total}})
    note = f"Daily check-in (day {streak})" + (" + 7-day streak bonus" if milestone_bonus else "")
    if saver_used:
        note += " · streak-saver pass used"
    await db.nug_events.insert_one({
        "id": new_id(), "user_id": user["id"], "kind": "checkin",
        "points": total, "note": note, "at": now_iso()})
    return {"streak_days": streak, "points_earned": total, "milestone_bonus": milestone_bonus,
            "saver_used": saver_used, "saver_earned": saver_earned, "streak_savers": savers}

@api.get("/checkin/status")
async def checkin_status(user: dict = Depends(get_current_user)):
    today = now_utc().date().isoformat()
    streak = user.get("streak_days", 0)
    return {
        "checked_in_today": user.get("last_checkin") == today,
        "streak_days": streak,
        "streak_savers": user.get("streak_savers", 0),
        "next_milestone_in": (7 - (streak % 7)) if streak % 7 else 7,
    }

# ------------------ WHAT SHOULD I DO WITH MY MONEY (SIGNATURE) ------------------
ALLOC_DISCLAIMER = "Educational guidance based on your own data — not registered investment advice. NugVio never moves money."

@api.get("/allocate")
async def allocate_money(user: dict = Depends(get_current_user), amount: Optional[float] = None):
    now = now_utc()
    ym = now.strftime("%Y-%m")
    exps = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).to_list(2000)
    income_m = sum(e["amount"] for e in exps if e.get("type") == "income" and str(e.get("date", ""))[:7] == ym)
    spend_m = sum(e["amount"] for e in exps if e.get("type") != "income" and str(e.get("date", ""))[:7] == ym)
    surplus = max(0.0, income_m - spend_m)
    amt = float(amount) if amount and amount > 0 else (round(surplus) if surplus >= 1000 else 10000.0)

    debts = await db.debts.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
    ef = await _emergency_stats(user)

    weights, meta = {}, {}
    high = [d for d in debts if d["balance"] > 0 and d.get("apr", 0) >= 15]
    if high:
        weights["debt"] = 35
        meta["debt"] = max(high, key=lambda x: x["apr"])
    if ef["gap"] > 0:
        weights["emergency"] = 25 if ef["coverage_pct"] < 50 else 15
    if goals:
        paces = [(g, _goal_pace(g)) for g in goals]
        behind = [gp for gp in paces if gp[1]["status"] == "behind"]
        meta["goals"] = (behind or paces)[0]
        weights["goals"] = 20 if behind else 12
    weights["invest"] = 20
    weights["flex"] = 10
    total_w = sum(weights.values())

    items = []
    keys = list(weights)
    allocated = 0.0
    for i, k in enumerate(keys):
        a = round(amt - allocated) if i == len(keys) - 1 else round(amt * weights[k] / total_w)
        allocated += a
        pct = round(a / amt * 100) if amt else 0
        if k == "debt":
            d = meta["debt"]
            before = _simulate_debts(debts)
            after = _simulate_debts([{**x, "balance": max(0, x["balance"] - a) if x["id"] == d["id"] else x["balance"]} for x in debts])
            items.append({
                "key": k, "label": f"Pay down {d['name']}", "amount": a, "pct": pct,
                "reasoning": f"At {d['apr']}% APR this debt costs you ~₹{int(d['balance'] * d['apr'] / 1200)}/month in interest — clearing it is the highest guaranteed return you can get.",
                "impact": f"Saves ~₹{int(max(0, before['total_interest'] - after['total_interest']))} in future interest and {max(0, before['months'] - after['months'])} month(s) of repayment.",
                "route": "/app/debts", "action_label": "Pay it now",
            })
        elif k == "emergency":
            new_cov = round(min(100, (ef["current"] + a) / ef["recommended"] * 100), 1) if ef["recommended"] else 100
            items.append({
                "key": k, "label": "Emergency fund", "amount": a, "pct": pct,
                "reasoning": f"Your safety net covers {ef['coverage_pct']}% of the recommended ₹{int(ef['recommended'])} — a gap of ₹{int(ef['gap'])} leaves you exposed to surprises.",
                "impact": f"Coverage grows {ef['coverage_pct']}% → {new_cov}%.",
                "route": "/app/emergency", "action_label": "Top up fund",
            })
        elif k == "goals":
            g, pace = meta["goals"]
            months_cov = round(a / pace["required_monthly"], 1) if pace["required_monthly"] else 0
            why = f"'{g['title']}' is behind schedule and needs ₹{int(pace['required_monthly'])}/month to hit its deadline." if pace["status"] == "behind" else f"'{g['title']}' needs ₹{int(pace['required_monthly'])}/month to stay on track."
            items.append({
                "key": k, "label": f"Goal: {g['title']}", "amount": a, "pct": pct,
                "reasoning": why,
                "impact": f"Covers {months_cov} month(s) of required saving for this goal.",
                "route": "/app/goals", "action_label": "Contribute",
            })
        elif k == "invest":
            fv = a * (1.12 ** 10)
            items.append({
                "key": k, "label": "Invest (SIP / index funds)", "amount": a, "pct": pct,
                "reasoning": "Money invested early compounds — long-term index investing historically beats idle cash.",
                "impact": f"Could grow to ~₹{int(fv)} in 10 years at 12% average return.",
                "route": "/app/investments", "action_label": "Set up SIP",
            })
        else:
            items.append({
                "key": k, "label": "Flexible spending", "amount": a, "pct": pct,
                "reasoning": "Plans fail when there's no room for fun. Guilt-free money keeps the rest of the plan sustainable.",
                "impact": "Keeps your budget realistic — and your streak alive.",
                "route": "/app/budgets", "action_label": "View budgets",
            })
    return {
        "amount": round(amt, 2), "surplus": round(surplus, 2),
        "income_month": round(income_m, 2), "spend_month": round(spend_m, 2),
        "items": items, "disclaimer": ALLOC_DISCLAIMER,
    }

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

async def seed_investments_demo():
    admin_email = os.environ.get("ADMIN_EMAIL", "demo@nugvio.in")
    u = await db.users.find_one({"email": admin_email})
    if not u:
        return
    if await db.holdings.find_one({"user_id": u["id"]}):
        return
    holdings = [
        ("Nippon India Small Cap", "MF", 120.5, 82.4, 118.6),
        ("Parag Parikh Flexi Cap", "MF", 85.2, 55.1, 68.3),
        ("HDFC Bank", "Stock", 30, 1420, 1685),
        ("Tata Digital Gold", "Gold", 8.4, 5900, 7250),
        ("SBI PPF", "FD", 1, 50000, 54000),
    ]
    for name, kind, units, avg, cur in holdings:
        await db.holdings.insert_one({
            "id": new_id(), "user_id": u["id"], "name": name, "kind": kind,
            "units": units, "avg_price": avg, "current_price": cur, "created_at": now_iso()
        })
    sips = [
        ("Nippon India Small Cap SIP", 2500, "2024-06-01", 15.0),
        ("Parag Parikh Flexi Cap SIP", 3000, "2024-03-15", 13.0),
        ("Nifty 50 Index SIP", 1500, "2025-01-10", 12.0),
    ]
    for name, amt, start, ret in sips:
        await db.sips.insert_one({
            "id": new_id(), "user_id": u["id"], "name": name,
            "monthly_amount": amt, "start_date": start, "expected_return": ret,
            "active": True, "created_at": now_iso()
        })

async def seed_wealth_demo():
    admin_email = os.environ.get("ADMIN_EMAIL", "demo@nugvio.in")
    u = await db.users.find_one({"email": admin_email})
    if not u:
        return
    if not await db.assets.find_one({"user_id": u["id"]}):
        for name, kind, val in [("HDFC Savings Account", "Bank", 42000), ("Cash in hand", "Cash", 2500)]:
            await db.assets.insert_one({"id": new_id(), "user_id": u["id"], "name": name, "kind": kind, "value": val, "created_at": now_iso()})
    if not await db.contributions.find_one({"user_id": u["id"]}):
        goals = await db.goals.find({"user_id": u["id"]}, {"_id": 0}).to_list(10)
        for i, g in enumerate(goals[:2]):
            await db.contributions.insert_one({
                "id": new_id(), "user_id": u["id"], "goal_id": g["id"], "goal_title": g["title"],
                "amount": 1200 + i * 800, "at": (now_utc() - timedelta(days=2 + i * 2)).isoformat()
            })
    if not await db.health_snapshots.find_one({"user_id": u["id"]}):
        await db.health_snapshots.insert_one({
            "user_id": u["id"], "date": (now_utc() - timedelta(days=8)).date().isoformat(), "score": 68
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
    await seed_investments_demo()
    await seed_wealth_demo()

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
