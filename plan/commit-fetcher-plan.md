# Commit diff fetcher: plan

Scope: the `Source/GitHub_Connector` piece only. Given `owner/name`, a head commit and an optional base commit, return the changed files (status, hunks) and let later steps read any file at either commit. Fits step 3 of the [overall plan](documentation-drifter-plan.md). Nothing has been added to the repo.

## What's in the stubs today

*Superseded (2026-10-17).* The stubs this table described (`monitor()`, `get_diff()`, `Change_request`, the `Repository` outline) were replaced by the v0 webhook receiver in `e3a718e`. See the [roadmap](roadmap.md)'s "Where we are: v0" section and its v1 code layout. The fetcher below becomes `fetch.py`, a new module beside the v0 files.

## Approach: git CLI first, REST as fallback

Checked live today: `git clone --filter=blob:none --no-checkout` of `psf/requests` took about 1 second and 3.9 MB, then `git diff`, `git ls-tree` and `git show` read both commits with no further setup.

Why git first:
- No REST rate limit (60/h without a token).
- No 300-file cap. Note: paging `compare` does **not** get past 300 files. GitHub returns the file list on the first page only, capped at 300; paging only walks commits. The [API notes](../github-api/base-head-endpoints.md) suggest otherwise and should be corrected.
- No dropped patches for large files (`compare` omits `patch` for big diffs and binaries).
- One mechanism for diff, tree and file content.

REST stays for hosts without `git`, or as a cheap pre-check (repo exists, commit exists) before cloning.

## Interface

```python
with fetch(repo: str, head: str, base: str | None = None) as cmp:   # yields a Comparison; clone deleted on exit

Comparison
  repo, head_sha, base_sha           # full 40-char SHAs
  files: list[FileChange]
  read(path, side) -> bytes | None   # side = "base" | "head"
  tree(side) -> list[str]

FileChange
  path, status                       # ADDED | MODIFIED | DELETED | RENAMED | COPIED | TYPE_CHANGED
  old_path                           # set when git saw a rename
  hunks: list[Hunk]
  binary: bool

Hunk
  old_start, old_len, new_start, new_len
```

Renames: *(updated 2026-10-17 to match the pod's contract)* a rename is one `RENAMED` change with `old_path` set, as T-03 expects. `status` uses the contract's vocabulary: ADDED, MODIFIED, DELETED, RENAMED, COPIED, TYPE_CHANGED. Schema v14 still doesn't follow renames for mapping, so the detector treats the new path as unrelated to the old one.

## Steps inside `fetch`

| Step | git command | REST fallback |
|---|---|---|
| Clone | `git clone --filter=blob:none --no-checkout --quiet https://github.com/{o}/{r}.git {tmp}` | none needed |
| Get commits not on the default branch | `git fetch origin {sha}` | — |
| Resolve head | `git rev-parse --verify {head}^{commit}` | `GET /repos/{o}/{r}/commits/{head}` → `sha` |
| Default base | `git rev-parse {head}^` (first parent; none for a root commit) | `parents[0].sha` |
| Changed files | `git diff --name-status -M {base} {head}` | `GET /compare/{base}...{head}` → `files[]` |
| ~~Hunks~~ | ~~`git diff -U0 -M {base} {head}` parsed with `unidiff`~~ *Decided 2026-10-17 (Q2): dropped from v1.1.* | each file's `patch` (missing if too large) |
| File list | `git ls-tree -r --name-only {sha}` | `GET /git/trees/{sha}?recursive=1` |
| File content | `git show {sha}:{path}` | `GET /contents/{path}?ref={sha}` (raw) |

*Decided 2026-10-17 (Q2, Q3):* hunks are dropped, because nothing in the contract reads them; v1.2 may pass the plain `git diff` text to the LLM. `-M` is used without `-C`, so COPIED is never produced.

## Errors (maps to the spec codes)

| Situation | git signal | REST signal | Spec code |
|---|---|---|---|
| Bad `owner/name` or SHA format | checked before any call | — | `INVALID_REQUEST` (400) |
| Repo missing or private | clone exits 128, "not found" / auth prompt blocked | 404 | `REPOSITORY_NOT_FOUND` (404), the pod's contract code |
| Unknown commit | `rev-parse` fails after fetch | 422 on `/commits`, 404 on `/compare` | `COMMIT_NOT_FOUND` (404) |
| Root commit, no base given | `{head}^` fails | `parents` empty | diff against the empty tree (every file added) |
| Too slow / too big | `timeout` on each subprocess | rate limit 403/429 | `TIMEOUT` |

## Safety (REQ-06)

- Fresh temp dir per run, `--no-checkout`, deleted at the end. Nothing in the repo is installed, imported or run.
- `GIT_TERMINAL_PROMPT=0` so a private repo fails fast instead of waiting for a password.
- A timeout on every git call, and a cap on changed-file count.

## Tools

| Need | Tool | Why |
|---|---|---|
| Fetch and diff | `git` CLI via `subprocess` | Already installed everywhere; GitPython/pygit2 add little |
| Parse diffs | `unidiff` | Handles hunks, added/removed files, renames, binary markers |
| Data shapes | Pydantic v2 (or dataclasses until the API exists) | Same models feed `POST /analyze` later |
| REST fallback | `httpx` | Timeouts and headers built in; `requests` works too |
| Tests | `pytest` | |

## Tests

Built from tiny repos the tests create with `git init` in `tmp_path`, so they need no network and the expected answer is exact:

1. Modify one line → one `MODIFIED` file.
2. Add a file, delete a file → `ADDED` and `DELETED`.
3. Rename → `old_path` set.
4. No base given → base is the head's parent.
5. Root commit → every file `added`.
6. Unknown SHA → `COMMIT_NOT_FOUND`.
7. 301+ changed files → all returned (the case REST can't do).
8. `read(path, "base")` and `read(path, "head")` return the right content; missing side returns `None`.
9. The fixture repo is byte-identical before and after (AC-09).

One optional network test against a small public repo, skipped when offline.

## Open questions for Kaan

1. **git vs REST as the main path.** This thread was first set up to use the REST `compare` endpoint; the overall plan and this one recommend git. Recommended: git.
2. **Pydantic now or later.** Recommended: plain dataclasses for the fetcher, switch when the API models land.
3. **Test repo.** The project repo is private, so a public repo with labelled cases is still needed for end-to-end checks.

## Left out on purpose (minimal first)

Webhooks and `monitor()`, caching clones between runs, following renames, private-repo tokens, and any language-specific parsing (that's step 7).
