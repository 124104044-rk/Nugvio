"""Offline tests for Phase 1 security limits: login lockout, AI Coach allowance,
message length limits and password rules.

Runs against an in-memory Mongo (mongomock-motor), no live backend or Gemini needed:
    cd backend && python -m pytest tests/test_security_limits.py -q
"""
import asyncio
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


# ---------- AI Coach: shared helpers ----------
#
# Concurrency tests are event-driven: the fake Gemini can hold a request until the test
# releases it, and the race tests pause a specific count query on an asyncio.Event.
# No test relies on a sleep to order events.

GEMINI_HOST = "generativelanguage.googleapis.com"
TIP = "Here's a tip."


class _GeminiResponse:
    def __init__(self, text):
        self._text = text

    def raise_for_status(self):
        pass

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": self._text}]}}]}


class FakeGemini:
    """Stands in for Gemini; every other httpx call stays real.

    text: what the model returns. fail: raise a network error. hold: wait for
    `release` before answering. hang: never answer (only a deadline ends it)."""

    def __init__(self, monkeypatch, *, text=TIP, fail=False, hold=False, hang=False):
        self.text, self.fail, self.hold, self.hang = text, fail, hold, hang
        self.calls = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        real_post = httpx.AsyncClient.post
        fake = self

        async def post(client, url, *args, **kwargs):
            if GEMINI_HOST not in str(url):
                return await real_post(client, url, *args, **kwargs)
            fake.calls += 1
            fake.entered.set()
            if fake.hang:
                await asyncio.Event().wait()  # never set
            if fake.hold:
                await fake.release.wait()
            if fake.fail:
                raise httpx.ReadTimeout("simulated Gemini outage")
            return _GeminiResponse(fake.text)

        monkeypatch.setenv("GEMINI_API_KEY", "test-not-a-real-key")
        monkeypatch.setattr(httpx.AsyncClient, "post", post)


def assert_clean(server):
    """No reservations, no held or awaited locks, and sane per-user counters.

    Per-user locks and completion counters intentionally persist (see server.py)."""
    assert server._coach_inflight == {}
    for lock in server._coach_locks.values():
        assert not lock.locked()
        assert not getattr(lock, "_waiters", None)
    for uid, n in getattr(server, "_coach_completions", {}).items():
        assert isinstance(n, int) and n >= 0, (uid, n)


def assert_no_pending_tasks():
    me = asyncio.current_task()
    pending = [t for t in asyncio.all_tasks() if t is not me and not t.done()]
    assert pending == [], pending


async def counted_replies(server, uid=None):
    q = {"role": "coach", "text": {"$nin": [server.COACH_OFFLINE_REPLY,
                                             getattr(server, "COACH_FALLBACK_REPLY", server.COACH_OFFLINE_REPLY)]}}
    if uid:
        q["user_id"] = uid
    return await server.db.coach_messages.count_documents(q)


async def until(condition):
    """Yield to the event loop until condition() holds (progress-based, not time-based)."""
    for _ in range(10_000):
        if condition():
            return
        await asyncio.sleep(0)
    raise AssertionError("condition never became true")


@pytest.fixture()
def gemini(monkeypatch):
    return FakeGemini(monkeypatch)


# ---------- AI Coach allowance and message limits ----------

def test_free_user_gets_5_coach_messages_per_day(srv, gemini):
    _, c, tok = srv
    for i in range(5):
        r = coach(c, tok)
        assert r.status_code == 200 and r.json()["reply"] == TIP, i
    r = coach(c, tok)
    assert r.status_code == 429
    assert "today's 5 AI Coach messages" in r.json()["detail"]


def test_blocked_message_is_not_saved(srv, gemini):
    server, c, tok = srv
    for _ in range(6):
        coach(c, tok)
    n = asyncio.run(server.db.coach_messages.count_documents({"role": "user"}))
    assert n == 5


def test_yesterdays_messages_do_not_count(srv, gemini):
    server, c, tok = srv
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    uid = c.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["id"]
    asyncio.run(server.db.coach_messages.insert_many([
        {"id": f"o{i}", "user_id": uid, "session_id": "s1", "role": "coach", "text": "old", "at": old} for i in range(9)]))
    assert coach(c, tok).status_code == 200


def test_gemini_failures_do_not_use_up_the_allowance(srv, monkeypatch):
    _, c, tok = srv
    FakeGemini(monkeypatch, fail=True)
    for _ in range(8):
        r = coach(c, tok)
        assert r.status_code == 200
        assert "offline" in r.json()["reply"]


def test_demo_account_gets_a_higher_allowance(srv, gemini):
    server, c, _ = srv
    demo = os.environ.get("ADMIN_EMAIL", "demo@nugvio.in")
    c.post("/api/auth/register", json={"name": "Demo", "email": demo, "password": PW})
    tok = login(c, email=demo).json()["token"]
    for i in range(server.COACH_DAILY_LIMIT + 3):
        r = coach(c, tok)
        assert r.status_code == 200 and r.json()["reply"] == TIP, i


def test_coach_message_length_is_capped(srv, gemini):
    server, c, tok = srv
    assert coach(c, tok, "x" * server.COACH_MAX_CHARS).status_code == 200
    assert coach(c, tok, "x" * (server.COACH_MAX_CHARS + 1)).status_code == 422
    assert coach(c, tok, "").status_code == 422


def test_coach_still_requires_login(srv):
    _, c, _ = srv
    c.cookies.clear()
    assert c.post("/api/coach/chat", json={"session_id": "s1", "text": "hi"}).status_code == 401


def test_ist_day_start_is_midnight_in_india():
    server = _load_server(ORIGIN)
    start = datetime.fromisoformat(server.ist_day_start_iso()).astimezone(server.IST)
    assert (start.hour, start.minute, start.second) == (0, 0, 0)
    assert datetime.now(server.IST) - start < timedelta(days=1)


# ---------- empty / unusable Gemini replies ----------

@pytest.mark.parametrize("model_text", [
    "",
    "   \n ",
    'ACTIONS: [{"label": "Open budgets", "route": "/app/budgets"}]',
])
def test_empty_or_unusable_reply_shows_the_fallback_and_does_not_count(srv, monkeypatch, model_text):
    server, c, tok = srv
    FakeGemini(monkeypatch, text=model_text)
    for _ in range(server.COACH_DAILY_LIMIT + 3):
        r = coach(c, tok)
        assert r.status_code == 200
        assert r.json() == {"reply": server.COACH_FALLBACK_REPLY, "actions": []}
    stored = asyncio.run(server.db.coach_messages.distinct("text", {"role": "coach"}))
    assert stored == [server.COACH_FALLBACK_REPLY]
    # the allowance is untouched: a real answer still works
    FakeGemini(monkeypatch, text=TIP)
    assert coach(c, tok).json()["reply"] == TIP


def test_reply_with_text_and_actions_still_counts_and_keeps_its_actions(srv, monkeypatch):
    server, c, tok = srv
    FakeGemini(monkeypatch, text='Trim dining out.\nACTIONS: [{"label": "Open budgets", "route": "/app/budgets"}]')
    for _ in range(server.COACH_DAILY_LIMIT):
        r = coach(c, tok)
        assert r.json() == {"reply": "Trim dining out.", "actions": [{"label": "Open budgets", "route": "/app/budgets"}]}
    assert coach(c, tok).status_code == 429


def test_no_api_key_fallback_is_not_counted(srv):
    server, c, tok = srv  # srv removes GEMINI_API_KEY
    for _ in range(server.COACH_DAILY_LIMIT + 2):
        r = coach(c, tok)
        assert r.status_code == 200 and r.json()["reply"] == server.COACH_FALLBACK_REPLY


# ---------- AI Coach concurrency (reservations), event-driven ----------

def _run(server, scenario):
    """Run a scenario against the app on ONE event loop, then check nothing is left behind."""
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
            result = await asyncio.wait_for(scenario(ask), timeout=20)  # watchdog against deadlocks only
            assert_clean(server)
            assert_no_pending_tasks()
            return result
    return asyncio.run(main())


@pytest.fixture()
def bare_server(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    server = _load_server(ORIGIN)
    server._login_failures.clear()
    return server


def test_simultaneous_requests_cannot_exceed_the_daily_allowance(bare_server, monkeypatch):
    fake = FakeGemini(monkeypatch, hold=True)

    async def scenario(ask):
        tasks = [asyncio.create_task(ask(f"q{i}")) for i in range(12)]
        # every request has either been refused or is waiting inside Gemini
        await until(lambda: sum(t.done() for t in tasks) + fake.calls == 12)
        refused_while_others_wait = sum(t.done() for t in tasks)
        fake.release.set()
        return await asyncio.gather(*tasks), refused_while_others_wait, await counted_replies(bare_server)
    results, refused, counted = _run(bare_server, scenario)
    assert fake.calls == bare_server.COACH_DAILY_LIMIT == 5     # all 5 slots used at once, never more
    assert refused == 7
    assert sum(r.status_code == 200 for r in results) == 5
    assert sum(r.status_code == 429 for r in results) == 7
    assert counted == 5


def test_simultaneous_requests_near_the_limit_allow_exactly_the_remaining_slots(bare_server, monkeypatch):
    fake = FakeGemini(monkeypatch)

    async def scenario(ask):
        for i in range(bare_server.COACH_DAILY_LIMIT - 1):        # use 4 of 5
            assert (await ask(f"seq{i}")).status_code == 200
        fake.hold = True
        tasks = [asyncio.create_task(ask(f"b{i}")) for i in range(6)]
        await until(lambda: sum(t.done() for t in tasks) + (fake.calls - 4) == 6)
        fake.release.set()
        burst = await asyncio.gather(*tasks)
        return burst, await ask("after burst"), await counted_replies(bare_server)
    burst, final, counted = _run(bare_server, scenario)
    assert sum(r.status_code == 200 for r in burst) == 1
    assert sum(r.status_code == 429 for r in burst) == 5
    assert final.status_code == 429 and "today's 5 AI Coach messages" in final.json()["detail"]
    assert counted == 5


def test_waiting_request_gets_a_clear_message(bare_server, monkeypatch):
    fake = FakeGemini(monkeypatch)

    async def scenario(ask):
        for i in range(bare_server.COACH_DAILY_LIMIT - 1):
            await ask(f"seq{i}")
        fake.hold, fake.entered = True, asyncio.Event()
        first = asyncio.create_task(ask("slow one"))
        await fake.entered.wait()                       # first is now inside Gemini
        second = await ask("impatient")
        fake.release.set()
        return await first, second
    first, second = _run(bare_server, scenario)
    assert first.status_code == 200
    assert second.status_code == 429 and "still being answered" in second.json()["detail"]


def test_failed_gemini_request_releases_its_reservation(bare_server, monkeypatch):
    fake = FakeGemini(monkeypatch)

    async def scenario(ask):
        for i in range(bare_server.COACH_DAILY_LIMIT - 1):
            assert (await ask(f"seq{i}")).status_code == 200
        fake.fail, fake.hold = True, True
        tasks = [asyncio.create_task(ask(f"f{i}")) for i in range(3)]
        await until(lambda: sum(t.done() for t in tasks) + (fake.calls - 4) == 3)
        fake.release.set()
        failed = await asyncio.gather(*tasks)
        reserved_after_failure = dict(bare_server._coach_inflight)
        fake.fail, fake.hold = False, False
        return failed, reserved_after_failure, await ask("retry after outage"), await ask("one too many")
    failed, reserved_after_failure, ok, over = _run(bare_server, scenario)
    assert sum(r.status_code == 200 and "offline" in r.json()["reply"] for r in failed) == 1
    assert sum(r.status_code == 429 for r in failed) == 2
    assert reserved_after_failure == {}
    assert ok.status_code == 200 and ok.json()["reply"] == TIP
    assert over.status_code == 429


def test_unexpected_error_releases_its_reservation(bare_server, monkeypatch):
    async def boom(body, user):
        raise RuntimeError("simulated crash")
    monkeypatch.setattr(bare_server, "_coach_reply", boom)

    async def scenario(ask):
        with pytest.raises(RuntimeError):
            await ask("crash")
    _run(bare_server, scenario)


def test_cancelled_request_releases_its_reservation_and_does_not_count(bare_server, monkeypatch):
    fake = FakeGemini(monkeypatch, hold=True)

    async def scenario(ask):
        task = asyncio.create_task(ask("will be cancelled"))
        await fake.entered.wait()
        assert sum(bare_server._coach_inflight.values()) == 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return await counted_replies(bare_server)
    assert _run(bare_server, scenario) == 0


def test_cancelled_while_waiting_for_the_users_lock_leaves_no_state(bare_server, monkeypatch):
    FakeGemini(monkeypatch)
    Coll = type(bare_server.db.coach_messages)
    real_count = Coll.count_documents
    gate = {"armed": True, "counting": asyncio.Event(), "go": asyncio.Event()}

    async def held_count(self, *a, **k):
        n = await real_count(self, *a, **k)
        if self.name == "coach_messages" and gate["armed"]:
            gate["armed"] = False
            gate["counting"].set()
            await gate["go"].wait()                 # first request holds the user's lock here
        return n
    monkeypatch.setattr(Coll, "count_documents", held_count)

    async def scenario(ask):
        first = asyncio.create_task(ask("first"))
        await gate["counting"].wait()
        waiter = asyncio.create_task(ask("waits for the lock"))
        await until(lambda: bare_server._coach_locks and next(iter(bare_server._coach_locks.values()))._waiters)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        gate["go"].set()
        return (await first).status_code
    assert _run(bare_server, scenario) == 200


def test_different_users_do_not_block_each_other(bare_server, monkeypatch):
    fake = FakeGemini(monkeypatch, hold=True)

    async def main():
        transport = httpx.ASGITransport(app=bare_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            toks = []
            for e in ("u1@x.in", "u2@x.in"):
                await ac.post("/api/auth/register", json={"name": "U", "email": e, "password": PW})
                ac.cookies.clear()
                toks.append((await ac.post("/api/auth/login", json={"email": e, "password": PW})).json()["token"])
                ac.cookies.clear()
            tasks = [asyncio.create_task(ac.post("/api/coach/chat", json={"session_id": "s", "text": "hi"},
                                                 headers={"Authorization": f"Bearer {t}"})) for t in toks]
            await until(lambda: fake.calls == 2)        # both users are inside Gemini at the same time
            fake.release.set()
            results = await asyncio.gather(*tasks)
            assert_clean(bare_server)
            assert_no_pending_tasks()
            return results
    assert [r.status_code for r in asyncio.run(main())] == [200, 200]


def test_many_users_bursting_together_never_deadlock_or_exceed(bare_server, monkeypatch):
    fake = FakeGemini(monkeypatch, hold=True)

    async def main():
        transport = httpx.ASGITransport(app=bare_server.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            heads = []
            for n in range(4):
                e = f"m{n}@x.in"
                await ac.post("/api/auth/register", json={"name": "M", "email": e, "password": PW})
                ac.cookies.clear()
                heads.append({"Authorization": "Bearer " + (await ac.post("/api/auth/login", json={"email": e, "password": PW})).json()["token"]})
                ac.cookies.clear()
            tasks = [asyncio.create_task(ac.post("/api/coach/chat", json={"session_id": "s", "text": f"q{i}"}, headers=h))
                     for i in range(8) for h in heads]
            await until(lambda: sum(t.done() for t in tasks) + fake.calls == len(tasks))
            fake.release.set()
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=20)
            assert_clean(bare_server)
            assert_no_pending_tasks()
            per_user = [await bare_server.db.coach_messages.count_documents(
                {"role": "coach", "text": TIP, "user_id": u["id"]}) for u in await bare_server.db.users.find({}).to_list(10)]
            return results, per_user
    results, per_user = asyncio.run(main())
    assert sum(r.status_code == 200 for r in results) == 4 * 5
    assert sorted(per_user) == [5, 5, 5, 5]


# ---------- the stale-count race from the 23 Nov review ----------
#
# Scenario: 4 of 5 replies used; request X holds the 5th slot. Request Y's count is
# evaluated while X is still in flight (it sees 4), but the result reaches Y only after
# X has saved its reply and released its slot. Y must not take a 6th slot.

def _pause_one_count(monkeypatch, server):
    """Pause the next armed coach_messages count AFTER it is evaluated, until `go` is set."""
    Coll = type(server.db.coach_messages)
    real_count = Coll.count_documents
    gate = {"armed": False, "evaluated": asyncio.Event(), "go": asyncio.Event(), "stale_value": None}

    async def count(self, *a, **k):
        n = await real_count(self, *a, **k)
        if self.name == "coach_messages" and gate["armed"]:
            gate["armed"] = False
            gate["stale_value"] = n
            gate["evaluated"].set()
            await gate["go"].wait()                 # result arrives late
        return n
    monkeypatch.setattr(Coll, "count_documents", count)
    return gate


async def _save_reply(server, uid):
    await server.db.coach_messages.insert_one({
        "id": server.new_id(), "user_id": uid, "session_id": "s", "role": "coach",
        "text": TIP, "actions": [], "at": server.now_iso()})


def test_stale_count_race_cannot_grant_a_sixth_reply(bare_server, monkeypatch):
    server, user = bare_server, {"id": "race-user", "email": "race@x.in"}
    gate = _pause_one_count(monkeypatch, server)

    async def main():
        y_key = None
        for _ in range(4):
            await _save_reply(server, user["id"])
        x_key = await server.coach_reserve(user)               # X: 5th slot, in flight
        gate["armed"] = True
        y = asyncio.create_task(server.coach_reserve(user))
        try:
            await gate["evaluated"].wait()                     # Y's count = 4 (X not saved yet)
            await _save_reply(server, user["id"])              # X finishes: save, then release
            server.coach_release(x_key)
            gate["go"].set()                                   # Y's stale result arrives now
            try:
                y_key = await y
                outcome = "reserved"
            except server.HTTPException as e:
                outcome = e.status_code, e.detail
            return gate["stale_value"], outcome, await counted_replies(server, user["id"])
        finally:
            gate["go"].set()
            if not y.done():
                y.cancel()
            await asyncio.gather(y, return_exceptions=True)
            if y_key is not None:                              # only on a broken implementation
                server.coach_release(y_key)
            assert_clean(server)
            assert_no_pending_tasks()
            if hasattr(server, "_coach_completions"):          # one finished request per release
                assert server._coach_completions == {user["id"]: 1 + (y_key is not None)}
    stale, outcome, counted = asyncio.run(main())
    assert stale == 4                                          # the race really happened
    assert counted == 5
    assert outcome == (429, "You've used today's 5 AI Coach messages. They reset at midnight (IST).")


def test_stale_count_race_through_the_app(bare_server, monkeypatch):
    """The same race end to end over HTTP: Y must get 429, never a 6th reply."""
    fake = FakeGemini(monkeypatch)
    gate = _pause_one_count(monkeypatch, bare_server)

    async def scenario(ask):
        for i in range(4):
            assert (await ask(f"seq{i}")).status_code == 200
        fake.hold, fake.entered = True, asyncio.Event()
        x = asyncio.create_task(ask("X"))
        await fake.entered.wait()                              # X holds the 5th slot, inside Gemini
        gate["armed"] = True
        y = asyncio.create_task(ask("Y"))
        try:
            await gate["evaluated"].wait()                     # Y counted 4
            fake.release.set()
            rx = await x                                       # X saved its reply and released
            gate["go"].set()
            ry = await y
        finally:
            fake.release.set()
            gate["go"].set()
            await asyncio.gather(x, y, return_exceptions=True)
        return gate["stale_value"], rx, ry, await counted_replies(bare_server)
    stale, rx, ry, counted = _run(bare_server, scenario)
    assert stale == 4
    assert rx.status_code == 200 and rx.json()["reply"] == TIP
    assert ry.status_code == 429, ry.text
    assert counted == 5


@pytest.mark.parametrize("x_finishes", ["before_y_counts", "while_y_counts", "after_y_decides"])
def test_no_ordering_of_a_finishing_request_exceeds_the_limit(bare_server, monkeypatch, x_finishes):
    server, user = bare_server, {"id": "order-user", "email": "order@x.in"}
    gate = _pause_one_count(monkeypatch, server)

    async def main():
        for _ in range(4):
            await _save_reply(server, user["id"])
        x_key = await server.coach_reserve(user)
        granted = []

        async def finish_x():
            await _save_reply(server, user["id"])
            server.coach_release(x_key)

        if x_finishes == "before_y_counts":
            await finish_x()
        gate["armed"] = x_finishes == "while_y_counts"
        y = asyncio.create_task(server.coach_reserve(user))
        if x_finishes == "while_y_counts":
            await gate["evaluated"].wait()
            await finish_x()
            gate["go"].set()
        try:
            granted.append(await y)
        except server.HTTPException as e:
            refusal = e.detail
        else:
            refusal = None
        if x_finishes == "after_y_decides":
            await finish_x()
        for k in granted:                                      # a granted Y would save a reply
            await _save_reply(server, user["id"])
            server.coach_release(k)
        total = await counted_replies(server, user["id"])
        assert_clean(server)
        assert_no_pending_tasks()
        if hasattr(server, "_coach_completions"):
            assert server._coach_completions == {user["id"]: 1 + len(granted)}
        return total, refusal
    total, refusal = asyncio.run(main())
    assert total <= 5
    assert total == 5
    assert refusal is not None


# ---------- overall Gemini deadline ----------

def test_gemini_overall_deadline_ends_a_trickling_call(bare_server, monkeypatch):
    fake = FakeGemini(monkeypatch, hang=True)                  # never answers
    monkeypatch.setattr(bare_server, "GEMINI_TOTAL_TIMEOUT_SEC", 0.05)

    async def scenario(ask):
        r = await ask("will time out")
        return r, await counted_replies(bare_server)
    r, counted = _run(bare_server, scenario)                   # _run also checks no slot/lock/task is left
    assert fake.calls == 1
    assert r.status_code == 200
    assert r.json() == {"reply": bare_server.COACH_OFFLINE_REPLY, "actions": []}
    assert counted == 0


def test_after_a_deadline_timeout_the_full_allowance_remains(bare_server, monkeypatch):
    fake = FakeGemini(monkeypatch, hang=True)
    monkeypatch.setattr(bare_server, "GEMINI_TOTAL_TIMEOUT_SEC", 0.05)

    async def scenario(ask):
        for _ in range(3):
            assert (await ask("times out")).json()["reply"] == bare_server.COACH_OFFLINE_REPLY
        fake.hang = False
        ok = [await ask(f"q{i}") for i in range(bare_server.COACH_DAILY_LIMIT)]
        return ok, await ask("one too many")
    ok, over = _run(bare_server, scenario)
    assert all(r.json()["reply"] == TIP for r in ok)
    assert over.status_code == 429


def test_deadline_defaults():
    server = _load_server(ORIGIN)
    assert server.GEMINI_STAGE_TIMEOUT_SEC == 90.0
    assert server.GEMINI_TOTAL_TIMEOUT_SEC == 100.0
