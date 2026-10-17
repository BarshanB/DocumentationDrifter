# covers ticket 07: categories from the ordered path rules, and config_version as their hash

import json
from pathlib import Path

import pytest

RULES = Path(__file__).resolve().parents[1] / "Source" / "GitHub_Connector" / "path_rules.json"

CASES = {
    "docs/installation.rst": "DOCUMENTATION",
    "README.md": "DOCUMENTATION",
    "guide/intro.rst": "DOCUMENTATION",
    "notes/todo.txt": "DOCUMENTATION",
    "docs/diagram.svg": "DOCUMENTATION",
    "docs/api/conf.py": "DOCUMENTATION",
    "src/pkg/README.md": "DOCUMENTATION",
    "requirements.txt": "OTHER",
    "requirements-dev.txt": "OTHER",
    "docs/requirements.txt": "OTHER",
    "src/main.c": "IMPLEMENTATION",
    "tests/data.json": "IMPLEMENTATION",
    "tools/build.py": "IMPLEMENTATION",
    "setup.py": "IMPLEMENTATION",
    "Makefile": "OTHER",
    "README": "OTHER",
    "setup.cfg": "OTHER",
    "poetry.lock": "OTHER",
    "package-lock.json": "OTHER",
    "lib/docs/x.c": "OTHER",
}


def analyse(api, head):
    # posts one analysis request and returns the parsed body
    r = api.post("/system/analyze", json={"repository": "octo/demo", "commit_id": head})
    assert r.status_code == 200, r.text
    return r.json()


def test_each_path_gets_the_first_matching_rule(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    head = repo.commit({path: f"{path}\n" for path in CASES})
    got = {c["path"]: c["category"] for c in analyse(api, head)["changes"]}
    assert got == CASES


def test_renamed_file_is_classified_by_its_new_path(api, make_repo):
    repo = make_repo()
    text = "".join(f"line {i}\n" for i in range(30))
    repo.commit({"notes.py": text})
    change = analyse(api, repo.commit({"notes.py": None, "docs/notes.md": text}))["changes"][0]
    assert (change["change_type"], change["category"]) == ("RENAMED", "DOCUMENTATION")


def test_there_are_no_design_architecture_specification_or_requirement_rules():
    used = {r["category"] for r in json.loads(RULES.read_text())["rules"]}
    assert used <= {"IMPLEMENTATION", "DOCUMENTATION", "OTHER"}


def test_config_version_follows_the_rules_file(api, make_repo, tmp_path, monkeypatch):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    head = repo.commit({"a.md": "a\n"})
    first, again = analyse(api, head)["config_version"], analyse(api, head)["config_version"]
    assert first == again and isinstance(first, str) and len(first) <= 16

    edited = tmp_path / "rules.json"
    data = json.loads(RULES.read_text())
    data["rules"].insert(0, {"pattern": "*.md", "category": "OTHER"})
    edited.write_text(json.dumps(data))
    monkeypatch.setenv("DRIFTER_RULES_FILE", str(edited))
    from GitHub_Connector.settings import get_settings

    get_settings.cache_clear()
    body = analyse(api, head)
    assert body["config_version"] != first
    assert body["changes"][0]["category"] == "OTHER"
