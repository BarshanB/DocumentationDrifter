# covers ticket 04: short SHAs, commits off every branch, odd bases and first audits

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from repos import GIT_ENV, FixtureRepo, git


def analyse(api, head, repo="octo/demo", **extra):
    # posts one analysis request and returns the response
    return api.post("/system/analyze", json={"repository": repo, "commit_id": head, **extra})


def listing(body):
    # reduces changes[] to (path, change_type) pairs
    return [(c["path"], c["change_type"]) for c in body["changes"]]


def assert_not_found(r, env, asks_full=False):
    # checks a COMMIT_NOT_FOUND answer that saved nothing and left no clone
    assert r.status_code == 404, r.text
    body = r.json()
    assert body["code"] == "COMMIT_NOT_FOUND"
    assert ("40-character" in body["message"]) is asks_full
    assert list(env["runs"].iterdir()) == []
    assert list(env["clones"].iterdir()) == []


@pytest.fixture
def line(make_repo):
    # builds a straight history a1 -> a2 -> a3, each adding one file
    repo = make_repo()
    shas = [repo.commit({f"f{i}": f"{i}\n"}) for i in (1, 2, 3)]
    return repo, shas


def test_base_several_commits_behind(api, line):
    _, (a1, a2, a3) = line
    body = analyse(api, a3, base_commit=a1).json()
    assert body["base_commit"] == a1
    assert listing(body) == [("f2", "ADDED"), ("f3", "ADDED")]


def test_base_equal_to_head_is_an_empty_success(api, line):
    _, (_, _, a3) = line
    r = analyse(api, a3, base_commit=a3)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "SUCCESS" and body["changes"] == []
    assert api.get(f"/system/analysis/{body['analysis_id']}").content == r.content


def test_base_after_head_gives_the_reverse_listing(api, line):
    _, (a1, _, a3) = line
    body = analyse(api, a1, base_commit=a3).json()
    assert listing(body) == [("f2", "DELETED"), ("f3", "DELETED")]


def test_base_from_unrelated_history(api, line):
    repo, (_, _, a3) = line
    repo.run("checkout", "--quiet", "--orphan", "other")
    repo.run("rm", "-rf", "--quiet", ".")
    other = repo.commit({"f1": "different\n", "solo": "s\n"}, push=False)
    repo.run("push", "--quiet", "origin", "other")
    body = analyse(api, a3, base_commit=other).json()
    assert body["status"] == "SUCCESS"
    assert listing(body) == [("f1", "MODIFIED"), ("f2", "ADDED"), ("f3", "ADDED"), ("solo", "DELETED")]


def test_root_commit_is_a_first_audit(api, make_repo):
    repo = make_repo()
    root = repo.commit({"a": "1\n", "dir/b": "2\n"})
    repo.commit({"c": "3\n"})
    body = analyse(api, root).json()
    assert body["base_commit"] is None
    assert listing(body) == [("a", "ADDED"), ("dir/b", "ADDED")]


def test_merge_commit_is_compared_with_its_first_parent(api, make_repo):
    repo = make_repo()
    repo.commit({"base": "0\n"})
    repo.run("checkout", "--quiet", "-b", "side")
    repo.commit({"side": "s\n"}, push=False)
    repo.run("checkout", "--quiet", "main")
    main_tip = repo.commit({"main": "m\n"}, push=False)
    repo.run("merge", "--quiet", "--no-ff", "--no-edit", "side")
    merge = repo.run("rev-parse", "HEAD")
    repo.run("push", "--quiet", "origin", "main")
    body = analyse(api, merge).json()
    assert body["base_commit"] == main_tip
    assert listing(body) == [("side", "ADDED")]


def test_short_shas_come_back_full(api, line):
    _, (a1, _, a3) = line
    body = analyse(api, a3[:7], base_commit=a1[:7]).json()
    assert body["head_commit"] == a3
    assert body["base_commit"] == a1


@pytest.fixture
def unreachable(line):
    # pushes a commit, then deletes the only ref that reaches it, as with a force-pushed PR
    repo, shas = line
    lost = repo.commit({"lost": "x\n"}, push=False)
    repo.run("push", "--quiet", "origin", "HEAD:refs/heads/tmp")
    repo.run("push", "--quiet", "origin", ":refs/heads/tmp")
    return repo, lost


def test_full_sha_off_every_branch_is_fetched(api, unreachable):
    _, lost = unreachable
    r = analyse(api, lost)
    assert r.status_code == 200
    assert listing(r.json()) == [("lost", "ADDED")]


def test_unknown_full_commit(api, line, v1_env):
    assert_not_found(analyse(api, "1" * 40), v1_env)


def test_unknown_full_base_commit(api, line, v1_env):
    _, (_, _, a3) = line
    assert_not_found(analyse(api, a3, base_commit="2" * 40), v1_env)


def test_sha_that_names_a_tree_is_not_a_commit(api, line, v1_env):
    repo, (_, _, a3) = line
    tree = repo.run("rev-parse", f"{a3}^{{tree}}")
    assert_not_found(analyse(api, tree), v1_env)


def test_short_sha_off_every_branch_asks_for_the_full_sha(api, unreachable, v1_env):
    _, lost = unreachable
    assert_not_found(analyse(api, lost[:7]), v1_env, asks_full=True)


def test_unknown_short_sha_asks_for_the_full_sha(api, line, v1_env):
    assert_not_found(analyse(api, "1234567"), v1_env, asks_full=True)


# --- shared prefix ---------------------------------------------------


def _commit_object(tree: str, message: str) -> bytes:
    # spells a root commit exactly as git commit-tree would with the fixture identity
    who = "Fixture <fixture@example.com> 1767225600 +0000"
    return f"tree {tree}\nauthor {who}\ncommitter {who}\n\n{message}\n".encode()


def _sha1(kind: str, body: bytes) -> str:
    # hashes an object the way git does
    return hashlib.sha1(f"{kind} {len(body)}\0".encode() + body).hexdigest()


@pytest.fixture(scope="session")
def twin_commits(tmp_path_factory):
    # finds two commits whose SHAs share 7 hex digits, then writes only those two
    root = tmp_path_factory.mktemp("twins")
    bare = root / "octo" / "twins.git"
    bare.parent.mkdir(parents=True)
    git("init", "--quiet", "--bare", "--initial-branch=main", str(bare), cwd=root)
    git("config", "uploadpack.allowFilter", "true", cwd=bare)
    tree = git("hash-object", "-t", "tree", "-w", "--stdin", cwd=bare, input=b"")
    seen: dict[str, str] = {}
    i = 0
    while True:
        message = f"twin {i}"
        prefix = _sha1("commit", _commit_object(tree, message))[:7]
        if prefix in seen:
            break
        seen[prefix] = message
        i += 1
    shas = [
        git("hash-object", "-t", "commit", "-w", "--stdin", cwd=bare, input=_commit_object(tree, m))
        for m in (seen[prefix], message)
    ]
    assert shas[0][:7] == shas[1][:7] and shas[0] != shas[1]
    git("update-ref", "refs/heads/main", shas[0], cwd=bare)
    git("update-ref", "refs/heads/twin", shas[1], cwd=bare)
    return root, shas


def test_short_sha_shared_by_two_commits_asks_for_the_full_sha(api, v1_env, twin_commits, monkeypatch):
    root, shas = twin_commits
    monkeypatch.setenv("DRIFTER_REMOTE_BASE_URL", root.as_uri() + "/")
    from GitHub_Connector.settings import get_settings

    get_settings.cache_clear()
    assert analyse(api, shas[0], repo="octo/twins").status_code == 200
    for p in v1_env["runs"].iterdir():
        p.unlink()
    assert_not_found(analyse(api, shas[0][:7], repo="octo/twins"), v1_env, asks_full=True)
