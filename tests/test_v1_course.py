# covers tickets 14 and 15: the course tester's /system/test routes, shapes probed on the reference service 2026-10-17

import uuid

import pytest

SOURCE = {"source": "system"}


def new_id(label: str = "s") -> str:
    # makes a session id no other test uses, sessions live as long as the process
    return f"{label}-{uuid.uuid4().hex}"


def setup(api, session_id: str, **extra):
    # opens a session the way the course tester does
    return api.post("/system/test/setup", json={"session_id": session_id, **extra})


def report(api, session_id: str):
    return api.get("/system/test/report", params={"session_id": session_id})


def assert_course_error(r, status: int, message: str):
    # checks the course routes' own error body, never the analyze ErrorBody
    assert r.status_code == status, r.text
    assert r.json() == {"message": message, **SOURCE}


# --- setup -----------------------------------------------------------


def test_setup_returns_201_with_the_session_id(api, v1_env):
    sid = new_id()
    r = setup(api, sid)
    assert r.status_code == 201, r.text
    assert r.json() == {"session_id": sid}


def test_setup_accepts_a_setup_object_and_extra_fields(api, v1_env):
    sid = new_id()
    r = setup(api, sid, setup={"a": 1, "nested": {"b": [1, 2]}}, extra=1)
    assert r.status_code == 201
    assert r.json() == {"session_id": sid}


@pytest.mark.parametrize("make", [lambda: " " * 2, lambda: new_id("x" * 160)[:200], lambda: new_id("has/a slash")])
def test_setup_accepts_any_id_of_1_to_200_characters(api, v1_env, make):
    sid = make()
    r = setup(api, sid)
    assert r.status_code == 201, r.text
    assert report(api, sid).status_code == 200


def test_setting_up_the_same_session_twice_is_409(api, v1_env):
    sid = new_id()
    setup(api, sid)
    assert_course_error(setup(api, sid, setup={"again": True}), 409, f"session {sid} already exists")


@pytest.mark.parametrize(
    "body, message",
    [
        ({}, "session_id is required"),
        ([1], "body has the wrong type"),
        ({"session_id": ""}, "session_id: String should have at least 1 character"),
        ({"session_id": "x" * 201}, "session_id: String should have at most 200 characters"),
        ({"session_id": 7}, "session_id has the wrong type"),
        ({"session_id": None}, "session_id has the wrong type"),
        ({"session_id": "ok", "setup": "str"}, "setup has the wrong type"),
        ({"session_id": "ok", "setup": None}, "setup has the wrong type"),
        ({"session_id": "ok", "setup": [1]}, "setup has the wrong type"),
        ({"session_id": 7, "setup": "s"}, "session_id has the wrong type"),
    ],
)
def test_setup_rejects_malformed_bodies_like_the_reference(api, v1_env, body, message):
    assert_course_error(api.post("/system/test/setup", json=body), 400, message)


def test_setup_rejects_a_body_that_is_not_json(api, v1_env):
    r = api.post("/system/test/setup", content=b"not json", headers={"content-type": "application/json"})
    assert_course_error(r, 400, "body has the wrong type")


def test_setup_rejects_json_sent_as_plain_text(api, v1_env):
    r = api.post("/system/test/setup", content=b'{"session_id": "x"}', headers={"content-type": "text/plain"})
    assert_course_error(r, 400, "body has the wrong type")


def test_setup_without_a_body_names_the_body(api, v1_env):
    # differs on purpose: the reference answers " is required" with an empty field name
    assert_course_error(api.post("/system/test/setup"), 400, "body is required")


# --- report ----------------------------------------------------------


@pytest.mark.parametrize("query", ["", "?session_id="])
def test_report_needs_a_session_id(api, v1_env, query):
    assert_course_error(api.get("/system/test/report" + query), 400, "session_id query parameter is required")


def test_report_for_an_unknown_session_is_404(api, v1_env):
    sid = new_id("unknown")
    assert_course_error(report(api, sid), 404, f"session {sid} is unknown")


def test_report_has_the_reference_shape(api, v1_env):
    sid = new_id()
    setup(api, sid)
    r = report(api, sid)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"session_id", "coverage"}
    assert body["session_id"] == sid
    assert set(body["coverage"]) == {"code"}
    code = body["coverage"]["code"]
    assert set(code) == {"covered", "total", "basis"}
    assert isinstance(code["covered"], int) and isinstance(code["total"], int)
    assert 0 < code["covered"] <= code["total"]
    assert "GitHub_Connector" in code["basis"] and "line coverage" in code["basis"]


def covered(api, sid: str) -> int:
    return report(api, sid).json()["coverage"]["code"]["covered"]


def test_an_analysis_after_setup_raises_the_covered_count(api, make_repo):
    repo = make_repo()
    repo.commit({"README.md": "one\n"})
    head = repo.commit({"README.md": "two\n", "src/app.py": "x = 1\n"})
    sid = new_id()
    setup(api, sid)
    before = covered(api, sid)
    r = api.post("/system/analyze", json={"repository": repo.name, "commit_id": head})
    assert r.status_code == 200, r.text
    assert covered(api, sid) > before


def test_a_session_counts_only_lines_run_since_its_own_setup(api, make_repo):
    repo = make_repo()
    repo.commit({"README.md": "one\n"})
    head = repo.commit({"README.md": "two\n"})
    early = new_id("early")
    setup(api, early)
    assert api.post("/system/analyze", json={"repository": repo.name, "commit_id": head}).status_code == 200
    late = new_id("late")
    setup(api, late)
    assert covered(api, late) < covered(api, early)


def test_the_total_stays_the_same_across_sessions(api, v1_env):
    a, b = new_id("a"), new_id("b")
    setup(api, a)
    setup(api, b)
    assert report(api, a).json()["coverage"]["code"]["total"] == report(api, b).json()["coverage"]["code"]["total"]


def test_only_the_v1_modules_are_counted():
    # leaves out v0's webhook receiver, which the /system app never runs
    from GitHub_Connector import course

    names = {p.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for p in course.Statements(course.PACKAGE_DIR).files()}
    assert {"api.py", "analysis.py", "fetch.py", "course.py"} <= names
    assert not names & {"gitHook.py", "parse.py", "store.py", "models.py", "config.py", "git.py"}


def test_analyses_are_unchanged_while_a_session_is_open(api, make_repo):
    repo = make_repo()
    repo.commit({"README.md": "one\n"})
    head = repo.commit({"README.md": "two\n"})
    setup(api, new_id())
    r = api.post("/system/analyze", json={"repository": repo.name, "commit_id": head})
    assert r.status_code == 200, r.text
    assert [c["path"] for c in r.json()["changes"]] == ["README.md"]
    assert api.get(f"/system/analysis/{r.json()['analysis_id']}").content == r.content


def test_analyze_errors_keep_their_own_shape_while_a_session_is_open(api, v1_env):
    setup(api, new_id())
    r = api.post("/system/analyze", json={"repository": "octo/demo"})
    assert r.json() == {"code": "INVALID_REQUEST", "message": "commit_id is required"}


# --- schema ----------------------------------------------------------


def test_the_setup_request_schema_matches_the_reference(api, v1_env):
    doc = api.get("/system/openapi.json").json()
    assert doc["components"]["schemas"]["TestSetupRequest"] == {
        "properties": {
            "session_id": {"type": "string", "maxLength": 200, "minLength": 1, "title": "Session Id"},
            "setup": {"additionalProperties": True, "type": "object", "title": "Setup"},
        },
        "type": "object",
        "required": ["session_id"],
        "title": "TestSetupRequest",
    }
    assert "201" in doc["paths"]["/system/test/setup"]["post"]["responses"]
    params = doc["paths"]["/system/test/report"]["get"]["parameters"]
    assert [(p["name"], p["in"], p["required"]) for p in params] == [("session_id", "query", False)]
