"""
Test setup. No test may touch the network, Firebase or OpenAI:

- every outbound socket connection except loopback raises;
- firebase_admin.initialize_app raises, and each test gets an in-memory
  FakeFirestore in place of the real client;
- each test gets a FakeOpenAI client that fails on any unexpected call;
- firebase_admin.auth.verify_id_token is replaced by a fake that accepts
  tokens of the form "token-<uid>".
"""
import os
import socket
import sys

import pytest

# Make the project root importable (main, routes, services, models, prompts).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Never use a real key, even if a local .env has one (load_dotenv does not
# override variables that are already set).
os.environ["OPENAI_API_KEY"] = "test-key-not-used"
os.environ.pop("FIREBASE_SERVICE_ACCOUNT", None)


# ── Network guard ────────────────────────────────────────────────────────────

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex


def _address_host(address):
    return address[0] if isinstance(address, tuple) else address


def _guarded_connect(self, address):
    if _address_host(address) not in _LOOPBACK:
        raise RuntimeError(f"Tests must not use the network (tried {address!r})")
    return _real_connect(self, address)


def _guarded_connect_ex(self, address):
    if _address_host(address) not in _LOOPBACK:
        raise RuntimeError(f"Tests must not use the network (tried {address!r})")
    return _real_connect_ex(self, address)


socket.socket.connect = _guarded_connect
socket.socket.connect_ex = _guarded_connect_ex


# ── Firebase: forbid real initialisation ─────────────────────────────────────

import firebase_admin  # noqa: E402
from firebase_admin import auth  # noqa: E402


def _no_real_firebase(*args, **kwargs):
    raise RuntimeError("Tests must not initialise the real Firebase app")


firebase_admin.initialize_app = _no_real_firebase

import services.firebase_service as firebase_service  # noqa: E402
import services.openai_service as openai_service  # noqa: E402
from tests.fakes import FakeFirestore, FakeOpenAI  # noqa: E402


@pytest.fixture(autouse=True)
def db(monkeypatch):
    """A fresh, empty in-memory Firestore for every test."""
    fake = FakeFirestore()
    monkeypatch.setattr(firebase_service, "_db", fake)
    return fake


@pytest.fixture(autouse=True)
def openai(monkeypatch):
    """A fake OpenAI client for every test. Queue replies in .replies."""
    fake = FakeOpenAI()
    monkeypatch.setattr(openai_service, "client", fake)
    return fake


def fake_verify_id_token(token, *args, **kwargs):
    if token == "token-expired":
        raise auth.ExpiredIdTokenError("Token expired", cause=None)
    if token == "token-keys-down":
        raise auth.CertificateFetchError("Could not fetch keys", cause=None)
    if token.startswith("token-") and len(token) > len("token-"):
        return {"uid": token[len("token-"):]}
    raise auth.InvalidIdTokenError("Invalid token")


@pytest.fixture(autouse=True)
def fake_firebase_auth(monkeypatch):
    monkeypatch.setattr(auth, "verify_id_token", fake_verify_id_token)


def bearer(uid):
    return {"Authorization": f"Bearer token-{uid}"}
