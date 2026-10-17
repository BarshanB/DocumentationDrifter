# covers ticket 01: one commit analysed, saved and served back, and a missing repository refused

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SHA40 = re.compile(r"^[0-9a-f]{40}$")
FIELDS = [
    "analysis_id", "repository", "head_commit", "base_commit", "config_version",
    "tool_version", "status", "error", "issues", "changes", "skipped", "created_at",
]


def two_commits(make_repo):
    # builds a repo whose head modifies one file, returns (repo, base, head)
    repo = make_repo()
    base = repo.commit({"Makefile": "all:\n", "LICENSE": "MIT\n"}, "first")
    head = repo.commit({"Makefile": "all:\n\techo hi\n"}, "second")
    return repo, base, head


def analyse(api, head, repo="octo/demo", **extra):
    # posts one analysis request and returns the response
    return api.post("/system/analyze", json={"repository": repo, "commit_id": head, **extra})


def strip(body):
    # drops the fields that legitimately differ between identical runs
    return {k: v for k, v in body.items() if k not in ("analysis_id", "created_at")}


def test_result_has_all_twelve_fields(api, make_repo):
    _, base, head = two_commits(make_repo)
    r = analyse(api, head)
    assert r.status_code == 200
    body = r.json()
    assert list(body) == FIELDS
    assert re.fullmatch(r"an-[0-9a-f]{32}", body["analysis_id"])
    assert body["repository"] == "octo/demo"
    assert body["head_commit"] == head and SHA40.match(head)
    assert body["base_commit"] == base
    assert isinstance(body["config_version"], str) and body["config_version"]
    assert isinstance(body["tool_version"], str) and body["tool_version"]
    assert body["status"] == "SUCCESS"
    assert body["error"] is None
    assert body["issues"] == [] and body["skipped"] == []
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", body["created_at"])


def test_one_modified_file_gives_one_modified_change(api, make_repo):
    _, _, head = two_commits(make_repo)
    assert analyse(api, head).json()["changes"] == [
        {"path": "Makefile", "old_path": None, "change_type": "MODIFIED", "category": "OTHER"}
    ]


def test_added_and_deleted_files_are_listed_sorted(api, make_repo):
    repo = make_repo()
    repo.commit({"zeta": "z\n", "keep": "k\n"})
    head = repo.commit({"zeta": None, "alpha": "a\n"})
    changes = analyse(api, head).json()["changes"]
    assert [(c["path"], c["change_type"]) for c in changes] == [("alpha", "ADDED"), ("zeta", "DELETED")]


def test_given_full_base_commit_is_used(api, make_repo):
    repo = make_repo()
    first = repo.commit({"a": "1\n"})
    repo.commit({"b": "1\n"})
    head = repo.commit({"c": "1\n"})
    body = analyse(api, head, base_commit=first).json()
    assert body["base_commit"] == first
    assert [c["path"] for c in body["changes"]] == ["b", "c"]


def test_get_returns_the_post_bytes(api, make_repo, v1_env):
    _, _, head = two_commits(make_repo)
    posted = analyse(api, head)
    analysis_id = posted.json()["analysis_id"]
    got = api.get(f"/system/analysis/{analysis_id}")
    assert got.status_code == 200
    assert got.content == posted.content
    assert [p.name for p in v1_env["runs"].iterdir()] == [f"{analysis_id}.json"]


def test_run_store_folder_is_gitignored():
    lines = (REPO_ROOT / ".gitignore").read_text().splitlines()
    assert "runs/" in lines


def test_three_identical_requests_differ_only_in_id_and_time(api, make_repo):
    _, _, head = two_commits(make_repo)
    bodies = [analyse(api, head).json() for _ in range(3)]
    assert strip(bodies[0]) == strip(bodies[1]) == strip(bodies[2])
    assert len({b["analysis_id"] for b in bodies}) == 3


def test_missing_repository_is_refused_and_nothing_saved(api, v1_env):
    r = analyse(api, "a" * 40, repo="octo/nothing-here")
    assert r.status_code == 404
    assert r.json() == {
        "code": "REPOSITORY_NOT_FOUND",
        "message": "Repository octo/nothing-here not found or is not public",
    }
    assert list(v1_env["runs"].iterdir()) == []


def test_every_contract_code_has_a_status():
    from GitHub_Connector.api import STATUS_FOR
    from GitHub_Connector.schemas import ErrorCode

    assert set(STATUS_FOR) == set(ErrorCode)


def test_no_clone_is_left_after_success_or_failure(api, make_repo, v1_env):
    _, _, head = two_commits(make_repo)
    assert analyse(api, head).status_code == 200
    assert list(v1_env["clones"].iterdir()) == []
    assert analyse(api, head, repo="octo/missing").status_code == 404
    assert list(v1_env["clones"].iterdir()) == []


def test_repo_is_untouched_and_its_code_never_runs(api, make_repo, tmp_path):
    marker = tmp_path / "marker"
    payload = f"open({str(marker)!r}, 'w').write('ran')\n"
    repo = make_repo()
    repo.commit({"setup.py": payload, "conftest.py": payload, "pkg/__init__.py": payload})
    head = repo.commit({"Makefile": "x\n"})
    before = repo.digest()
    assert analyse(api, head).status_code == 200
    assert repo.digest() == before
    assert not marker.exists()


def test_health_answers_without_git(api, monkeypatch):
    import subprocess as sp

    def _no_git(*a, **k):
        raise AssertionError("health ran a subprocess")

    monkeypatch.setattr(sp, "run", _no_git)
    r = api.get("/system/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "storage": "local"}


def test_openapi_lives_under_system_and_has_no_webhook_route(api):
    doc = api.get("/system/openapi.json").json()
    assert all(p.startswith("/system/") for p in doc["paths"])
    assert not any("hooks" in p for p in doc["paths"])


def test_importing_the_v1_app_never_imports_v0():
    probe = (
        "import sys; sys.path.insert(0, %r); import GitHub_Connector.api; "
        "print('GitHub_Connector.gitHook' in sys.modules)"
    ) % str(REPO_ROOT / "Source")
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


def test_analyze_works_without_http(api, make_repo):
    from GitHub_Connector.analysis import analyze
    from GitHub_Connector.schemas import AnalysisRequest

    _, _, head = two_commits(make_repo)
    direct = analyze(AnalysisRequest(repository="octo/demo", commit_id=head))
    over_http = analyse(api, head).json()
    assert strip(json.loads(direct.model_dump_json())) == strip(over_http)
