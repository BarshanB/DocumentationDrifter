# covers ticket 09: real GitHub, anonymous not-found, the schema check and the conformance harness

import json
import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

import reference

PRIVATE_REPO = "MuhammadSban/DocumentationDrifter"
MISSING_REPO = "octocat/this-repo-cannot-exist-7f3a9c"
HELLO = {"repository": "octocat/Hello-World", "commit_id": "7fd1a60"}


@pytest.fixture
def github_env(monkeypatch, v1_env):
    # keeps runs and clones under tmp_path but uses the default remote base URL (GitHub)
    monkeypatch.delenv("DRIFTER_REMOTE_BASE_URL")
    from GitHub_Connector.settings import get_settings

    get_settings.cache_clear()
    return v1_env


@pytest.fixture
def recorded_helper(monkeypatch, tmp_path):
    # installs a credential helper that records any use, through git's environment config
    log = tmp_path / "helper-used.log"
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "credential.helper")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", f"!f() {{ echo used >> '{log.as_posix()}'; }}; f")
    return log


def host_injects_credentials() -> bool:
    # tells whether a bare anonymous git can read the private repo, which means a proxy adds credentials
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "HOME": "/nonexistent"}
    proc = subprocess.run(
        ["git", "-c", "credential.helper=", "ls-remote", f"https://github.com/{PRIVATE_REPO}", "HEAD"],
        env=env, capture_output=True, timeout=30,
    )
    return proc.returncode == 0


@pytest.fixture
def anonymous_host():
    # skips where credentials are injected outside git, unless CI demands an anonymous host
    if host_injects_credentials():
        message = (
            "this host injects GitHub credentials outside git's control, so a private repo "
            "is readable here; the private-repo check runs in CI or against the deployed service"
        )
        if os.environ.get("DRIFTER_REQUIRE_ANONYMOUS") == "1":
            pytest.fail(message)
        pytest.skip(message)


@pytest.mark.network
def test_hello_world_through_github(api, github_env):
    r = api.post("/system/analyze", json=HELLO)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["head_commit"] == "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
    assert body["base_commit"].startswith("553c2077")
    assert [(c["path"], c["change_type"]) for c in body["changes"]] == [("README", "MODIFIED")]
    assert api.get(f"/system/analysis/{body['analysis_id']}").content == r.content


@pytest.mark.network
def test_missing_repository_fails_fast_without_credentials(api, github_env, recorded_helper):
    start = time.monotonic()
    r = api.post("/system/analyze", json={"repository": MISSING_REPO, "commit_id": "a" * 40})
    assert time.monotonic() - start < 15
    assert r.status_code == 404
    assert r.json()["code"] == "REPOSITORY_NOT_FOUND"
    assert not recorded_helper.exists(), "a credential helper was asked for credentials"


@pytest.mark.network
def test_private_repository_is_not_found(api, github_env, recorded_helper, anonymous_host):
    r = api.post("/system/analyze", json={"repository": PRIVATE_REPO, "commit_id": "a" * 40})
    assert r.status_code == 404
    assert r.json()["code"] == "REPOSITORY_NOT_FOUND"
    assert not recorded_helper.exists()


# --- schema ----------------------------------------------------------


def our_openapi():
    # reads our published OpenAPI document from the in-process app
    from fastapi.testclient import TestClient

    from GitHub_Connector.api import app

    return TestClient(app).get("/system/openapi.json").json()


def test_our_schema_matches_the_captured_reference():
    if not reference.CAPTURED_OPENAPI.exists():
        pytest.skip("no captured reference document yet: run `python tests/reference.py capture`")
    theirs = json.loads(reference.CAPTURED_OPENAPI.read_text())
    assert reference.schema_differences(our_openapi(), theirs) == []


def test_schema_comparison_catches_a_real_difference():
    # guards the comparison itself: an extra field or enum value must show up
    ours = our_openapi()
    theirs = json.loads(json.dumps(ours))
    assert reference.schema_differences(ours, theirs) == []
    theirs["components"]["schemas"]["Change"]["properties"]["extra"] = {"type": "string"}
    theirs["components"]["schemas"]["ErrorCode"]["enum"].append("LLM_UNAVAILABLE")
    found = reference.schema_differences(ours, theirs)
    assert any("Change.extra" in f for f in found)
    assert any("ErrorBody.code" in f for f in found)


@pytest.fixture(scope="session")
def reference_awake():
    # checks the reference service once per session, warming it with retries only where CI needs it
    if os.environ.get("DRIFTER_REQUIRE_REFERENCE") == "1":
        return reference.warm()
    return reference.reachable()


@pytest.fixture
def live_reference(reference_awake):
    # hands out the reference URL, skipping offline unless CI demands it
    if reference_awake:
        return reference.REFERENCE_URL
    message = f"reference service {reference.REFERENCE_URL} did not answer"
    if os.environ.get("DRIFTER_REQUIRE_REFERENCE") == "1":
        pytest.fail(message)
    pytest.skip(message)


@pytest.mark.network
def test_our_schema_matches_the_live_reference(live_reference):
    theirs = httpx.get(f"{live_reference}/openapi.json", timeout=60).json()
    assert reference.schema_differences(our_openapi(), theirs) == []


# --- conformance -----------------------------------------------------


class Ours:
    # sends requests to the in-process app, or to a deployed URL from DRIFTER_TARGET_URL

    def __init__(self, api):
        self.url = os.environ.get("DRIFTER_TARGET_URL", "").rstrip("/")
        self.api = api

    def request(self, method, path, body=None):
        if self.url:
            r = httpx.request(method, self.url + path, json=body, timeout=180)
        else:
            r = self.api.request(method, "/system" + path, json=body)
        return r.status_code, r.json()


def theirs(method, path, body=None):
    # sends one request to the reference service
    r = httpx.request(method, reference.REFERENCE_URL + path, json=body, timeout=180)
    return r.status_code, r.json()


CASES = {
    "hello-world": ("POST", "/analyze", HELLO),
    "missing-repository": ("POST", "/analyze", {"repository": MISSING_REPO, "commit_id": "a" * 40}),
    "private-repository": ("POST", "/analyze", {"repository": PRIVATE_REPO, "commit_id": "a" * 40}),
    "health": ("GET", "/health", None),
}


@pytest.mark.network
@pytest.mark.parametrize("case", sorted(CASES))
def test_conformance(case, api, github_env, live_reference, request):
    if case == "private-repository" and not os.environ.get("DRIFTER_TARGET_URL"):
        request.getfixturevalue("anonymous_host")
    method, path, body = CASES[case]
    our_status, our_body = Ours(api).request(method, path, body)
    their_status, their_body = theirs(method, path, body)
    assert our_status == their_status, f"{case}: status ours {our_status}, theirs {their_status}"
    found = reference.differences(reference.normalise(our_body), reference.normalise(their_body))
    assert found == [], f"{case}:\n" + "\n".join(found)


def test_differences_name_the_field_and_allow_only_known_ones():
    ours = {"config_version": "abc", "changes": [{"path": "d.md", "category": "DOCUMENTATION", "change_type": "ADDED"}]}
    same = {"config_version": "mapping-v1", "changes": [{"path": "d.md", "category": "OTHER", "change_type": "ADDED"}]}
    assert reference.differences(ours, same) == []
    other = {"config_version": "x", "changes": [{"path": "d.md", "category": "OTHER", "change_type": "MODIFIED"}]}
    assert reference.differences(ours, other) == ["body.changes[0].change_type: ours 'ADDED', theirs 'MODIFIED'"]
    swapped = {"config_version": "x", "changes": [{"path": "d.md", "category": "IMPLEMENTATION", "change_type": "ADDED"}]}
    assert reference.differences(ours, swapped) != []
