# covers tickets 06 and 16: unreadable files are skipped with a reason code and still reported as changes

import json
from pathlib import Path

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 8
MB = 1024 * 1024
RULES = Path(__file__).resolve().parents[1] / "Source" / "GitHub_Connector" / "path_rules.json"


def analyse(api, head, **extra):
    # posts one analysis request and returns the parsed body
    r = api.post("/system/analyze", json={"repository": "octo/demo", "commit_id": head, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def paths(items):
    # lists the path of each entry
    return [i["path"] for i in items]


def reason_for(body, path):
    # finds the skip reason recorded for one path
    return next(s["reason"] for s in body["skipped"] if s["path"] == path)


def test_skipped_file_is_still_reported_as_a_change(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    body = analyse(api, repo.commit({"logo.bin": b"\0\1\2", "notes.md": "hi\n"}))
    assert paths(body["skipped"]) == ["logo.bin"]
    assert [(c["path"], c["change_type"], c["category"]) for c in body["changes"]] == [
        ("logo.bin", "ADDED", "OTHER"),
        ("notes.md", "ADDED", "DOCUMENTATION"),
    ]


def test_nul_byte_in_the_first_8kb_marks_binary(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    body = analyse(api, repo.commit({"data.txt": b"text" * 100 + b"\0" + b"more\n"}))
    assert reason_for(body, "data.txt") == "BINARY_FILE"


def test_size_cap_is_exact(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    head = repo.commit({"big.txt": b"a" * MB + b"\n", "fits.txt": b"a" * (MB - 1) + b"\n"})
    body = analyse(api, head)
    assert reason_for(body, "big.txt") == "FILE_TOO_LARGE"
    # fits.txt is under the file cap but a doc far past the drift check's budget (v1.2)
    assert reason_for(body, "fits.txt") == "OVER_DOC_BUDGET"
    assert paths(body["changes"]) == ["big.txt", "fits.txt"]


def test_non_utf8_file_is_skipped(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    body = analyse(api, repo.commit({"latin1.txt": "café crème\n".encode("latin-1")}))
    assert reason_for(body, "latin1.txt") == "NOT_UTF8"
    assert paths(body["changes"]) == ["latin1.txt"]


def test_deleted_binary_is_still_skipped(api, make_repo):
    repo = make_repo()
    repo.commit({"logo.png": PNG, "keep": "k\n"})
    body = analyse(api, repo.commit({"logo.png": None}))
    assert paths(body["skipped"]) == ["logo.png"]
    assert [(c["path"], c["change_type"]) for c in body["changes"]] == [("logo.png", "DELETED")]


def test_unchanged_files_are_not_read_unless_the_doc_budget_reports_them(api, make_repo):
    repo = make_repo()
    repo.commit({"logo.png": PNG, "big.txt": b"a" * (2 * MB)})
    body = analyse(api, repo.commit({"readme": "changed\n"}))
    # the image is nobody's business, the unchanged doc is named because the check never saw it (v1.2)
    assert body["skipped"] == [{"path": "big.txt", "reason": "OVER_DOC_BUDGET"}]
    assert paths(body["changes"]) == ["readme"]


def test_skipped_is_sorted_by_path(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    body = analyse(api, repo.commit({"z.png": PNG, "a.png": PNG, "m.bin": b"\0\1\2"}))
    assert paths(body["skipped"]) == ["a.png", "m.bin", "z.png"]


def test_hidden_binary_is_in_neither_list(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    body = analyse(api, repo.commit({".assets/logo.png": PNG}))
    assert body["skipped"] == [] and body["changes"] == []


def test_renamed_binary_is_skipped_under_its_new_path(api, make_repo):
    repo = make_repo()
    repo.commit({"old.png": PNG})
    body = analyse(api, repo.commit({"old.png": None, "new.png": PNG}))
    assert paths(body["skipped"]) == ["new.png"]
    assert [(c["path"], c["change_type"], c["old_path"]) for c in body["changes"]] == [("new.png", "RENAMED", "old.png")]


def test_unsupported_file_type_is_skipped_before_any_content_check(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    body = analyse(api, repo.commit({"logo.png": PNG, "Pipfile.lock": "{}\n"}))
    assert body["skipped"] == [
        {"path": "Pipfile.lock", "reason": "UNSUPPORTED_FILE_TYPE"},
        {"path": "logo.png", "reason": "UNSUPPORTED_FILE_TYPE"},
    ]
    assert [(c["path"], c["category"]) for c in body["changes"]] == [("Pipfile.lock", "OTHER"), ("logo.png", "OTHER")]


def test_large_file_of_an_unsupported_type_gets_the_type_code(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    body = analyse(api, repo.commit({"art/logo.ai": b"%!PS-Adobe\n" + b"a" * (2 * MB)}))
    assert body["skipped"] == [{"path": "art/logo.ai", "reason": "UNSUPPORTED_FILE_TYPE"}]
    assert paths(body["changes"]) == ["art/logo.ai"]


def test_the_denylist_lives_in_the_rules_file(api, make_repo, tmp_path, monkeypatch):
    from GitHub_Connector.settings import get_settings

    repo = make_repo()
    repo.commit({"seed": "0\n"})
    head = repo.commit({"page.html": "<p>hi</p>\n"})
    before = analyse(api, head)
    assert before["skipped"] == [{"path": "page.html", "reason": "UNSUPPORTED_FILE_TYPE"}]

    data = json.loads(RULES.read_text())
    data["unsupported"].remove(".html")
    edited = tmp_path / "rules.json"
    edited.write_text(json.dumps(data))
    monkeypatch.setenv("DRIFTER_RULES_FILE", str(edited))
    get_settings.cache_clear()

    after = analyse(api, head)
    assert after["skipped"] == []
    assert after["config_version"] != before["config_version"]


def test_file_skipped_by_type_is_never_downloaded(api, make_repo):
    # removes the image from the remote, so any attempt to download it fails the analysis
    from repos import git

    repo = make_repo()
    repo.commit({"seed": "0\n"})
    head = repo.commit({"big.png": PNG, "notes.md": "hi\n"})
    blob = git("rev-parse", f"{head}:big.png", cwd=repo.bare)
    loose = repo.bare / "objects" / blob[:2] / blob[2:]
    assert loose.is_file(), "expected the pushed image as a loose object"
    loose.chmod(0o644)  # git writes objects read-only, which Windows won't delete
    loose.unlink()
    body = analyse(api, head)
    assert reason_for(body, "big.png") == "UNSUPPORTED_FILE_TYPE"
    assert paths(body["changes"]) == ["big.png", "notes.md"]
