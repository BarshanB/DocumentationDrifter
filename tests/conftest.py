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
# puts tests/ itself on the path, so tests in subfolders can import repos and reference
sys.path.insert(0, str(Path(__file__).resolve().parent))

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


# --- project repo visibility and anonymity ---------------------------

# names our own repo, public since 2026-10-17 and maybe private again after deployment
PROJECT_REPO = "MuhammadSban/DocumentationDrifter"

_visibility: str | None = None


def project_visibility() -> str:
    # asks GitHub once whether our repo is "public" or "private", "unknown" when it can't tell
    global _visibility
    if _visibility is None:
        import httpx

        try:
            r = httpx.get(f"https://api.github.com/repos/{PROJECT_REPO}", timeout=15)
            if r.status_code == 404:
                _visibility = "private"
            elif r.status_code == 200:
                _visibility = "private" if r.json().get("private") else "public"
            else:
                _visibility = "unknown"
        except httpx.HTTPError:
            _visibility = "unknown"
    return _visibility


@pytest.fixture
def private_project():
    # skips unless our repo is private, see tests/private_tests/README.md
    seen = project_visibility()
    if seen != "private":
        pytest.skip(f"{PROJECT_REPO} is {seen}, so the private-repo checks don't apply")
    return PROJECT_REPO


@pytest.fixture
def public_project():
    # skips unless our repo is public, see tests/public_tests/README.md
    seen = project_visibility()
    if seen != "public":
        pytest.skip(f"{PROJECT_REPO} is {seen}, so the public-repo checks don't apply")
    return PROJECT_REPO


@pytest.fixture
def recorded_helper(monkeypatch, tmp_path):
    # installs a credential helper that records any use, through git's environment config
    log = tmp_path / "helper-used.log"
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "credential.helper")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", f"!f() {{ echo used >> '{log.as_posix()}'; }}; f")
    return log


def host_injects_credentials(private_repo: str) -> bool:
    # tells whether a bare anonymous git can read a private repo, which means a proxy adds credentials
    import os
    import subprocess

    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "HOME": "/nonexistent"}
    proc = subprocess.run(
        ["git", "-c", "credential.helper=", "ls-remote", f"https://github.com/{private_repo}", "HEAD"],
        env=env, capture_output=True, timeout=30,
    )
    return proc.returncode == 0


@pytest.fixture
def anonymous_host(private_project):
    # skips where credentials are injected outside git, unless CI demands an anonymous host
    import os

    if host_injects_credentials(private_project):
        message = (
            "this host injects GitHub credentials outside git's control, so a private repo "
            "is readable here; the private-repo check runs in CI or against the deployed service"
        )
        if os.environ.get("DRIFTER_REQUIRE_ANONYMOUS") == "1":
            pytest.fail(message)
        pytest.skip(message)


@pytest.fixture(scope="session")
def reference_awake():
    # checks the reference service once per session, warming it with retries only where CI needs it
    import os

    import reference

    if os.environ.get("DRIFTER_REQUIRE_REFERENCE") == "1":
        return reference.warm()
    return reference.reachable()


@pytest.fixture
def live_reference(reference_awake):
    # hands out the reference URL, skipping offline unless CI demands it
    import os

    import reference

    if reference_awake:
        return reference.REFERENCE_URL
    message = f"reference service {reference.REFERENCE_URL} did not answer"
    if os.environ.get("DRIFTER_REQUIRE_REFERENCE") == "1":
        pytest.fail(message)
    pytest.skip(message)


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


@pytest.fixture
def target(api):
    # talks to the service under test: the in-process app, or a deployed one at DRIFTER_TARGET_URL
    import os

    url = os.environ.get("DRIFTER_TARGET_URL", "").rstrip("/")
    if not url:
        yield api
        return
    import httpx

    root = url[: -len("/system")] if url.endswith("/system") else url
    with httpx.Client(base_url=root, timeout=180) as client:
        yield client


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


# --- test repo -------------------------------------------------------

LOCAL_TESTREPO = "fixtures/drifter-testrepo"


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    # builds the test repo once per session and reads the manifest back out of it, shared by ticket 11 and 12 tests
    import json
    import subprocess
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import testrepo

    root = tmp_path_factory.mktemp("testrepo")
    bare = root / f"{LOCAL_TESTREPO}.git"
    testrepo.build(bare)
    raw = subprocess.run(["git", "show", "main:manifest.json"], cwd=bare, capture_output=True, check=True).stdout
    return root, bare, json.loads(raw)
