# puts Source on the path and gives each test a clean store

import hashlib
import hmac
import json
import sys
from pathlib import Path

import pytest

# matches the layout the deleted Alembic env.py assumed, GitHub_Connector lives under Source
SOURCE = Path(__file__).resolve().parents[1] / "Source"
sys.path.insert(0, str(SOURCE))

SECRET = "test-secret"


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    # repoints settings and the store at a throwaway SQLite file per test

    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")

    from GitHub_Connector.config import get_settings

    get_settings.cache_clear()

    from GitHub_Connector import store

    store.init_db(f"sqlite:///{tmp_path/'test.db'}")
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    # builds a test client against the real app
    from fastapi.testclient import TestClient

    from GitHub_Connector.gitHook import app

    return TestClient(app)


def sign(body: bytes, secret: str = SECRET) -> str:
    # signs a body the way GitHub does
    return "sha256=" + hmac.new(
        secret.encode(), msg=body, digestmod=hashlib.sha256
    ).hexdigest()


def push_body(**overrides) -> bytes:
    # builds a push payload, shaped like a real delivery
    payload = {
        "ref": "refs/heads/main",
        "before": "a" * 40,
        "after": "b" * 40,
        "created": False,
        "deleted": False,
        "forced": False,
        "repository": {"full_name": "octocat/hello-world"},
        "head_commit": {"id": "b" * 40},
    }
    payload.update(overrides)
    return json.dumps(payload).encode()


def post(client, body: bytes, delivery="d-1", event="push", signature=None):
    # posts a delivery with GitHub's headers
    headers = {
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery,
        "X-Hub-Signature-256": sign(body) if signature is None else signature,
        "Content-Type": "application/json",
    }
    return client.post("/hooks/github", content=body, headers=headers)
