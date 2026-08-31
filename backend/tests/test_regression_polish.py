"""Regression tests for NugVio polish pass:
- Expenses CRUD (incl PATCH), filters (q/type/category/date_from/date_to)
- Income exclusion from budgets, health-score month spend
- /api/me PATCH (name/currency/notif_prefs)
- Alerts respects notif_prefs.spending_alerts
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"
EMAIL = "demo@nugvio.in"
PASSWORD = "Nugvio@123"


@pytest.fixture(scope="module")
def auth():
    r = requests.post(f"{API}/auth/login",
                      json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# -------- Auth me / Branding response --------
class TestAuthMe:
    def test_me(self, auth):
        r = requests.get(f"{API}/auth/me", headers=auth, timeout=15)
        assert r.status_code == 200
        u = r.json()
        assert u["email"] == EMAIL
        assert "password_hash" not in u


# -------- Expenses CRUD + PATCH --------
class TestExpensesCrudPatch:
    def test_add_edit_delete_expense(self, auth):
        # ADD expense
        r = requests.post(f"{API}/expenses", headers=auth, timeout=20,
                          json={"description": "TEST_ zomato lunch", "amount": 250})
        assert r.status_code == 200, r.text
        e = r.json()
        eid = e["id"]
        assert e["type"] == "expense"
        assert e["amount"] == 250
        # category auto-assigned via keyword
        assert e["category"] == "Food"

        # PATCH amount
        rp = requests.patch(f"{API}/expenses/{eid}", headers=auth, timeout=15,
                            json={"amount": 275})
        assert rp.status_code == 200, rp.text
        assert rp.json()["amount"] == 275

        # GET verify
        rg = requests.get(f"{API}/expenses?q=TEST_", headers=auth, timeout=15)
        assert rg.status_code == 200
        rows = rg.json()
        found = [x for x in rows if x["id"] == eid]
        assert found and found[0]["amount"] == 275

        # DELETE
        rd = requests.delete(f"{API}/expenses/{eid}", headers=auth, timeout=15)
        assert rd.status_code == 200
        assert rd.json().get("deleted") == 1


# -------- Filters --------
class TestExpensesFilters:
    def test_filter_q_type_category_daterange(self, auth):
        # seed 2 items
        r1 = requests.post(f"{API}/expenses", headers=auth, timeout=15,
                           json={"description": "TEST_filterA netflix", "amount": 199,
                                 "category": "Entertainment"}).json()
        r2 = requests.post(f"{API}/expenses", headers=auth, timeout=15,
                           json={"description": "TEST_filterB salary", "amount": 100,
                                 "type": "income", "category": "Salary"}).json()
        ids = [r1["id"], r2["id"]]
        try:
            # q filter
            rows = requests.get(f"{API}/expenses?q=TEST_filter", headers=auth, timeout=15).json()
            assert len([x for x in rows if x["id"] in ids]) == 2

            # type=expense excludes income
            rows = requests.get(f"{API}/expenses?type=expense&q=TEST_filter",
                                headers=auth, timeout=15).json()
            got_ids = [x["id"] for x in rows]
            assert r1["id"] in got_ids
            assert r2["id"] not in got_ids

            # type=income only
            rows = requests.get(f"{API}/expenses?type=income&q=TEST_filter",
                                headers=auth, timeout=15).json()
            got_ids = [x["id"] for x in rows]
            assert r2["id"] in got_ids
            assert r1["id"] not in got_ids

            # category filter
            rows = requests.get(f"{API}/expenses?category=Entertainment&q=TEST_filter",
                                headers=auth, timeout=15).json()
            assert any(x["id"] == r1["id"] for x in rows)

            # date range (super wide)
            rows = requests.get(
                f"{API}/expenses?date_from=2020-01-01&date_to=2099-01-01&q=TEST_filter",
                headers=auth, timeout=15).json()
            assert len([x for x in rows if x["id"] in ids]) == 2

            # date range that excludes everything
            rows = requests.get(
                f"{API}/expenses?date_from=1990-01-01&date_to=1990-01-02&q=TEST_filter",
                headers=auth, timeout=15).json()
            assert not any(x["id"] in ids for x in rows)
        finally:
            for i in ids:
                requests.delete(f"{API}/expenses/{i}", headers=auth, timeout=15)


# -------- Income exclusion critical --------
class TestIncomeExclusion:
    def test_income_not_in_budget_spent_or_health_month_spend(self, auth):
        # get baselines
        hs_before = requests.get(f"{API}/health-score", headers=auth, timeout=15).json()
        bud_before = requests.get(f"{API}/budgets", headers=auth, timeout=15).json()
        # sum of "spent" fields
        spent_before = sum(b.get("spent", 0) for b in bud_before) if isinstance(bud_before, list) else 0
        month_before = ((hs_before.get("totals") or {}).get("month_spend")
                        or hs_before.get("month_spend") or 0)

        # add BIG income
        r = requests.post(f"{API}/expenses", headers=auth, timeout=15,
                          json={"description": "TEST_INCOME_HUGE", "amount": 99999,
                                "type": "income", "category": "Salary"}).json()
        iid = r["id"]
        try:
            hs_after = requests.get(f"{API}/health-score", headers=auth, timeout=15).json()
            bud_after = requests.get(f"{API}/budgets", headers=auth, timeout=15).json()
            spent_after = sum(b.get("spent", 0) for b in bud_after) if isinstance(bud_after, list) else 0
            month_after = ((hs_after.get("totals") or {}).get("month_spend")
                           or hs_after.get("month_spend") or 0)
            # Should be unchanged (income excluded)
            assert abs(spent_after - spent_before) < 1.0, \
                f"budget spent inflated by income: before={spent_before} after={spent_after}"
            assert abs(month_after - month_before) < 1.0, \
                f"month_spend inflated: before={month_before} after={month_after}"
        finally:
            requests.delete(f"{API}/expenses/{iid}", headers=auth, timeout=15)


# -------- /api/me PATCH --------
class TestMePatch:
    def test_patch_name_currency_notif(self, auth):
        me = requests.get(f"{API}/auth/me", headers=auth, timeout=15).json()
        orig_name = me.get("name") or ""
        orig_currency = me.get("currency") or "INR"
        orig_prefs = me.get("notif_prefs") or {}

        # patch
        r = requests.patch(f"{API}/me", headers=auth, timeout=15, json={
            "name": "TEST_Nug User",
            "currency": "USD",
            "notif_prefs": {"risk_alerts": True, "spending_alerts": False, "goal_alerts": True},
        })
        assert r.status_code == 200, r.text
        u = r.json()
        assert u["name"] == "TEST_Nug User"
        assert u["currency"] == "USD"
        assert u["notif_prefs"]["spending_alerts"] is False

        # Alerts should not include level=spending now
        al = requests.get(f"{API}/alerts", headers=auth, timeout=15).json()
        assert all(a.get("level") != "spending" for a in al.get("alerts", [])), \
            "spending alerts leaked despite pref off"

        # Restore prefs -> spending alerts allowed again
        rr = requests.patch(f"{API}/me", headers=auth, timeout=15, json={
            "name": orig_name or "Nugvio Demo",
            "currency": orig_currency,
            "notif_prefs": {"risk_alerts": True, "spending_alerts": True, "goal_alerts": True},
        })
        assert rr.status_code == 200
        u2 = rr.json()
        assert u2["currency"] == orig_currency
        assert u2["notif_prefs"]["spending_alerts"] is True
