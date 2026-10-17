# reads the analysed repo with git, the only code in v1 that runs git

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from GitHub_Connector.schemas import AnalysisError, ChangeType, ErrorCode
from GitHub_Connector.settings import get_settings

# maps git's status letters to the contract's change types
_STATUS = {
    "A": ChangeType.ADDED,
    "M": ChangeType.MODIFIED,
    "D": ChangeType.DELETED,
    "R": ChangeType.RENAMED,
    "T": ChangeType.TYPE_CHANGED,
}

# keeps plain and executable files, drops symlinks (120000) and submodules (160000)
REGULAR = {"100644", "100755"}


@dataclass(frozen=True)
class FileChange:
    # describes one changed path as git reports it
    path: str
    change_type: ChangeType
    old_path: str | None = None


@dataclass
class Comparison:
    # carries what changed between base and head, valid only inside fetch()
    repo: str
    head: str
    base: str | None
    changes: list[FileChange] = field(default_factory=list)
    _git: _Git | None = None

    def tree(self, side: str) -> list[str]:
        # lists the kept files at "base" or "head", without -l so no blob is fetched
        sha = self.head if side == "head" else self.base
        if sha is None:
            return []
        raw = self._git.run("ls-tree", "-r", "-z", "--full-tree", sha).stdout
        paths = []
        for entry in raw.decode("utf-8", "surrogateescape").split("\0"):
            if entry:
                meta, path = entry.split("\t", 1)
                if kept(path, meta.split(" ")[0]):
                    paths.append(path)
        return sorted(paths)


class _Git:
    # runs git anonymously inside one temporary clone

    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir
        self.env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",  # fails a private repo at once instead of asking
            "GIT_ASKPASS": "",
            "SSH_ASKPASS": "",
            "LC_ALL": "C",
        }

    def run(self, *args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        # runs one git command with no credential helper, returns raw bytes
        cmd = ["git", "-c", "credential.helper=", "-c", "core.quotepath=false", *args]
        proc = subprocess.run(
            cmd,
            cwd=cwd or self.workdir / "clone",
            env=self.env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
        )
        if check and proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, proc.stdout, proc.stderr)
        return proc

    def ok(self, *args: str) -> bool:
        # reports whether a git command succeeds, used for probes like rev-parse
        return self.run(*args, check=False).returncode == 0

    def out(self, *args: str) -> str:
        # runs a git command and returns its trimmed text output
        return self.run(*args).stdout.decode("utf-8", "surrogateescape").strip()


def _remote_url(repo: str) -> str:
    # builds the clone URL, tests repoint the base at local bare repos
    base = get_settings().remote_base_url
    return base.rstrip("/") + "/" + repo + ".git"


def _rmtree(path: Path) -> None:
    # deletes a clone, clearing read-only bits that git sets on pack files (Windows)
    def _retry(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_retry)
    else:
        shutil.rmtree(path, onerror=_retry)


@contextmanager
def fetch(repo: str, head: str, base: str | None = None) -> Iterator[Comparison]:
    # clones repo blobless into a temp folder, yields the comparison, deletes the clone on exit
    clone_root = get_settings().clone_dir
    if clone_root is not None:
        clone_root.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="drifter-", dir=clone_root))
    try:
        git = _Git(workdir)
        _clone(git, repo)
        head_sha = _resolve(git, head)
        base_sha = _resolve(git, base) if base is not None else _first_parent(git, head_sha)
        cmp = Comparison(repo=repo, head=head_sha, base=base_sha, _git=git)
        cmp.changes = _diff(git, base_sha, head_sha)
        yield cmp
    finally:
        _rmtree(workdir)


def _clone(git: _Git, repo: str) -> None:
    # makes a blobless, no-checkout clone, so nothing from the repo lands on disk as files
    proc = git.run(
        "clone", "--filter=blob:none", "--no-checkout", "--quiet",
        _remote_url(repo), str(git.workdir / "clone"),
        cwd=git.workdir, check=False,
    )
    if proc.returncode != 0:
        raise AnalysisError(
            ErrorCode.REPOSITORY_NOT_FOUND,
            f"Repository {repo} not found or is not public",
        )


def _resolve(git: _Git, sha: str) -> str:
    # expands a SHA to its full 40-hex form, fetching a full SHA by id when no branch reaches it
    sha = sha.lower()
    full = len(sha) == 40
    if full and not _present(git, sha):
        # asks for the commit by id, GitHub serves any commit in the repo this way
        git.run("fetch", "--quiet", "--no-tags", "--filter=blob:none", "origin", sha, check=False)
    proc = git.run("rev-parse", "--verify", "--quiet", "--end-of-options", f"{sha}^{{commit}}", check=False)
    if proc.returncode != 0:
        if full:
            raise AnalysisError(ErrorCode.COMMIT_NOT_FOUND, f"Commit {sha} not found")
        raise AnalysisError(
            ErrorCode.COMMIT_NOT_FOUND,
            f"Commit {sha} not found or ambiguous; a short SHA only works for a commit on a "
            "branch or tag, so send the full 40-character SHA",
        )
    return proc.stdout.decode().strip()


def _present(git: _Git, sha: str) -> bool:
    # checks the clone for an object without a lazy fetch (git 2.44+ honours the flag)
    git.env["GIT_NO_LAZY_FETCH"] = "1"
    try:
        return git.ok("cat-file", "-e", sha)
    finally:
        del git.env["GIT_NO_LAZY_FETCH"]


def _first_parent(git: _Git, head: str) -> str | None:
    # returns the head's first parent, None for a root commit
    proc = git.run("rev-parse", "--verify", "--quiet", f"{head}^1", check=False)
    return proc.stdout.decode().strip() if proc.returncode == 0 else None


def kept(path: str, mode: str) -> bool:
    # admits a regular file with no hidden segment, everything else is an ignored path
    return mode in REGULAR and not any(part.startswith(".") for part in path.split("/"))


def _diff(git: _Git, base: str | None, head: str) -> list[FileChange]:
    # lists changed paths between base and head, renames only, never copies
    # compares a first audit against the empty tree, so every file counts as added
    old = base if base is not None else git.out("hash-object", "-t", "tree", "--stdin")
    raw = git.run("diff", "--raw", "-z", "-M", "--no-abbrev", "--no-ext-diff", old, head).stdout
    fields = raw.decode("utf-8", "surrogateescape").split("\0")
    changes: list[FileChange] = []
    i = 0
    while i < len(fields) and fields[i]:
        # reads ":oldmode newmode oldsha newsha status" then one or two paths
        old_mode, new_mode, _, _, status = fields[i][1:].split(" ")
        letter = status[0]
        if letter == "R":
            old_path, new_path = fields[i + 1], fields[i + 2]
            i += 3
            # checks each side on its own, so an ignored path never shows, not even as old_path
            old_ok, new_ok = kept(old_path, old_mode), kept(new_path, new_mode)
            if old_ok and new_ok:
                changes.append(FileChange(new_path, ChangeType.RENAMED, old_path))
            elif new_ok:
                changes.append(FileChange(new_path, ChangeType.ADDED))
            elif old_ok:
                changes.append(FileChange(old_path, ChangeType.DELETED))
            continue
        path = fields[i + 1]
        i += 2
        # judges the head side, or the base side for a deletion
        if kept(path, old_mode if letter == "D" else new_mode):
            changes.append(FileChange(path, _STATUS[letter]))
    return changes
