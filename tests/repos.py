# builds fixture repos that the v1 tests analyse through a local remote base URL

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

# pins identity and dates, so a fixture builds the same on any machine
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.com",
    "GIT_COMMITTER_NAME": "Fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.com",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(*args: str, cwd: Path, input: bytes | None = None) -> str:
    # runs git for the fixture with a fixed identity, returns stdout text
    env = {**os.environ, **GIT_ENV}
    proc = subprocess.run(
        ["git", *args], cwd=cwd, env=env, input=input, capture_output=True, check=True
    )
    return proc.stdout.decode().strip()


class FixtureRepo:
    # owns a working copy and the bare remote it pushes to, served like GitHub serves a repo

    def __init__(self, remotes: Path, work_root: Path, name: str) -> None:
        self.name = name
        self.bare = remotes / f"{name}.git"
        self.work = work_root / name
        self.bare.parent.mkdir(parents=True, exist_ok=True)
        self.work.mkdir(parents=True)
        git("init", "--quiet", "--bare", "--initial-branch=main", str(self.bare), cwd=remotes)
        # lets clients clone blobless and fetch any SHA, as github.com does
        git("config", "uploadpack.allowFilter", "true", cwd=self.bare)
        git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=self.bare)
        git("init", "--quiet", "--initial-branch=main", cwd=self.work)
        git("config", "core.autocrlf", "false", cwd=self.work)
        git("config", "core.symlinks", "true", cwd=self.work)
        git("remote", "add", "origin", str(self.bare), cwd=self.work)
        self._tick = 0

    def commit(
        self,
        files: dict[str, bytes | str | None],
        message: str = "change",
        push: bool = True,
        symlinks: dict[str, str] | None = None,
        executable: tuple[str, ...] = (),
        gitlinks: dict[str, str] | None = None,
    ) -> str:
        # writes files (None deletes), links and submodule entries, commits and pushes, returns the SHA
        for rel, content in files.items():
            path = self.work / rel
            if content is None:
                path.unlink()
                continue
            if path.is_symlink():
                path.unlink()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode() if isinstance(content, str) else content)
        for rel, target in (symlinks or {}).items():
            path = self.work / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() or path.is_symlink():
                path.unlink()
            path.symlink_to(target)
        return self._commit(message, push, executable, gitlinks or {})

    def _commit(self, message: str, push: bool, executable=(), gitlinks=None) -> str:
        # commits the working copy with a fresh date, so every commit gets its own SHA
        self._tick += 1
        date = f"2026-01-01T{self._tick // 3600:02d}:{self._tick // 60 % 60:02d}:{self._tick % 60:02d}Z"
        env = {**os.environ, **GIT_ENV, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        subprocess.run(["git", "add", "-A"], cwd=self.work, env=env, check=True)
        for rel in executable:
            subprocess.run(["git", "update-index", "--chmod=+x", rel], cwd=self.work, env=env, check=True)
        for rel, sha in (gitlinks or {}).items():
            subprocess.run(
                ["git", "update-index", "--add", "--cacheinfo", f"160000,{sha},{rel}"],
                cwd=self.work, env=env, check=True,
            )
        subprocess.run(
            ["git", "commit", "--quiet", "--allow-empty", "-m", message],
            cwd=self.work, env=env, check=True, capture_output=True,
        )
        sha = git("rev-parse", "HEAD", cwd=self.work)
        if push:
            git("push", "--quiet", "--force", "origin", "HEAD:refs/heads/main", cwd=self.work)
        return sha

    def run(self, *args: str) -> str:
        # runs any git command in the working copy, for branches, merges and the like
        return git(*args, cwd=self.work)

    def digest(self) -> str:
        # hashes every byte of the bare remote, to prove an analysis left it untouched
        h = hashlib.sha256()
        for path in sorted(self.bare.rglob("*")):
            h.update(str(path.relative_to(self.bare)).encode())
            if path.is_file():
                h.update(path.read_bytes())
        return h.hexdigest()
