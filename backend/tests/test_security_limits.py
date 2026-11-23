"""Offline tests for Phase 1 security limits: login lockout, AI Coach allowance,
message length limits and password rules.

Runs against an in-memory Mongo (mongomock-motor), no live backend or Gemini needed:
    cd backend && python -m pytest tests/test_security_limits.py -q
"""
import os
from datetime import datetime, timedelta, timezone

import httpx
import pytest

pytest.importorskip("mongomock_motor")
from fastapi.testclient import TestClient  # noqa: E402

from tests.test_auth_startup import ORIGIN, _load_server  # noqa: E402

PW = "Passw0rd!"


@pytest.fixture()
def srv(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    server = _load_server(ORIGIN)
    server._login_failures.clear()
    with TestClient(server.app) as c:
        r = c.post("/api/auth/register", json={"name": "T", "email": "t@x.in", "password": PW})
        assert r.status_code == 200, r.text
        c.cookies.clear()
        yield server, c, r.json()["token"]


def login(c, email="t@x.in", pw=PW, ip="203.0.113.7", spoof=None):
    xff = f"{spoof}, {ip}" if spoof else ip
    c.cookies.clear()
    return c.post("/api/auth/login", json={"email": email, "password": pw}, headers={"X-Forwarded-For": xff})


def coach(c, tok, text="How am I doing?"):
    return c.post("/api/coach/chat", json={"session_id": "s1", "text": text},
                  headers={"Authorization": f"Bearer {tok}"})


# ---------- login brute-force protection ----------

def test_correct_password_logs_in(srv):
    _, c, _ = srv
    assert login(c).status_code == 200


def test_five_wrong_passwords_lock_that_account_from_that_address(srv):
    _, c, _ = srv
    for _ in range(5):
        assert login(c, pw="wrong").status_code == 401
    r = login(c)  # even the right password is refused while locked
    assert r.status_code == 429
    assert "Too many failed login attempts" in r.json()["detail"]
    assert int(r.headers["retry-after"]) > 0


def test_lockout_does_not_block_the_same_account_from_another_address(srv):
    # an attacker can't lock a real user (or the public demo account) out
    _, c, _ = srv
    for _ in range(5):
        login(c, pw="wrong", ip="198.51.100.1")
    assert login(c, ip="198.51.100.2").status_code == 200


def test_spoofed_forwarded_for_cannot_dodge_the_lock(srv):
    # Render appends the real address last; a fake first entry must be ignored
    _, c, _ = srv
    for i in range(5):
        login(c, pw="wrong", spoof=f"10.0.0.{i}")
    assert login(c, spoof="10.9.9.9").status_code == 429


def test_lock_expires_after_the_window(srv):
    server, c, _ = srv
    for _ in range(5):
        login(c, pw="wrong")
    for k in server._login_failures:
        server._login_failures[k] = [t - server.LOGIN_WINDOW_SEC - 1 for t in server._login_failures[k]]
    assert login(c).status_code == 200


def test_success_resets_the_account_counter(srv):
    _, c, _ = srv
    for _ in range(4):
        login(c, pw="wrong")
    assert login(c).status_code == 200
    for _ in range(4):
        assert login(c, pw="wrong").status_code == 401
    assert login(c).status_code == 200


def test_password_spraying_from_one_address_is_limited(srv):
    server, c, _ = srv
    for i in range(server.LOGIN_MAX_FAILS_PER_IP):
        login(c, email=f"victim{i}@x.in", pw="guess", ip="192.0.2.50")
    assert login(c, ip="192.0.2.50").status_code == 429
    assert login(c, ip="192.0.2.51").status_code == 200


# ---------- password rules ----------

def test_new_accounts_need_8_characters(srv):
    _, c, _ = srv
    r = c.post("/api/auth/register", json={"name": "N", "email": "n@x.in", "password": "short7!"})
    assert r.status_code == 422
    r = c.post("/api/auth/register", json={"name": "N", "email": "n@x.in", "password": "longer8!"})
    assert r.status_code == 200


def test_existing_short_passwords_can_still_log_in(srv):
    server, c, _ = srv
    import asyncio
    asyncio.get_event_loop().run_until_complete(server.db.users.insert_one(
        {"id": "old", "email": "old@x.in", "name": "Old", "password_hash": server.hash_pw("abc123")}))
    assert login(c, email="old@x.in", pw="abc123").status_code == 200


# ---------- AI Coach allowance and message limits ----------

def test_free_user_gets_5_coach_messages_per_day(srv):
    _, c, tok = srv
    for i in range(5):
        assert coach(c, tok).status_code == 200, i
    r = coach(c, tok)
    assert r.status_code == 429
    assert "today's 5 AI Coach messages" in r.json()["detail"]


def test_blocked_message_is_not_saved(srv):
    server, c, tok = srv
    for _ in range(6):
        coach(c, tok)
    import asyncio
    n = asyncio.get_event_loop().run_until_complete(
        server.db.coach_messages.count_documents({"role": "user"}))
    assert n == 5


def test_yesterdays_messages_do_not_count(srv):
    server, c, tok = srv
    import asyncio
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    uid = c.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["id"]
    asyncio.get_event_loop().run_until_complete(server.db.coach_messages.insert_many([
        {"id": f"o{i}", "user_id": uid, "session_id": "s1", "role": "coach", "text": "old", "at": old} for i in range(9)]))
    assert coach(c, tok).status_code == 200


def test_gemini_failures_do_not_use_up_the_allowance(srv, monkeypatch):
    _, c, tok = srv
    monkeypatch.setenv("GEMINI_API_KEY", "test-not-a-real-key")

    async def boom(*a, **k):
        raise httpx.ReadTimeout("simulated outage")
    monkeypatch.setattr(httpx.AsyncClient, "post", boom)
    for _ in range(8):
        r = coach(c, tok)
        assert r.status_code == 200
        assert "offline" in r.json()["reply"]


def test_demo_account_gets_a_higher_allowance(srv):
    server, c, _ = srv
    demo = os.environ.get("ADMIN_EMAIL", "demo@nugvio.in")
    c.post("/api/auth/register", json={"name": "Demo", "email": demo, "password": PW})
    tok = login(c, email=demo).json()["token"]
    for i in range(server.COACH_DAILY_LIMIT + 3):
        assert coach(c, tok).status_code == 200, i


def test_coach_message_length_is_capped(srv):
    server, c, tok = srv
    assert coach(c, tok, "x" * server.COACH_MAX_CHARS).status_code == 200
    assert coach(c, tok, "x" * (server.COACH_MAX_CHARS + 1)).status_code == 422
    assert coach(c, tok, "").status_code == 422


def test_coach_still_requires_login(srv):
    _, c, _ = srv
    c.cookies.clear()
    assert c.post("/api/coach/chat", json={"session_id": "s1", "text": "hi"}).status_code == 401


def test_ist_day_start_is_midnight_in_india():
    from tests.test_auth_startup import _load_server as load
    server = load(ORIGIN)
    start = datetime.fromisoformat(server.ist_day_start_iso()).astimezone(server.IST)
    assert (start.hour, start.minute, start.second) == (0, 0, 0)
    assert datetime.now(server.IST) - start < timedelta(days=1)


# ---------- AI Coach concurrency (reservations) ----------
import asyncio  # noqa: E402

GEMINI_HOST = "generativelanguage.googleapis.com"


class _FakeGeminiResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": "Here's a tip."}]}}]}


def _patch_gemini(monkeypatch, *, delay=0.3, fail=False):
    """Fake Gemini (slow, optionally failing) while leaving every other httpx call real."""
    real_post = httpx.AsyncClient.post
    calls = {"n": 0}

    async def fake_post(self, url, *args, **kwargs):
        if GEMINI_HOST in str(url):
            calls["n"] += 1
            await asyncio.sleep(delay)
            if fail:
                raise httpx.ReadTimeout("simulated Gemini outage")
            return _FakeGeminiResponse()
        return await real_post(self, url, *args, **kwargs)

    monkeypatch.setenv("GEMINI_API_KEY", "test-not-a-real-key")
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    return calls


def _run(server, scenario):
    """Run an async scenario against the app on ONE event loop (locks are loop-bound)."""
    async def main():
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            await ac.post("/api/auth/register", json={"name": "C", "email": "c@x.in", "password": PW})
            ac.cookies.clear()
            tok = (await ac.post("/api/auth/login", json={"email": "c@x.in", "password": PW})).json()["token"]
            ac.cookies.clear()
            h = {"Authorization": f"Bearer {tok}"}

            async def ask(text="hi"):
                return await ac.post("/api/coach/chat", json={"session_id": "s1", "text": text}, headers=h)
            return await scenario(ask)
    return asyncio.run(main())


@pytest.fixture()
def bare_server(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    server = _load_server(ORIGIN)
    server._login_failures.clear()
    return server


def test_simultaneous_requests_cannot_exceed_the_daily_allowance(bare_server, monkeypatch):
    calls = _patch_gemini(monkeypatch, delay=0.3)

    async def scenario(ask):
        return await asyncio.gather(*[ask(f"q{i}") for i in range(12)])
    results = _run(bare_server, scenario)
    ok = [r for r in results if r.status_code == 200]
    limited = [r for r in results if r.status_code == 429]
    assert len(ok) + len(limited) == 12
    assert len(ok) <= bare_server.COACH_DAILY_LIMIT
    assert calls["n"] == len(ok)  # blocked requests never reach Gemini

    # nothing is left reserved once requests finish
    assert bare_server._coach_inflight == {}


def test_simultaneous_requests_near_the_limit_allow_exactly_the_remaining_slots(bare_server, monkeypatch):
    _patch_gemini(monkeypatch, delay=0.3)

    async def scenario(ask):
        for i in range(bare_server.COACH_DAILY_LIMIT - 1):       # use 4 of 5
            assert (await ask(f"seq{i}")).status_code == 200
        burst = await asyncio.gather(*[ask(f"b{i}") for i in range(6)])
        final = await ask("after burst")
        return burst, final
    burst, final = _run(bare_server, scenario)
    assert sum(r.status_code == 200 for r in burst) == 1
    assert sum(r.status_code == 429 for r in burst) == 5
    assert final.status_code == 429
    assert "today's 5 AI Coach messages" in final.json()["detail"]


def test_waiting_request_gets_a_clear_message(bare_server, monkeypatch):
    _patch_gemini(monkeypatch, delay=0.5)

    async def scenario(ask):
        for i in range(bare_server.COACH_DAILY_LIMIT - 1):
            await ask(f"seq{i}")
        first = asyncio.create_task(ask("slow one"))
        await asyncio.sleep(0.1)
        second = await ask("impatient")
        return await first, second
    first, second = _run(bare_server, scenario)
    assert first.status_code == 200
    assert second.status_code == 429
    assert "still being answered" in second.json()["detail"]


def test_failed_gemini_request_releases_its_reservation(bare_server, monkeypatch):
    async def scenario(ask):
        for i in range(bare_server.COACH_DAILY_LIMIT - 1):
            assert (await ask(f"seq{i}")).status_code == 200   # no key: default reply, counted
        _patch_gemini(monkeypatch, delay=0.2, fail=True)
        failed = await asyncio.gather(*[ask(f"f{i}") for i in range(3)])
        reserved_after_failure = dict(bare_server._coach_inflight)
        _patch_gemini(monkeypatch, delay=0.05, fail=False)
        ok = await ask("retry after outage")
        over = await ask("one too many")
        return failed, reserved_after_failure, ok, over
    failed, reserved_after_failure, ok, over = _run(bare_server, scenario)
    # one failed attempt went to Gemini, the others waited; none used up the allowance
    assert any(r.status_code == 200 and "offline" in r.json()["reply"] for r in failed)
    assert reserved_after_failure == {}
    assert ok.status_code == 200 and "offline" not in ok.json()["reply"]
    assert over.status_code == 429


def test_unexpected_error_releases_its_reservation(bare_server, monkeypatch):
    async def boom(body, user):
        raise RuntimeError("simulated crash")
    monkeypatch.setattr(bare_server, "_coach_reply", boom)

    async def scenario(ask):
        try:
            await ask("crash")
        except RuntimeError:
            pass
        return dict(bare_server._coach_inflight)
    assert _run(bare_server, scenario) == {}


def test_different_users_do_not_block_each_other(bare_server, monkeypatch):
    _patch_gemini(monkeypatch, delay=0.3)

    async def main():
        transport = httpx.ASGITransport(app=bare_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            toks = []
            for e in ("u1@x.in", "u2@x.in"):
                await ac.post("/api/auth/register", json={"name": "U", "email": e, "password": PW})
                ac.cookies.clear()
                toks.append((await ac.post("/api/auth/login", json={"email": e, "password": PW})).json()["token"])
                ac.cookies.clear()
            reqs = [ac.post("/api/coach/chat", json={"session_id": "s", "text": "hi"},
                            headers={"Authorization": f"Bearer {t}"}) for t in toks]
            return await asyncio.gather(*reqs)
    assert [r.status_code for r in asyncio.run(main())] == [200, 200]
