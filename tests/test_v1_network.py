# covers ticket 09: GitHub, anonymous not-found, schema and conformance, repo-visibility checks live in private_tests and public_tests

import json
import os
import time
from pathlib import Path

import httpx
import pytest

import reference

MISSING_REPO = "octocat/this-repo-cannot-exist-7f3a9c"
HELLO = {"repository": "octocat/Hello-World", "commit_id": "7fd1a60"}


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


@pytest.mark.network
def test_our_schema_matches_the_live_reference(live_reference):
    theirs = httpx.get(f"{live_reference}/openapi.json", timeout=60).json()
    found = reference.schema_differences(our_openapi(), theirs)
    assert found == [], " | ".join(found)


# --- conformance -----------------------------------------------------


def theirs(method, path, body=None):
    # sends one request to the reference service
    r = httpx.request(method, reference.REFERENCE_URL + path, json=body, timeout=180)
    return r


def analyze(body):
    # spells a POST /analyze case
    return ("POST", "/analyze", body)


HELLO_FULL = "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"

# lists the conformance requests, real repos then every error case (ticket 12)
CASES = {
    "hello-world": analyze(HELLO),
    "hello-world-explicit-parent": analyze({**HELLO, "base_commit": "553c2077f0edc3d5dc5d17262f6aa498e69d6f8e"}),
    "hello-world-older-base": analyze({**HELLO, "base_commit": "7629413"}),
    "psf-requests": analyze({"repository": "psf/requests", "commit_id": "d568f47"}),
    "missing-commit-id": analyze({"repository": "octocat/Hello-World"}),
    "malformed-repository": analyze({"repository": "not-a-repo", "commit_id": HELLO_FULL}),
    "malformed-sha": analyze({"repository": "octocat/Hello-World", "commit_id": "xyz"}),
    "wrong-json-types": analyze({"repository": 7, "commit_id": HELLO_FULL}),
    "missing-repository": analyze({"repository": MISSING_REPO, "commit_id": "a" * 40}),
    "unknown-commit": analyze({"repository": "octocat/Hello-World", "commit_id": "1" * 40}),
    "unknown-base-commit": analyze({**HELLO, "base_commit": "2" * 40}),
    "unfetchable-short-sha": analyze({"repository": "octocat/Hello-World", "commit_id": "1234567"}),
    "unknown-analysis-id": ("GET", "/analysis/an-" + "0" * 32, None),
    "malformed-analysis-id": ("GET", "/analysis/not-an-id", None),
    "health": ("GET", "/health", None),
}


def label_cases():
    # adds every test-repo label once the public test repo exists
    repo = os.environ.get("DRIFTER_TEST_REPO", "")
    if not repo:
        return {}
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import testrepo

    return {f"label-{name}": ("POST", "/analyze", None) for name in testrepo.LABELS}


@pytest.mark.network
@pytest.mark.parametrize("case", sorted({**CASES, **label_cases()}))
def test_conformance(case, target, github_env, live_reference, request):
    if case.startswith("label-"):
        built = request.getfixturevalue("built")
        entry = built[2]["labels"][case[len("label-"):]]
        method, path, body = "POST", "/analyze", {"repository": os.environ["DRIFTER_TEST_REPO"], **entry["request"]}
    else:
        method, path, body = CASES[case]
    ours = target.request(method, "/system" + path, json=body)
    their = theirs(method, path, body)
    assert ours.status_code == their.status_code, f"{case}: status ours {ours.status_code}, theirs {their.status_code}"
    found = reference.differences(reference.normalise(ours.json()), reference.normalise(their.json()))
    assert found == [], f"{case}: " + " | ".join(found)
    if method == "POST" and ours.status_code == 200:
        # checks each service serves back its own POST bytes
        assert target.get(f"/system/analysis/{ours.json()['analysis_id']}").content == ours.content
        assert theirs("GET", f"/analysis/{their.json()['analysis_id']}").content == their.content


def test_differences_name_the_field_and_allow_only_known_ones():
    ours = {"config_version": "abc", "changes": [{"path": "d.md", "category": "DOCUMENTATION", "change_type": "ADDED"}]}
    same = {"config_version": "mapping-v1", "changes": [{"path": "d.md", "category": "OTHER", "change_type": "ADDED"}]}
    assert reference.differences(ours, same) == []
    other = {"config_version": "x", "changes": [{"path": "d.md", "category": "OTHER", "change_type": "MODIFIED"}]}
    assert reference.differences(ours, other) == ["body.changes[0].change_type: ours 'ADDED', theirs 'MODIFIED'"]
    swapped = {"config_version": "x", "changes": [{"path": "d.md", "category": "IMPLEMENTATION", "change_type": "ADDED"}]}
    assert reference.differences(ours, swapped) != []
