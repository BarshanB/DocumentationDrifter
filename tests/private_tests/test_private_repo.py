# covers the private-repo checks of tickets 09 and 12, run only while our own repo is private

import os

import httpx
import pytest

import reference


@pytest.mark.network
def test_private_repository_is_not_found(api, github_env, recorded_helper, private_project, anonymous_host):
    r = api.post("/system/analyze", json={"repository": private_project, "commit_id": "a" * 40})
    assert r.status_code == 404
    assert r.json()["code"] == "REPOSITORY_NOT_FOUND"
    assert not recorded_helper.exists(), "a credential helper was asked for credentials"


@pytest.mark.network
def test_private_repository_conformance(target, github_env, private_project, live_reference, request):
    if not os.environ.get("DRIFTER_TARGET_URL"):
        request.getfixturevalue("anonymous_host")
    body = {"repository": private_project, "commit_id": "a" * 40}
    ours = target.post("/system/analyze", json=body)
    theirs = httpx.post(f"{live_reference}/analyze", json=body, timeout=180)
    assert ours.status_code == theirs.status_code
    assert reference.differences(reference.normalise(ours.json()), reference.normalise(theirs.json())) == []
