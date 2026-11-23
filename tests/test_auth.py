"""
Tests for the Firebase token dependency and for route protection.

firebase_admin.auth.verify_id_token is replaced with a fake: the token
"token-alice" belongs to uid "alice"; "token-expired" raises the expiry
error; anything else is invalid.
"""
import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from firebase_admin import auth

import main
import routes.progress
from services.auth import get_current_uid


def fake_verify_id_token(token, *args, **kwargs):
    if token == "token-alice":
        return {"uid": "alice"}
    if token == "token-expired":
        raise auth.ExpiredIdTokenError("Token expired", cause=None)
    if token == "token-keys-down":
        raise auth.CertificateFetchError("Could not fetch keys", cause=None)
    raise auth.InvalidIdTokenError("Invalid token")


@pytest.fixture(autouse=True)
def fake_firebase_auth(monkeypatch):
    monkeypatch.setattr(auth, "verify_id_token", fake_verify_id_token)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ── The dependency on its own ────────────────────────────────────────────────

@pytest.fixture
def whoami_client():
    app = FastAPI()

    @app.get("/whoami")
    def whoami(uid: str = Depends(get_current_uid)):
        return {"uid": uid}

    return TestClient(app)


def test_valid_token_returns_uid(whoami_client):
    r = whoami_client.get("/whoami", headers=bearer("token-alice"))
    assert r.status_code == 200
    assert r.json() == {"uid": "alice"}


def test_missing_header_is_401(whoami_client):
    r = whoami_client.get("/whoami")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Basic dXNlcjpwYXNz", "Bearer", "token-alice", ""])
def test_malformed_header_is_401(whoami_client, header):
    r = whoami_client.get("/whoami", headers={"Authorization": header})
    assert r.status_code == 401


@pytest.mark.parametrize("token", ["not-a-real-token", "token-expired"])
def test_invalid_or_expired_token_is_401(whoami_client, token):
    r = whoami_client.get("/whoami", headers=bearer(token))
    assert r.status_code == 401


def test_key_fetch_failure_is_503(whoami_client):
    r = whoami_client.get("/whoami", headers=bearer("token-keys-down"))
    assert r.status_code == 503


# ── A protected route: GET /progress/{user_id} ───────────────────────────────

@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def fake_progress_store(monkeypatch):
    """Replace the Firestore helpers used by routes.progress and record calls."""
    calls = []

    def get_document(collection, doc_id):
        calls.append((collection, doc_id))
        if collection == "users" and doc_id == "alice":
            return {"id": "alice", "login_streak": 2, "longest_streak": 5}
        return None

    def query_collection(collection, filters):
        calls.append((collection, filters))
        return []

    monkeypatch.setattr(routes.progress, "get_document", get_document)
    monkeypatch.setattr(routes.progress, "query_collection", query_collection)
    return calls


def test_progress_without_token_is_401(client, fake_progress_store):
    r = client.get("/progress/alice")
    assert r.status_code == 401
    assert fake_progress_store == []


def test_progress_with_invalid_token_is_401(client, fake_progress_store):
    r = client.get("/progress/alice", headers=bearer("forged"))
    assert r.status_code == 401
    assert fake_progress_store == []


def test_progress_for_another_user_is_403(client, fake_progress_store):
    r = client.get("/progress/bob", headers=bearer("token-alice"))
    assert r.status_code == 403
    # The database is never read for someone else's data
    assert fake_progress_store == []


def test_progress_for_own_user_succeeds(client, fake_progress_store):
    r = client.get("/progress/alice", headers=bearer("token-alice"))
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == "alice"
    assert body["login_streak"] == 2
    assert body["longest_streak"] == 5
    assert body["topics"] == []


def test_body_user_id_mismatch_is_403(client, monkeypatch):
    called = []
    monkeypatch.setattr(routes.progress, "get_document", lambda *a: called.append(a))
    r = client.post("/progress/streak/update", json={"user_id": "bob"},
                    headers=bearer("token-alice"))
    assert r.status_code == 403
    assert called == []


def test_health_needs_no_token(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Every route except /health rejects a request with no token ───────────────

PROTECTED = [
    (method, route.path)
    for route in main.app.routes
    if isinstance(route, APIRoute) and route.path != "/health"
    for method in route.methods
]


def test_route_list_is_not_empty():
    assert len(PROTECTED) >= 16


@pytest.mark.parametrize("method,path", PROTECTED)
def test_every_route_requires_token(client, method, path):
    url = path.replace("{user_id}", "alice").replace("{topic_id}", "t1") \
              .replace("{course_id}", "c1")
    r = client.request(method, url, json={})
    assert r.status_code == 401, f"{method} {path} answered {r.status_code}"
