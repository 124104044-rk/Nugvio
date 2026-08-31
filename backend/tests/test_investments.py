"""Backend tests for Nugvio Investments feature + regression smoke."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://finpilot-preview-7.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
DEMO_EMAIL = "demo@nugvio.in"
DEMO_PASSWORD = "Nugvio@123"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    t = r.json().get("token")
    assert t
    return t


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Auth requirement ----------
class TestAuthRequired:
    @pytest.mark.parametrize("path", [
        "/investments/summary",
        "/investments/holdings",
        "/investments/sips",
        "/investments/projection",
    ])
    def test_unauth_401(self, path):
        r = requests.get(f"{API}{path}", timeout=15)
        assert r.status_code in (401, 403), f"{path} unexpected {r.status_code}"


# ---------- Summary / Projection ----------
class TestSummary:
    def test_summary_shape(self, auth):
        r = requests.get(f"{API}/investments/summary", headers=auth, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["invested", "current_value", "gain", "gain_pct", "monthly_sip",
                  "allocation", "best", "worst", "holdings_count", "sips_count"]:
            assert k in d, f"missing {k}"
        assert d["invested"] > 0, "expected seeded holdings"
        assert d["holdings_count"] >= 1
        assert d["monthly_sip"] > 0, "expected seeded SIPs"
        assert isinstance(d["allocation"], list) and len(d["allocation"]) >= 1
        assert d["best"] is not None

    def test_projection(self, auth):
        r = requests.get(f"{API}/investments/projection", headers=auth, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "series" in d and len(d["series"]) == 10
        assert d["final_value"] > d["total_invested"] > 0
        assert d["monthly_sip"] > 0


# ---------- Holdings CRUD ----------
class TestHoldings:
    def test_list_seeded(self, auth):
        r = requests.get(f"{API}/investments/holdings", headers=auth, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and len(rows) >= 1
        h = rows[0]
        for k in ["id", "name", "kind", "units", "avg_price", "current_price",
                  "invested", "current", "gain", "gain_pct"]:
            assert k in h

    def test_create_delete_holding(self, auth):
        payload = {"name": "TEST_HOLD", "kind": "Stock", "units": 10, "avg_price": 100, "current_price": 120}
        r = requests.post(f"{API}/investments/holdings", json=payload, headers=auth, timeout=15)
        assert r.status_code == 200, r.text
        hid = r.json()["id"]
        # verify in list
        r2 = requests.get(f"{API}/investments/holdings", headers=auth, timeout=15)
        ids = [h["id"] for h in r2.json()]
        assert hid in ids
        # verify summary reflects
        s = requests.get(f"{API}/investments/summary", headers=auth, timeout=15).json()
        assert s["invested"] >= 1000
        # delete
        rd = requests.delete(f"{API}/investments/holdings/{hid}", headers=auth, timeout=15)
        assert rd.status_code == 200
        r3 = requests.get(f"{API}/investments/holdings", headers=auth, timeout=15)
        assert hid not in [h["id"] for h in r3.json()]

    def test_holding_validation(self, auth):
        r = requests.post(f"{API}/investments/holdings",
                          json={"name": "x", "kind": "Stock", "units": 0, "avg_price": 10, "current_price": 10},
                          headers=auth, timeout=15)
        assert r.status_code == 422


# ---------- SIPs CRUD ----------
class TestSIPs:
    def test_list_seeded(self, auth):
        r = requests.get(f"{API}/investments/sips", headers=auth, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and len(rows) >= 1
        s = rows[0]
        for k in ["id", "name", "monthly_amount", "expected_return", "start_date",
                  "active", "months_run", "invested_so_far"]:
            assert k in s

    def test_create_toggle_delete(self, auth):
        payload = {"name": "TEST_SIP", "monthly_amount": 2000, "start_date": "2024-01-01", "expected_return": 12}
        r = requests.post(f"{API}/investments/sips", json=payload, headers=auth, timeout=15)
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        assert r.json()["active"] is True

        # summary monthly_sip should include new sip
        s1 = requests.get(f"{API}/investments/summary", headers=auth, timeout=15).json()
        base_monthly = s1["monthly_sip"]
        assert base_monthly >= 2000

        # pause
        rp = requests.patch(f"{API}/investments/sips/{sid}", json={"active": False}, headers=auth, timeout=15)
        assert rp.status_code == 200
        s2 = requests.get(f"{API}/investments/summary", headers=auth, timeout=15).json()
        assert s2["monthly_sip"] == round(base_monthly - 2000, 2)

        # resume
        rr = requests.patch(f"{API}/investments/sips/{sid}", json={"active": True}, headers=auth, timeout=15)
        assert rr.status_code == 200

        # delete
        rd = requests.delete(f"{API}/investments/sips/{sid}", headers=auth, timeout=15)
        assert rd.status_code == 200
        r3 = requests.get(f"{API}/investments/sips", headers=auth, timeout=15)
        assert sid not in [x["id"] for x in r3.json()]


# ---------- Regression smoke ----------
class TestRegression:
    @pytest.mark.parametrize("path", [
        "/auth/me",
        "/expenses",
        "/budgets",
        "/insights/summary",
    ])
    def test_endpoints_ok(self, auth, path):
        r = requests.get(f"{API}{path}", headers=auth, timeout=20)
        assert r.status_code == 200, f"{path} => {r.status_code} {r.text[:200]}"
