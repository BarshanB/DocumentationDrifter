# covers ticket 05: change types, renames, and ignored paths that never appear anywhere

import os

import pytest

from repos import git

def _can_symlink() -> bool:
    # checks that this machine can create symlinks (Windows needs Developer Mode for it)
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        try:
            os.symlink("target", os.path.join(d, "link"))
            return True
        except (OSError, NotImplementedError):
            return False


SYMLINKS = _can_symlink()


def analyse(api, head, **extra):
    # posts one analysis request and returns the parsed body
    r = api.post("/system/analyze", json={"repository": "octo/demo", "commit_id": head, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def listing(body):
    # reduces changes[] to (path, change_type, old_path) triples
    return [(c["path"], c["change_type"], c["old_path"]) for c in body["changes"]]


TEXT = "".join(f"line {i}: the quick brown fox jumps over the lazy dog\n" for i in range(40))


def test_moved_file_is_one_renamed_change(api, make_repo):
    repo = make_repo()
    repo.commit({"old/name.txt": TEXT})
    head = repo.commit({"old/name.txt": None, "new/name.txt": TEXT})
    assert listing(analyse(api, head)) == [("new/name.txt", "RENAMED", "old/name.txt")]


def test_lightly_edited_move_is_still_a_rename(api, make_repo):
    repo = make_repo()
    repo.commit({"a.txt": TEXT})
    head = repo.commit({"a.txt": None, "b.txt": TEXT + "one more line\n"})
    assert listing(analyse(api, head)) == [("b.txt", "RENAMED", "a.txt")]


def test_move_below_half_similarity_is_delete_plus_add(api, make_repo):
    repo = make_repo()
    repo.commit({"a.txt": TEXT})
    rewritten = "".join(f"entirely new content {i}\n" for i in range(40))
    head = repo.commit({"a.txt": None, "b.txt": rewritten})
    assert listing(analyse(api, head)) == [("a.txt", "DELETED", None), ("b.txt", "ADDED", None)]


def test_copy_is_reported_as_added(api, make_repo):
    repo = make_repo()
    repo.commit({"a.txt": TEXT})
    head = repo.commit({"copy.txt": TEXT})
    body = analyse(api, head)
    assert listing(body) == [("copy.txt", "ADDED", None)]
    assert all(c["change_type"] != "COPIED" for c in body["changes"])


def test_every_change_of_a_huge_commit_is_returned_sorted(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    files = {f"bulk/file{i:03d}.txt": f"{i}\n" for i in range(305)}
    head = repo.commit(files)
    paths = [c["path"] for c in analyse(api, head)["changes"]]
    assert paths == sorted(files)


def test_tester_change_types(api, make_repo):
    # added, modified and deleted in one commit, each listed once
    repo = make_repo()
    repo.commit({"keep.txt": "k\n", "edit.txt": "1\n", "gone.txt": "g\n"})
    head = repo.commit({"edit.txt": "2\n", "gone.txt": None, "new.txt": "n\n"})
    assert listing(analyse(api, head)) == [
        ("edit.txt", "MODIFIED", None),
        ("gone.txt", "DELETED", None),
        ("new.txt", "ADDED", None),
    ]


def test_hidden_paths_are_ignored(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    head = repo.commit({
        ".gitignore": "*.pyc\n",
        ".github/x.md": "# workflows\n",
        "src/a.py": "x = 1\n",
        "docs/.cache/deep.md": "hidden deep\n",
        "src/pkg/.env.example": "A=1\n",
    })
    assert listing(analyse(api, head)) == [("src/a.py", "ADDED", None)]


@pytest.mark.skipif(not SYMLINKS, reason="needs symlink support")
def test_symlink_is_not_listed(api, make_repo):
    repo = make_repo()
    repo.commit({"target.txt": "t\n"})
    head = repo.commit({"real.txt": "r\n"}, symlinks={"link.txt": "target.txt"})
    assert listing(analyse(api, head)) == [("real.txt", "ADDED", None)]


def test_submodule_is_not_listed(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    head = repo.commit({"real.txt": "r\n"}, gitlinks={"vendor/lib": "1" * 40})
    assert listing(analyse(api, head)) == [("real.txt", "ADDED", None)]


def test_executable_file_is_kept(api, make_repo):
    repo = make_repo()
    repo.commit({"seed": "0\n"})
    head = repo.commit({"run.sh": "#!/bin/sh\necho hi\n"}, executable=("run.sh",))
    assert listing(analyse(api, head)) == [("run.sh", "ADDED", None)]


def test_rename_out_of_a_hidden_folder_is_added(api, make_repo):
    repo = make_repo()
    repo.commit({".github/a.md": TEXT})
    head = repo.commit({".github/a.md": None, "docs/a.md": TEXT})
    assert listing(analyse(api, head)) == [("docs/a.md", "ADDED", None)]


def test_rename_into_a_hidden_folder_is_deleted(api, make_repo):
    repo = make_repo()
    repo.commit({"docs/x.md": TEXT})
    head = repo.commit({"docs/x.md": None, ".archive/x.md": TEXT})
    assert listing(analyse(api, head)) == [("docs/x.md", "DELETED", None)]


@pytest.mark.skipif(not SYMLINKS, reason="needs symlink support")
def test_switch_between_file_and_symlink_never_lists_the_link_side(api, make_repo):
    repo = make_repo()
    repo.commit({"target.txt": "t\n", "flip.txt": "regular\n"})
    to_link = repo.commit({}, symlinks={"flip.txt": "target.txt"})
    back = repo.commit({"flip.txt": "regular again\n"})
    # the regular-to-link side lists nothing; the link-to-regular side lists only the regular file
    assert listing(analyse(api, to_link)) == []
    assert [c["path"] for c in analyse(api, back)["changes"]] == ["flip.txt"]
