"""Offline tests for /api/auth/me authentication behaviour and CORS.

Runs against an in-memory Mongo (mongomock-motor), so it needs no live backend:
    cd backend && python -m pytest tests/test_auth_startup.py -q
"""
import importlib
import os
import sys
import types
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest

pytest.importorskip("mongomock_motor")
from mongomock_motor import AsyncMongoMockClient  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SECRET = "test-secret-long-enough-for-hs256-key"
ORIGIN = "https://nugvio-app.vercel.app"


def _load_server(cors_origins):
    os.environ.update({"JWT_SECRET": SECRET, "MONGO_URL": "mongodb://localhost:27017",
                       "DB_NAME": "nugvio_test", "CORS_ORIGINS": cors_origins})
    # The private LLM package isn't needed for auth; stub it if it's not installed.
    if "emergentintegrations" not in sys.modules:
        try:
            importlib.import_module("emergentintegrations.llm.chat")
        except ImportError:
            chat = types.ModuleType("emergentintegrations.llm.chat")
            chat.LlmChat = chat.UserMessage = object
            for name, mod in {"emergentintegrations": types.ModuleType("emergentintegrations"),
                              "emergentintegrations.llm": types.ModuleType("emergentintegrations.llm"),
                              "emergentintegrations.llm.chat": chat}.items():
                sys.modules[name] = mod
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.modules.pop("server", None)
    server = importlib.import_module("server")
    server.db = AsyncMongoMockClient()["nugvio_test"]
    server.app.router.on_startup.clear()  # skip demo seeding against a real DB
    return server


@pytest.fixture()
def env():
    server = _load_server(ORIGIN)
    with TestClient(server.app) as c:
        c.post("/api/auth/register", json={"name": "T", "email": "t@x.in", "password": "Passw0rd!"})
        c.cookies.clear()
        tok = c.post("/api/auth/login", json={"email": "t@x.in", "password": "Passw0rd!"}).json()["token"]
        c.cookies.clear()
        yield server, c, tok


def _expired(sub="nobody"):
    now = datetime.now(timezone.utc)
    return pyjwt.encode({"sub": sub, "email": "t@x.in", "exp": now - timedelta(minutes=1),
                         "iat": now - timedelta(days=1)}, SECRET, algorithm="HS256")


def test_me_missing_token_is_401(env):
    _, c, _ = env
    r = c.get("/api/auth/me")
    assert r.status_code == 401 and r.json()["detail"] == "Not authenticated"


def test_me_valid_bearer_is_200(env):
    _, c, tok = env
    r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "t@x.in" and "password_hash" not in body


def test_me_expired_bearer_is_401(env):
    _, c, _ = env
    r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {_expired()}"})
    assert r.status_code == 401 and r.json()["detail"] == "Token expired"


def test_me_garbage_bearer_is_401(env):
    _, c, _ = env
    r = c.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401 and r.json()["detail"] == "Invalid token"


def test_stale_cookie_no_longer_masks_valid_bearer(env):
    # Previously the cookie was checked exclusively, so a stale cookie => 401 even
    # with a perfectly valid Authorization header.
    _, c, tok = env
    c.cookies.set("access_token", _expired())
    r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200


def test_valid_cookie_still_works(env):
    _, c, tok = env
    c.cookies.set("access_token", tok)
    assert c.get("/api/auth/me").status_code == 200


def test_both_invalid_still_401(env):
    _, c, _ = env
    c.cookies.set("access_token", _expired())
    r = c.get("/api/auth/me", headers={"Authorization": "Bearer junk"})
    assert r.status_code == 401


def test_logout_then_protected_route_401(env):
    _, c, _ = env
    c.post("/api/auth/logout")
    assert c.get("/api/auth/me").status_code == 401


def test_wrong_password_401(env):
    _, c, _ = env
    r = c.post("/api/auth/login", json={"email": "t@x.in", "password": "wrong"})
    assert r.status_code == 401


def test_cors_allows_credentials_for_explicit_origin(env):
    _, c, _ = env
    r = c.get("/api/auth/me", headers={"Origin": ORIGIN})
    assert r.status_code == 401
    assert r.headers.get("access-control-allow-origin") == ORIGIN
    assert r.headers.get("access-control-allow-credentials") == "true"
    pre = c.options("/api/auth/me", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET",
                                             "Access-Control-Request-Headers": "authorization"})
    assert pre.status_code == 200
    assert pre.headers.get("access-control-allow-credentials") == "true"

