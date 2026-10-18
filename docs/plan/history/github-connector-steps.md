# GitHub connector, step by step

> **History, superseded.** Kept for the reasoning behind v1.1. The current plan is the [roadmap](../roadmap.md), the [v1.1 spec](../../Models/v1/v1.1/spec-v1.1.md) and the [decision log](../decisions.md); where this file disagrees with them, they win.

How to build the piece that connects to a **public GitHub repo**, gets the **base and head commit ids**, and reads **all source code and documentation** at both commits, skipping hidden files such as `.gitignore`.

**Spec sources used.** The project's specification is the Phase 2 spec, now kept as text in [docs/vision/](../../vision/README.md). This guide treats it as "the provided file". The repo's `docs/vision/documentation-tracker-schema-v14.pdf` (schema v14) adds the Snapshot model on top of it. Section numbers below refer to these two. This guide follows the same design as the [commit fetcher plan](commit-fetcher-plan.md): git first, REST as a fallback, and the same `fetch()` → `Comparison` interface. It adds the hidden-file rule and spells out where the commit ids come from. Nothing was changed in the repo.

> **Updated 2026-10-17.** The pod's live service (`doc-tracker-5t4s.onrender.com/system`) now fixes the shared contract. Changes are marked *Contract:* or *Decided:* below. The contract makes renames one `RENAMED` change, a missing or private repo `REPOSITORY_NOT_FOUND`, and `TIMEOUT` a 500; the M0 build order adds `src/**` and `tests/**` as IMPLEMENTATION. Kaan has also decided on `requirements*.txt` → OTHER. The [roadmap](../roadmap.md) builds v1 from this guide, slice by slice. A second update the same day ([actions readiness](../reports/actions-readiness.md)) changed step 3 for the v3 GitHub Action, dropped `-l` from step 4 and made `fetch()` a context manager in step 8.

The git commands below were checked on 2026-10-16 against `psf/requests`. A blobless clone took about 1.2 s. At one commit, `ls-tree` listed 130 files, 26 of them hidden, which left 104 to analyse.

---

## Step 0: What the spec asks the connector to do

| Spec text | What it means for the connector |
|---|---|
| §2.2: *"The first version shall support public GitHub repositories with code and documentation stored in the same repository."* | Anonymous access only. Code and docs come from the same clone. |
| §2.2 (excluded): *"Documentation stored outside the repository."* | Never fetch wikis, GitHub Pages or external links. |
| REQ-01: *"When given a public Git repository, the system shall use read-only analysis to identify changes … For each change, it must report the affected file and change category."* | Output a list of changed files, each with a category. |
| REQ-05: *"When required inputs are missing or invalid, the repository or commit cannot be accessed … return an error status and a short message."* | Every failure maps to an error code. Nothing fails silently. |
| REQ-06: *"…treat its contents as read-only input and shall not execute repository-supplied code."* | Read files as bytes only. Never install, import or run anything from the repo. |
| REQ-07 / AC-10: same inputs give the same results | Use full SHAs and sort every list. |
| §5.2 / M4: `repository` is `"owner/name"`, `commit_id` is required, `base_commit` is optional. M4 note: *"default: first parent · Action: PR base or push before"*. Stored commits are 40-hex. | This is how the base and head ids are chosen (step 3). |
| §8.1: *"For repository change detection, we will reuse Git. We will use Git diff to identify changes between commits."* | git is the main path. REST is the fallback. |
| Schema v14: Snapshot = `commit`, `root: Folder` (folders/files), `sections` (Markdown), `unparsed` | The connector supplies each commit's file tree and file bytes. Later steps build sections and symbols from them. |

---

## Step 1: Validate the request (before touching the network)

- `repository` must match `^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$`.
- `commit_id` is required and must be 7–40 hex characters. The same rule applies to `base_commit` when it is given (M4).
- Otherwise return **400 `INVALID_REQUEST`** with a message such as `"commit_id is required"`. This example comes straight from spec §5.2.

## Step 2: Connect to the public repo

```bash
export GIT_TERMINAL_PROMPT=0            # never wait for a password
git -c credential.helper= clone --filter=blob:none --no-checkout --quiet \
    https://github.com/{owner}/{name}.git  $TMP/repo
```

- `--filter=blob:none` downloads commits and trees now and file contents only when they are read. That keeps large repos cheap.
- `--no-checkout` means no working tree is written, so nothing from the repo lands on disk as runnable files (REQ-06).
- `-c credential.helper=` and `GIT_TERMINAL_PROMPT=0` make the clone **anonymous**. A private or missing repo then fails at once (exit 128) and maps to **404 `REPOSITORY_NOT_FOUND`** (*Contract:* the pod's service uses this one code for both cases, replacing `REPO_NOT_ACCESSIBLE` / `REPO_NOT_FOUND`). This matters in testing. In this cloud container a proxy injects GitHub credentials, so `git ls-remote` on our private repo *succeeded*. Without the empty helper, the "public only" rule would not be enforced.
- Put a timeout on every git subprocess and return **`TIMEOUT`** when it expires.
- REST alternative: `GET /repos/{o}/{r}` returns 404 for missing or private repos when no token is sent.

## Step 3: Get the head and base commit ids

**Head** is always the request's `commit_id`:

```bash
git fetch --quiet --filter=blob:none origin {commit_id}   # only needed if not already in the clone
git rev-parse --verify {commit_id}^{commit}               # → full 40-hex SHA
```

GitHub lets a client fetch any reachable SHA by its full id (tested). A short SHA can only be resolved after the clone, which already contains every branch. An unknown SHA makes `rev-parse` exit 128 (tested), which maps to **404 `COMMIT_NOT_FOUND`**. *Decided (Q6):* a short SHA that can't be fetched (not on a branch or tag) or is ambiguous gets the same 404, with a message asking for the full 40-character SHA. *Decided (Q5):* any `base_commit` is accepted and diffed exactly as given.

**Base** depends on where the request came from:

| Caller | Base | Where it comes from |
|---|---|---|
| Direct API call, `base_commit` given | that SHA, resolved the same way | request body |
| Direct API call, no `base_commit` | **first parent** of head | `git rev-parse {head}^` |
| GitHub Action on `pull_request` | merge base of the PR base and head | `github.event.pull_request.base.sha`, with head = `github.event.pull_request.head.sha`. *Recommended (roadmap decision 10, to agree with the pod):* the v3 Action sends the merge base, read from `merge_base_commit` in GitHub's compare endpoint, so it needs no checkout (see below) |
| GitHub Action on `push` | the commit before the push | `github.event.before`, with head = `github.event.after`. After a force push, the merge base of the two |
| GitHub Action on `push` of a new branch, `before` = `0000…0000` | merge base of the default branch and head; the Action skips the push if that equals the head, which happens when the default branch itself is created | compare endpoint. *Decided:* not a first audit, because the contract can't ask for one for a head that isn't a root commit, and it would list the whole repo as added (roadmap decision 15) ([decision 15](../decisions.md#decision-15-the-base-for-a-push-that-creates-a-branch-2026-10-17)) |
| Root commit | none | `base_commit: null`. Schema v14 calls this a *"first audit"*: resolution checks only, and every file counts as added. |

Two details to get right:

- **PR base vs merge base.** `pull_request.base.sha` is the tip of the target branch, so it can include commits made there after the PR branched. Diffing the two directly would then blame the PR for those commits. Use `git merge-base {base} {head}` and diff from that, which is what GitHub's own "Files changed" tab does. The spec doesn't say this yet, so it's worth agreeing in the pod. The v3 Action reads it from `merge_base_commit` in `GET /repos/{owner}/{repo}/compare/{base}...{head}`, so it needs no checkout.
- **PRs from forks.** The head commit lives in the fork, but GitHub mirrors it in the base repo as `refs/pull/{n}/head`. Run `git fetch origin refs/pull/{n}/head`, or fetch the SHA directly, since it is reachable through that ref.

Store both ids as full 40-hex SHAs in the run file (`head_commit`, `base_commit`). This keeps runs repeatable (REQ-07).

REST equivalents: `GET /repos/{o}/{r}/commits/{ref}` returns `sha` and `parents[0].sha`. An unknown SHA there returns 422.

## Step 4: List every file at each commit, minus hidden ones

```bash
git ls-tree -r {sha}           # mode, type, blob sha, path
```

*Decided:* no `-l`. In a blobless clone, `-l` reads every blob's size and fetches each missing blob one at a time. The binary and size checks below run only on changed paths, after `git diff --numstat` has fetched their blobs in one batch; sizes then come from `git cat-file -s`.

Keep an entry only if all of these hold:

| Rule | Why |
|---|---|
| No path segment starts with `.` | Your hidden-file rule. It drops `.gitignore`, `.pre-commit-config.yaml`, `.github/…`, `.vscode/…` |
| Mode `100644` or `100755` (regular file) | `120000` is a symlink. Its "content" is just the target path, and `psf/requests` has two of them. `160000` is a submodule, which is another repo and therefore out of scope |
| Not binary | `git diff --numstat` shows `-  -` for binaries, or check the first 8 KB for a NUL byte. Spec §2.2: *"primarily support text-based source code and documentation files"* |
| Under a size cap (say 1 MB) | Bounds memory and time. Oversized files go to `skipped[]` instead of failing the run |

Files dropped for being binary or too large go into `skipped[]` with a reason, so REQ-05's "don't report an incomplete check as successful" still holds. Hidden files are simply out of scope and are not listed.

**Decisions this rule forces (flag to the pod):**
- `.github/` often holds real docs such as `CONTRIBUTING.md` and `SECURITY.md`. Excluding every dot-path drops them. They're arguably process docs rather than technical documentation, so excluding them is fine for v1.
- The **mapping file** must not be hidden, or this filter would hide it. Name it `doctracker.yml` rather than `.doctracker.yml`, or read it explicitly before filtering. This updates the name suggested in the overall plan.

The result is the `root: Folder` tree for that commit's Snapshot (schema v14): folders and files keyed by repo-relative `/` paths, with the root at `""`.

## Step 5: Sort each file into source code or documentation

Schema M3 says *"first matching path rule wins; no rule matches → OTHER"*, and M4's `Change.change_category` is one of `IMPLEMENTATION · DESIGN · ARCHITECTURE · SPECIFICATION · REQUIREMENT · DOCUMENTATION · OTHER`. A minimal rule table:

| Path rule | Category |
|---|---|
| `requirements*.txt` | OTHER (*Decided:* so the `*.txt` rule below doesn't catch it) |
| `*.md`, `*.rst`, `*.txt`, `docs/**` | DOCUMENTATION |
| `src/**`, `tests/**`, `*.py` (v1 parses Python only, per schema v14) | IMPLEMENTATION (*Contract:* `src/**` and `tests/**` added from the M0 build order) |
| everything else | OTHER |

Keep the rules in config, not in code, because their hash feeds `config_version`. DESIGN / ARCHITECTURE / SPECIFICATION / REQUIREMENT need path conventions the pod hasn't agreed yet (e.g. `docs/design/**`).

## Step 6: Read file contents at a commit

```bash
git show {sha}:{path}          # raw bytes; downloads that one blob on demand
```

- Decode as UTF-8. If decoding fails, put the file in `skipped[]` (schema v14 uses `PARSE_FAILED` for code files that don't parse).
- An unchanged file has the **same blob SHA** at base and head. Cache by blob SHA so it is read only once.
- A path missing on one side returns `None`. That is how "exists at base only" in the M3 rule is detected.
- REST alternatives: `GET /contents/{path}?ref={sha}` with `Accept: application/vnd.github.raw+json`, or `https://raw.githubusercontent.com/{o}/{r}/{sha}/{path}`, which has no rate limit and serves public repos only.

## Step 7: Get the changes between base and head

```bash
git diff --name-status -M {base} {head}   # A / M / D / R per file
```

- Apply the step 4 filter here too, so a change to `.gitignore` never appears in `changes[]`. *Decided (Q4):* the filter checks each side of a rename. A rename out of a hidden path is ADDED, a rename into one is DELETED, and a hidden path never appears as `old_path`.
- *Decided (Q3):* `-M` only, at git's default 50% similarity, so COPIED never appears.
- Renames: emit **one** `RENAMED` change with `old_path` set. *Contract:* this replaces the earlier "two changes" rule from M4. The M0 build order ("Rename yields ONE change with old_path set, not a delete + add"), the pod's live enum and tester case T-03 all expect one change. Schema v14's *"renames are not followed"* still holds for mapping: the detector treats the new path as unrelated to the old one.
- With no base (first audit), compare against the empty tree, so every file counts as added.
- *Decided (Q2):* no `-U0` hunks and no `unidiff` in v1.1, because nothing in the contract reads them. v1.2 may pass the plain `git diff` text to the LLM.

## Step 8: Hand it on and clean up

Return the `Comparison` from the [fetcher plan](commit-fetcher-plan.md) with three additions: `tree(side)` applies the step 4 filter, every `FileChange` carries its `change_category`, and the skipped files are included. Sort everything by path. *Decided:* `fetch()` is a context manager (`with fetch(repo, head, base) as cmp:`) that deletes the temp clone when the block exits, including on error, so `read()` works only inside the block. AC-09 checks that the analysed repo is unchanged, and since the clone is our own temporary copy, that holds automatically.

## Errors in one table

| When | Code | HTTP |
|---|---|---|
| Missing or badly formed field (step 1) | `INVALID_REQUEST` | 400 |
| Clone fails: missing or private repo (step 2) | `REPOSITORY_NOT_FOUND` (*Contract*) | 404 |
| `rev-parse` or `fetch` fails for head or base (step 3) | `COMMIT_NOT_FOUND` | 404 |
| A git call exceeds its timeout | `TIMEOUT` | 500, with nothing saved (*Contract:* the pod's service answers failures with `{code, message}` and no run file) |
| A file is binary, too large or undecodable | entry in `skipped[]` | — |

## Tests to write alongside (no network needed)

Build tiny repos in `tmp_path` with `git init`. Also add the nine cases from the fetcher plan, plus:

1. A commit that adds `.gitignore`, `.github/x.md` and `src/a.py` → only `src/a.py` appears in `tree()` and `changes[]`.
2. A symlink and a binary PNG → neither is read; the PNG is in `skipped[]`.
3. No `base_commit` → the base is the first parent. A root commit → the base is `null` and every file is added.
4. A PR-style history where the base branch moved on → the diff uses the merge base and doesn't blame the PR for base-branch commits.
5. A clone with no credentials against a private repo → `REPOSITORY_NOT_FOUND`.

## Tools

The same choices as the fetcher plan: the **git CLI** through `subprocess`, **dataclasses** for now (Pydantic once the API lands), **`httpx`** only for the REST fallback, and **`pytest`**. The hidden-file filter, file categories and binary check are plain Python and need no extra libraries.

## Open points for the pod

1. ~~Should `.github/` docs be excluded?~~ *Decided:* yes for v1 (roadmap decision 9).
2. Mapping file name: `doctracker.yml`, not hidden. Needed only once the mapping lands, in v1.3 or v2 (Q10).
3. Diff PRs from the merge base rather than `pull_request.base.sha`?
4. The path rules for DESIGN / ARCHITECTURE / SPECIFICATION / REQUIREMENT.
