# covers ticket 18: the console served at / beside the /system contract

from pathlib import Path

CONSOLE = Path(__file__).resolve().parents[1] / "Source" / "Frontend" / "index.html"


def test_root_serves_the_console(api):
    r = api.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.content == CONSOLE.read_bytes()


def test_console_is_not_in_the_contract(api):
    paths = api.get("/system/openapi.json").json()["paths"]
    assert "/" not in paths


def test_console_and_api_share_one_app(api, make_repo):
    repo = make_repo()
    repo.commit({"README.md": "# demo\n"}, "first")
    head = repo.commit({"README.md": "# demo\n\nmore\n"}, "second")
    assert api.get("/").status_code == 200
    r = api.post("/system/analyze", json={"repository": "octo/demo", "commit_id": head})
    assert r.status_code == 200
    assert [c["path"] for c in r.json()["changes"]] == ["README.md"]
