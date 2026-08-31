"""Backend tests for 7 new Nugvio features:
Action Center, Health Score Breakdown, Emergency Fund, Net Worth, Alerts,
Goals Autopilot, Weekly Recap.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"
DEMO_EMAIL = "demo@nugvio.in"
DEMO_PASSWORD = "Nugvio@123"


@pytest.fixture(scope="module")
def auth():
    r = requests.post(f"{API}/auth/login",
                      json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------- Auth requirement ----------
class TestAuthRequired:
    @pytest.mark.parametrize("path", [
        "/action-center", "/health-score/breakdown", "/emergency-fund",
        "/networth", "/alerts", "/goals-autopilot", "/recap/weekly",
    ])
    def test_401(self, path):
        r = requests.get(f"{API}{path}", timeout=15)
        assert r.status_code in (401, 403)


# ---------- Action Center ----------
class TestActionCenter:
    def test_shape_and_sort(self, auth):
        r = requests.get(f"{API}/action-center", headers=auth, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "insights" in d
        assert isinstance(d["insights"], list)
        prio = {"high": 0, "medium": 1, "low": 2, "win": 3}
        levels = [prio.get(i.get("level", "low"), 9) for i in d["insights"]]
        assert levels == sorted(levels), f"insights not sorted: {levels}"
        for i in d["insights"]:
            for k in ["title", "message", "action_label", "route"]:
                assert k in i, f"missing {k} in insight"


# ---------- Health Score Breakdown ----------
class TestHealthBreakdown:
    def test_shape(self, auth):
        r = requests.get(f"{API}/health-score/breakdown", headers=auth, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "overall" in d and "target" in d
        assert "components" in d and len(d["components"]) == 6
        expected_max = {"savings": 25, "spending": 20, "debt": 20,
                        "emergency": 15, "investments": 10, "discipline": 10}
        by_key = {c["key"]: c for c in d["components"]}
        for k, m in expected_max.items():
            assert k in by_key, f"missing component {k}"
            assert by_key[k]["max"] == m, f"max mismatch {k}: {by_key[k]['max']}"
            assert "points" in by_key[k]
            assert 0 <= by_key[k]["points"] <= m
        total_max = sum(c["max"] for c in d["components"])
        assert total_max == 100
        assert "actions" in d and len(d["actions"]) == 3
        for a in d["actions"]:
            assert "potential_gain" in a

    def test_old_health_score_still_works(self, auth):
        r = requests.get(f"{API}/health-score", headers=auth, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "overall" in d
        assert "sub_scores" in d or "components" in d  # legacy shape


# ---------- Emergency Fund ----------
class TestEmergencyFund:
    def test_default(self, auth):
        r = requests.get(f"{API}/emergency-fund", headers=auth, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["monthly_essentials", "recommended", "current", "gap",
                  "coverage_pct", "plans"]:
            assert k in d

    def test_months_param_changes_recommended(self, auth):
        r6 = requests.get(f"{API}/emergency-fund?months=6", headers=auth, timeout=15).json()
        r12 = requests.get(f"{API}/emergency-fund?months=12", headers=auth, timeout=15).json()
        r3 = requests.get(f"{API}/emergency-fund?months=3", headers=auth, timeout=15).json()
        assert r12["recommended"] > r6["recommended"] > r3["recommended"]


# ---------- Net Worth + Assets CRUD ----------
class TestNetWorth:
    def test_shape(self, auth):
        r = requests.get(f"{API}/networth", headers=auth, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "assets" in d and "liabilities" in d and "net_worth" in d
        assets = d["assets"]
        liabs = d["liabilities"]
        all_assets = assets["manual"] + assets["auto"]
        a_total = sum(x["value"] for x in all_assets)
        l_total = sum(x["value"] for x in liabs["items"])
        assert abs(assets["total"] - a_total) < 1.0
        assert abs(liabs["total"] - l_total) < 1.0
        assert abs(d["net_worth"] - (a_total - l_total)) < 1.0
        auto_names = [x["name"].lower() for x in assets["auto"]]
        assert any("investment" in n for n in auto_names), auto_names
        assert any("goal" in n for n in auto_names), auto_names

    def test_asset_crud(self, auth):
        payload = {"name": "TEST_ASSET_X", "kind": "Cash", "value": 12345}
        rc = requests.post(f"{API}/assets", json=payload, headers=auth, timeout=15)
        assert rc.status_code in (200, 201), rc.text
        aid = rc.json()["id"]
        nw = requests.get(f"{API}/networth", headers=auth, timeout=15).json()
        assert any(a.get("id") == aid for a in nw["assets"]["manual"])
        rp = requests.patch(f"{API}/assets/{aid}", json={"value": 20000}, headers=auth, timeout=15)
        assert rp.status_code == 200
        nw2 = requests.get(f"{API}/networth", headers=auth, timeout=15).json()
        found = [a for a in nw2["assets"]["manual"] if a.get("id") == aid][0]
        assert found["value"] == 20000
        rd = requests.delete(f"{API}/assets/{aid}", headers=auth, timeout=15)
        assert rd.status_code in (200, 204)
        nw3 = requests.get(f"{API}/networth", headers=auth, timeout=15).json()
        assert not any(a.get("id") == aid for a in nw3["assets"]["manual"])


# ---------- Alerts ----------
class TestAlerts:
    def test_shape(self, auth):
        r = requests.get(f"{API}/alerts", headers=auth, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "alerts" in d
        allowed = {"risk", "spending", "goal"}
        for a in d["alerts"]:
            assert a.get("level") in allowed, f"bad level {a.get('level')}"


# ---------- Goals Autopilot ----------
class TestGoalsAutopilot:
    def test_list(self, auth):
        r = requests.get(f"{API}/goals-autopilot", headers=auth, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "goals" in d
        for g in d["goals"]:
            for k in ["id", "required_monthly", "committed_monthly", "status"]:
                assert k in g

    def test_patch_autopilot_and_sip_link(self, auth):
        # get a goal
        goals = requests.get(f"{API}/goals", headers=auth, timeout=15).json()
        assert isinstance(goals, list) and len(goals) >= 1
        gid = goals[0]["id"]
        # get a sip
        sips = requests.get(f"{API}/investments/sips", headers=auth, timeout=15).json()
        assert len(sips) >= 1
        sip = sips[0]
        # patch
        rp = requests.patch(f"{API}/goals/{gid}/autopilot",
                            json={"monthly_commit": 3000, "linked_sip_id": sip["id"]},
                            headers=auth, timeout=15)
        assert rp.status_code == 200, rp.text
        # verify via list
        after = requests.get(f"{API}/goals-autopilot", headers=auth, timeout=15).json()
        target = [g for g in after["goals"] if g["id"] == gid][0]
        # committed_monthly reflects commit + linked sip amount
        assert target["committed_monthly"] >= 3000
        # unlink for cleanup
        requests.patch(f"{API}/goals/{gid}/autopilot",
                       json={"monthly_commit": 0, "linked_sip_id": None},
                       headers=auth, timeout=15)


# ---------- Weekly Recap ----------
class TestRecap:
    def test_shape(self, auth):
        r = requests.get(f"{API}/recap/weekly", headers=auth, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["saved", "spent", "spend_delta", "budget_used_pct",
                  "goal_progress_pct", "streak_days", "health_score", "health_delta"]:
            assert k in d, f"missing {k}"

    def test_contribution_increases_saved(self, auth):
        goals = requests.get(f"{API}/goals", headers=auth, timeout=15).json()
        gid = goals[0]["id"]
        before = requests.get(f"{API}/recap/weekly", headers=auth, timeout=15).json()["saved"]
        rc = requests.post(f"{API}/goals/{gid}/contribute",
                           json={"amount": 500}, headers=auth, timeout=15)
        assert rc.status_code in (200, 201), rc.text
        after = requests.get(f"{API}/recap/weekly", headers=auth, timeout=15).json()["saved"]
        assert after >= before + 500 - 1
