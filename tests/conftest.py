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


# --- network tests ---------------------------------------------------


def pytest_configure(config):
    # registers the one marker every network test shares
    config.addinivalue_line("markers", "network: needs GitHub; skipped offline or with DRIFTER_OFFLINE=1")


_github: bool | None = None


def _github_reachable() -> bool:
    # checks once per session whether git can reach GitHub anonymously
    global _github
    if _github is None:
        import os
        import subprocess

        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        try:
            proc = subprocess.run(
                ["git", "-c", "credential.helper=", "ls-remote", "https://github.com/octocat/Hello-World", "HEAD"],
                env=env, capture_output=True, timeout=15,
            )
            _github = proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            _github = False
    return _github


def pytest_collection_modifyitems(config, items):
    # skips network tests when told to stay offline or when GitHub can't be reached
    import os

    network = [i for i in items if i.get_closest_marker("network")]
    if not network:
        return
    if os.environ.get("DRIFTER_OFFLINE") == "1":
        reason = "DRIFTER_OFFLINE=1"
    elif not _github_reachable():
        reason = "GitHub is not reachable"
    else:
        return
    for item in network:
        item.add_marker(pytest.mark.skip(reason=reason))


# --- v1 fixtures -----------------------------------------------------


@pytest.fixture
def v1_env(monkeypatch, tmp_path):
    # repoints v1 settings at folders under tmp_path / "repo", away from v0's test.db
    root = tmp_path / "repo"
    paths = {
        "remotes": root / "remotes",
        "work": root / "work",
        "runs": root / "runs",
        "clones": root / "clones",
    }
    for p in paths.values():
        p.mkdir(parents=True)
    monkeypatch.setenv("DRIFTER_REMOTE_BASE_URL", paths["remotes"].as_uri() + "/")
    monkeypatch.setenv("DRIFTER_RUNS_DIR", str(paths["runs"]))
    monkeypatch.setenv("DRIFTER_CLONE_DIR", str(paths["clones"]))

    from GitHub_Connector.settings import get_settings

    get_settings.cache_clear()
    yield paths
    get_settings.cache_clear()


@pytest.fixture
def make_repo(v1_env):
    # builds a fixture repo reachable as owner/name through the remote base URL
    from repos import FixtureRepo

    def _make(name: str = "octo/demo") -> "FixtureRepo":
        return FixtureRepo(v1_env["remotes"], v1_env["work"], name)

    return _make


@pytest.fixture
def github_env(monkeypatch, v1_env):
    # keeps runs and clones under tmp_path but uses the default remote base URL (GitHub)
    monkeypatch.delenv("DRIFTER_REMOTE_BASE_URL")
    from GitHub_Connector.settings import get_settings

    get_settings.cache_clear()
    return v1_env


@pytest.fixture
def api(v1_env):
    # builds a test client against the v1 app, named apart from v0's client
    from fastapi.testclient import TestClient

    from GitHub_Connector.api import app

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
