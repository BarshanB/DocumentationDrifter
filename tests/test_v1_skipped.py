# covers ticket 06: binary, oversize and non-UTF-8 files are skipped with a reason, never checked

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 8
MB = 1024 * 1024


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


def test_changed_png_is_skipped_as_binary(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    body = analyse(api, repo.commit({"logo.png": PNG, "notes.md": "hi\n"}))
    assert paths(body["skipped"]) == ["logo.png"]
    assert reason_for(body, "logo.png") == "binary file"
    assert paths(body["changes"]) == ["notes.md"]


def test_nul_byte_in_the_first_8kb_marks_binary(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    body = analyse(api, repo.commit({"data.txt": b"text" * 100 + b"\0" + b"more\n"}))
    assert reason_for(body, "data.txt") == "binary file"


def test_size_cap_is_exact(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    head = repo.commit({"big.txt": b"a" * MB + b"\n", "fits.txt": b"a" * (MB - 1) + b"\n"})
    body = analyse(api, head)
    assert paths(body["skipped"]) == ["big.txt"]
    assert reason_for(body, "big.txt") == "file larger than 1 MB"
    assert paths(body["changes"]) == ["fits.txt"]


def test_non_utf8_file_is_skipped(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    body = analyse(api, repo.commit({"latin1.txt": "café crème\n".encode("latin-1")}))
    assert reason_for(body, "latin1.txt") == "not valid UTF-8"
    assert body["changes"] == []


def test_deleted_binary_is_still_skipped(api, make_repo):
    repo = make_repo()
    repo.commit({"logo.png": PNG, "keep": "k\n"})
    body = analyse(api, repo.commit({"logo.png": None}))
    assert paths(body["skipped"]) == ["logo.png"]
    assert body["changes"] == []


def test_unchanged_binary_and_big_files_are_not_skipped(api, make_repo):
    repo = make_repo()
    repo.commit({"logo.png": PNG, "big.txt": b"a" * (2 * MB)})
    body = analyse(api, repo.commit({"readme": "changed\n"}))
    assert body["skipped"] == []
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
    assert body["changes"] == []
