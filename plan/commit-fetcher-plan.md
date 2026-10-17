# Commit diff fetcher (the connector)

Scope: the connector in `Source/GitHub_Connector/fetch.py`. Given `owner/name`, a head commit and an optional base commit, it lists the changed files and skipped files and lets later steps read any file at either commit. It is the only code that runs git. The step-by-step reasoning is in [GitHub connector, step by step](github-connector-steps.md) (the guide); this file is the connector's interface and what is built.

Revised 2026-10-17 to match the v1.1 build. The first version planned hunks, `unidiff` and COPIED changes, all dropped by the [decision log](decisions-2026-10-17.md) (Q2, Q3), and described stubs that the v0 webhook receiver replaced.

## Approach: git CLI first, REST later

Checked live on 2026-10-16: a blobless clone of `psf/requests` with no checkout took about a second and 3.9 MB. After that, `git diff`, `git ls-tree` and `git cat-file` read both commits with no further setup.

Why git first (roadmap decision 3):
- No REST rate limit (60 requests an hour without a token).
- No 300-file cap. GitHub's `compare` endpoint returns its file list on the first page only, capped at 300; paging walks commits, not files.
- No dropped patches for large files or binaries.
- One mechanism for the diff, the file list and the file contents.

The REST fallback, for hosts without git, is left for v4. The Docker image ships git, so v1 doesn't need it.

## Interface (v1.1)

```python
with fetch(repo, head, base=None, deadline=None) as cmp:   # clone deleted when the block exits
    ...

Comparison
  repo
  head, base                          # full 40-hex SHAs; base is None for a first audit
  changes: list[FileChange]           # kept files only, see the guide's filter
  skipped: list[SkippedFile]          # binary, over 1 MB, not UTF-8
  tree(side) -> list[str]             # kept files at "base" or "head", no blob reads
  read(path, side) -> bytes | None    # None where the path is missing on that side

FileChange
  path
  change_type                         # ADDED | MODIFIED | DELETED | RENAMED | TYPE_CHANGED
  old_path                            # set only for RENAMED, never a hidden path

SkippedFile
  path, reason                        # "binary file" | "file larger than 1 MB" | "not valid UTF-8"
```

- `deadline` is a `time.monotonic()` value from `analyze()`. Any git call after it fails with `TIMEOUT`.
- COPIED is in the contract's enum but never produced, because only `-M` is used (Q3).
- There are no hunks. They come back with section-level mapping (after v2; see the [end-product plan](documentation-drifter-plan.md)).
- v1.2 uses `read()` to send the changed code and docs to the LLM. v1.3 or v2 uses it to read the mapping file.

## Steps inside `fetch`

| Step | git command | Later REST fallback |
|---|---|---|
| Clone | `git -c credential.helper= clone --filter=blob:none --no-checkout --quiet {url} {tmp}` | none needed |
| Fetch a commit no branch reaches | `git fetch --filter=blob:none origin {full sha}`, only when it isn't in the clone | — |
| Resolve a SHA | `git rev-parse --verify {sha}^{commit}` | `GET /repos/{o}/{r}/commits/{sha}` → `sha` |
| Default base | `git rev-parse {head}^1`; none for a root commit | `parents[0].sha` |
| First audit | diff against the empty tree (`git hash-object -t tree --stdin`) | — |
| Changed files and modes | `git diff --raw -z -M --no-abbrev {base} {head}` | `GET /compare/{base}...{head}` → `files[]` |
| Binaries, plus one batch fetch of changed blobs | `git diff --numstat -z -M {base} {head}` | — |
| Sizes | `git cat-file --batch-check` | — |
| NUL and UTF-8 checks | `git cat-file --batch` | — |
| File list | `git ls-tree -r -z {sha}` (no `-l`) | `GET /git/trees/{sha}?recursive=1` |
| File content | `git cat-file blob {sha}:{path}` | `GET /contents/{path}?ref={sha}` (raw) |

## Errors

| Situation | git signal | Code |
|---|---|---|
| Bad `owner/name` or SHA format | checked in `analyze()` before any git call | `INVALID_REQUEST` (400) |
| Repo missing or private | the clone fails | `REPOSITORY_NOT_FOUND` (404) |
| Unknown, non-commit, unfetchable or ambiguous SHA | `rev-parse` fails | `COMMIT_NOT_FOUND` (404); a short SHA gets a message asking for the full 40-character SHA |
| A git call over 60 s, or the 120 s deadline passed | timeout; the process group is killed | `TIMEOUT` (500) |
| Root commit with no base given | `{head}^1` fails | not an error: a first audit, every file ADDED |

## Safety (REQ-06)

- A fresh temporary folder per run, no checkout, deleted at the end, even after an error. Nothing from the repo is installed, imported or run.
- `GIT_TERMINAL_PROMPT=0` and an empty credential helper, so a private repo fails fast and no stored credentials are used.
- Every git call has a timeout and runs in its own process group, so a killed call leaves no helper behind.
- At most two analyses at once (a semaphore in `analyze()`).

## Tools

- The git CLI through `subprocess`.
- Dataclasses inside the connector; Pydantic only for the API models.
- No `unidiff` (Q2).
- `httpx` only in the tests, and for the REST fallback when it comes.

## Tests

Each test builds a small repo with git under `tmp_path` and checks the answer through the `/system` API (the spec's one test seam):

| Case | Where |
|---|---|
| One modified file → one MODIFIED | `test_v1_tracer.py` |
| An added and a deleted file → ADDED and DELETED | `test_v1_tracer.py` |
| A rename → one RENAMED with `old_path`; copies → ADDED | `test_v1_changes.py` |
| No base → first parent; root commit → base `null` and every file ADDED | `test_v1_tracer.py`, `test_v1_commits.py` |
| Unknown SHA → COMMIT_NOT_FOUND | `test_v1_commits.py` |
| 301 or more changed files all returned | `test_v1_changes.py` |
| Binary, oversize and non-UTF-8 files → `skipped[]` | `test_v1_skipped.py` |
| Fixture repo byte-identical before and after (AC-09) | `test_v1_tracer.py` |

`read()` and `tree()` are checked in review: their first user is v1.2. Network tests against `octocat/Hello-World` skip when offline.

## Settled questions

1. **git or REST as the main path:** git (roadmap decision 3).
2. **Pydantic now or later:** dataclasses in the connector, Pydantic for the API models.
3. **Test repo:** built deterministically by `tools/testrepo.py` (ticket 11). It is made public once Kaan approves.

## Left out on purpose (minimal first)

Webhooks (v4), caching clones between runs, following renames, private-repo tokens, the REST fallback, and language-specific parsing (sectioning, after v2).
