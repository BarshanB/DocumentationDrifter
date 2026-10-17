# covers ticket 03: malformed requests and unknown runs are answered without git

import pytest

GOOD = {"repository": "octo/demo", "commit_id": "a" * 40}


@pytest.fixture
def no_remote(monkeypatch, v1_env, tmp_path):
    # points the remote base URL at a folder that doesn't exist, so any git work would 404
    monkeypatch.setenv("DRIFTER_REMOTE_BASE_URL", (tmp_path / "nowhere").as_uri() + "/")
    from GitHub_Connector.settings import get_settings

    get_settings.cache_clear()
    return v1_env


def assert_invalid(r, message=None):
    # checks a 400 INVALID_REQUEST ErrorBody
    assert r.status_code == 400, r.text
    body = r.json()
    assert set(body) == {"code", "message"}
    assert body["code"] == "INVALID_REQUEST"
    if message is not None:
        assert body["message"] == message


def assert_nothing_happened(env):
    # checks no run file was saved and no clone was made
    assert list(env["runs"].iterdir()) == []
    assert list(env["clones"].iterdir()) == []


def test_missing_commit_id(api, no_remote):
    r = api.post("/system/analyze", json={"repository": "octo/demo"})
    assert_invalid(r, "commit_id is required")
    assert_nothing_happened(no_remote)


def test_null_commit_id_counts_as_missing(api, no_remote):
    assert_invalid(api.post("/system/analyze", json={**GOOD, "commit_id": None}), "commit_id is required")


def test_missing_repository(api, no_remote):
    assert_invalid(api.post("/system/analyze", json={"commit_id": "a" * 40}), "repository is required")


@pytest.mark.parametrize(
    "repository",
    ["not-a-repo", "a/b/c", "octo /demo", "octo/de mo", "", "octo.cat/demo", "/demo", "octo/", "octo_cat/demo"],
)
def test_malformed_repository(api, no_remote, repository):
    assert_invalid(api.post("/system/analyze", json={**GOOD, "repository": repository}))
    assert_nothing_happened(no_remote)


@pytest.mark.parametrize("repository", ["octo-cat/demo", "o/d", "Octo9/de.mo_x-1"])
def test_well_formed_repository_reaches_git(api, no_remote, repository):
    # passes validation, then fails at the clone because the remote doesn't exist
    r = api.post("/system/analyze", json={**GOOD, "repository": repository})
    assert r.status_code == 404
    assert r.json()["code"] == "REPOSITORY_NOT_FOUND"


@pytest.mark.parametrize("sha", ["abc123", "a" * 41, "g" * 40, "abc 1234", ""])
@pytest.mark.parametrize("field", ["commit_id", "base_commit"])
def test_malformed_sha(api, no_remote, field, sha):
    assert_invalid(api.post("/system/analyze", json={**GOOD, field: sha}))
    assert_nothing_happened(no_remote)


@pytest.mark.parametrize("extra", [{}, {"base_commit": None}])
def test_absent_or_null_base_is_accepted(api, no_remote, extra):
    r = api.post("/system/analyze", json={**GOOD, **extra})
    assert r.json()["code"] == "REPOSITORY_NOT_FOUND"


@pytest.mark.parametrize(
    "body",
    [
        {"repository": 7, "commit_id": "a" * 40},
        {"repository": "octo/demo", "commit_id": ["a" * 40]},
        {"repository": "octo/demo", "commit_id": "a" * 40, "base_commit": 1234567},
        ["octo/demo", "a" * 40],
        "octo/demo",
    ],
)
def test_wrong_json_types(api, no_remote, body):
    assert_invalid(api.post("/system/analyze", json=body))
    assert_nothing_happened(no_remote)


def test_body_that_is_not_json(api, no_remote):
    r = api.post("/system/analyze", content=b"{not json", headers={"Content-Type": "application/json"})
    assert_invalid(r)


def test_missing_body(api, no_remote):
    assert_invalid(api.post("/system/analyze"))


def test_validation_also_guards_direct_calls(no_remote):
    from GitHub_Connector.analysis import analyze
    from GitHub_Connector.schemas import AnalysisError, AnalysisRequest, ErrorCode

    with pytest.raises(AnalysisError) as exc:
        analyze(AnalysisRequest(repository="not-a-repo", commit_id="a" * 40))
    assert exc.value.code is ErrorCode.INVALID_REQUEST


# --- unknown runs ---------------------------------------------------

def unknown_run(analysis_id):
    # spells the reference service's body for a run that doesn't exist
    return {"code": "ANALYSIS_NOT_FOUND", "message": f"analysis {analysis_id} does not exist"}


def test_unknown_but_well_formed_id_is_404(api, v1_env):
    r = api.get("/system/analysis/an-" + "0" * 32)
    assert r.status_code == 404
    assert r.json() == unknown_run("an-" + "0" * 32)


@pytest.mark.parametrize(
    "analysis_id",
    ["nope", "an-123", "an-" + "G" * 32, "AN-" + "0" * 32, "an-" + "0" * 32 + ".json"],
)
def test_malformed_id_gives_the_same_404_and_reads_nothing_outside(api, v1_env, analysis_id):
    secret = v1_env["runs"].parent / "secret.json"
    secret.write_text('{"leak": true}')
    r = api.get(f"/system/analysis/{analysis_id}")
    assert r.status_code == 404
    assert r.json() == unknown_run(analysis_id)


@pytest.mark.parametrize("path", ["..%2F..%2Fsecret", "../secret"])
def test_path_traversal_reads_nothing_outside(api, v1_env, path):
    secret = v1_env["runs"].parent / "secret.json"
    secret.write_text('{"leak": true}')
    r = api.get(f"/system/analysis/{path}")
    assert r.status_code == 404
    assert "leak" not in r.text


@pytest.mark.parametrize(
    "body, message",
    [
        ({**GOOD, "repository": "not-a-repo"}, "repository must use the format owner/name"),
        ({**GOOD, "commit_id": "xyz"}, "commit_id must be a 7-40 character hexadecimal commit SHA"),
        ({**GOOD, "base_commit": "xyz"}, "base_commit must be a 7-40 character hexadecimal commit SHA"),
        ({**GOOD, "repository": 7}, "repository has the wrong type"),
        ({**GOOD, "commit_id": ["a" * 40]}, "commit_id has the wrong type"),
        ({**GOOD, "base_commit": 1234567}, "base_commit has the wrong type"),
    ],
)
def test_messages_use_the_reference_wording(api, no_remote, body, message):
    assert_invalid(api.post("/system/analyze", json=body), message)


@pytest.mark.parametrize(
    "body",
    [
        {"repository": "octo/demo\n", "commit_id": "a" * 40},
        {"repository": "octo/demo", "commit_id": "abcdef1\n"},
        {"repository": "octo/demo", "commit_id": "a" * 40, "base_commit": "abcdef1\n"},
    ],
)
def test_trailing_newline_is_malformed(api, no_remote, body):
    assert_invalid(api.post("/system/analyze", json=body))
    assert_nothing_happened(no_remote)
