# DocumentationDrifter: what we're building and how

Scanned 2026-10-16 at `main` @ `5b74560`. Sources: the repo (README, `Skills/CLAUDE.md`, `Models/documentation-tracker-schema-v14.pdf`, `Models/WebHookConnectors.png`, `Source/GitHub_Connector/*`), the Phase 2 spec (`/mnt/project-files/phase2.pdf`), and the earlier API notes in [base-head-endpoints.md](/mnt/project-files/github-api/base-head-endpoints.md). Nothing was changed in the repo.

> *Superseded in part (2026-10-17).* This is a snapshot from `5b74560`. Where it differs from the [roadmap](roadmap.md), the roadmap wins. In particular, the webhook and GitHub App path is v4, after Phase 5 (roadmap decision 14), the v3 GitHub Action is the only Phase 5 trigger, and an Action's head and base follow [guide step 3](github-connector-steps.md).

> *Superseded (2026-10-17, [decision log](decisions-2026-10-17.md)).* The detection design below (hand-written rule, hunk overlap, section selectors, a confidence value) no longer applies. An LLM decides drift from v1.2 (Q1, Q9), there is no mapping file before v1.3 or v2 (Q10), hunks are dropped (Q2), `Finding` has no confidence field (Q13), and the error codes follow the pod's contract plus `LLM_UNAVAILABLE` (Q16). Read the [roadmap](roadmap.md) for the current plan; this file is kept as history.

## 1. What we're building, in one paragraph

A **read-only web service** that takes a public GitHub repo plus a head commit (and an optional base commit), works out what changed between the two, and uses an **authored mapping file in the repo** (doc section ↔ code selectors) to flag documentation that is now **missing or outdated**. Every finding is `PENDING_REVIEW` for a human. Each run is saved as one JSON file. A **GitHub Action** calls the service on push or PR and posts the result back. No LLM runs inside the service (spec §8.2); detection is rule-based and repeatable.

Interface (spec §5, schema M4):

- `POST /analyze` with `{repository: "owner/name", commit_id, base_commit?}` returns an `AnalysisResult` (analysis_id, head/base commit, config_version, tool_version, status, issues[], changes[], skipped[], error, created_at).
- `GET /analysis/{analysis_id}` returns the saved run file unchanged.
- Errors: `INVALID_REQUEST`, `REPO_NOT_FOUND`, `REPO_NOT_ACCESSIBLE`, `COMMIT_NOT_FOUND`, `INVALID_CONFIG`, `CHECKS_SKIPPED`, `DETECTOR_ERROR`, `TIMEOUT`, `WRITE_FAILED`.

## 2. Where the repo is today

| Thing | State |
|---|---|
| `Source/GitHub_Connector/gitHook.py` | `monitor()` and `get_diff()` are comments only; file starts with a bare `import`, so it doesn't parse. |
| `parse.py` | `parse(request)` → `Change_request(file, line_start, line_end)`; imports a module `blank` that doesn't exist. |
| `store.py` | Commented outline of `Repository` (sleep/revive/load doc). |
| `Models/` | Schema v14 (the best design doc in the repo) and a webhook architecture sketch. |
| `migrations/` | An Alembic setup was added then removed in the last commit. |
| Tests, CI, dependencies file | None yet. |
| Visibility | The repo is **private**; v1 targets **public** repos, so test repos must be public (or the service needs a token). |

**Two architectures are in play and they should be reconciled before coding:**

1. **Spec M1 (stateless):** Action → `POST /analyze` → resolve → detect → save run file. No accounts, no stored repos.
2. **README / `WebHookConnectors.png` / spec §7.3 (stateful):** GitHub App webhooks → queue → workers → database, per-user sign-in, repos "sleep" and "revive".

**Recommendation:** build (1) for Phases 3–4. It's what the acceptance tests hit, and it's much smaller. Keep (2) as the Phase 5 "hosted app" layer on top: a webhook simply becomes another caller of the same `analyze()` function. The current stubs (`monitor`, `Repository.sleep/revive`) belong to (2) and can wait.

## 3. The pipeline (M2 states) and the tool for each step

```
VALIDATING → RESOLVING → ANALYZING → SAVING → SUCCESS | ERROR | NOT SAVED
```

| Step | What it does | Recommended tool | Alternatives / notes |
|---|---|---|---|
| Validate request | Check `owner/name`, 7–40 hex SHAs; return 400 | **FastAPI + Pydantic v2** (models double as the JSON schema) | Flask + jsonschema. FastAPI also gives free OpenAPI docs for the other team. |
| Get the repo | Fetch both commits without running anything | **`git` CLI via `subprocess`**: `git clone --filter=blob:none --no-checkout`, `git fetch origin <sha>` | REST `tarball/{sha}` (one call per snapshot) when the host has no git. GitPython / pygit2 add little over the CLI. |
| Resolve commits | Short → full SHA; default base = first parent | `git rev-parse <sha>^{commit}`, `git rev-parse <sha>^` | REST `GET /repos/{o}/{r}/commits/{ref}` (`parents[0]`), see API notes. |
| Changed lines | `git diff -U0 base head` → hunks per file, both sides | **git CLI + `unidiff`** (parses hunks, statuses, renames) | REST `compare/{base}...{head}` has `patch`, but caps at 300 files and drops large patches. |
| Snapshot tree | Folder/File list at each commit | `git ls-tree -r --name-only <sha>` | REST `git/trees/{sha}?recursive=1`. |
| File content | Read a file at a commit | `git show <sha>:<path>` | REST `contents/{path}?ref=` (raw), or `raw.githubusercontent.com` (no rate limit, public only). |
| Python symbols | Functions/classes/methods with start (incl. decorators) and end lines | **stdlib `ast`** (`lineno`, `end_lineno`, `decorator_list`); it parses, never executes | **tree-sitter + tree-sitter-python**, which schema v14 names; worth it once a second language is added. |
| Dependencies (1 hop) | Name-based call/inheritance edges | `ast.walk` over `Call` / `ClassDef.bases` | tree-sitter queries later. |
| Markdown sections | Heading path, start/end line per section, plus whole-file section | **`markdown-it-py`** (token `.map` gives line ranges, ignores `#` inside code fences) | A 20-line ATX-heading regex is enough if fences are handled. |
| Mapping file | Authored `DocLink`s read at base and head | **YAML via `PyYAML.safe_load`** at a fixed path, e.g. `.doctracker.yml` | JSON (no dependency). Format and path still need pod agreement (spec review note 7). |
| Detect (M3) | Overlap hunks with spans, apply the rule table | Plain Python | — |
| `config_version` | Hash of the mapping file at head | `hashlib.sha256` | — |
| Save run | `runs/{analysis_id}.json`, written once | Local disk / volume for v1; then commit to a separate **evidence repo** via the GitHub Contents API (M1) | SQLite or S3-style bucket if the host has no persistent disk. |
| Analysis id | Unique, server-assigned | `uuid4` or ULID (sortable by time) | — |

### The M3 rule in code terms (symbol level, schema v14)

For each `DocLink` in the mapping at head (and base):

1. Resolve every selector (`path/`, `path`, `path::name`, `path::Type.method`) against the snapshot. Unresolvable → `SKIPPED · INVALID_MAPPING`. Code file fails to parse → `SKIPPED · PARSE_FAILED`.
2. **code changed** = a target's span overlaps a hunk (either side), or it exists at base only, or a target it depends on changed (1 hop).
3. **doc changed** = the section's span overlaps a hunk.
4. code changed and doc not → `OUTDATED_DOCUMENTATION`. Link kept, section gone, target kept → `MISSING_DOCUMENTATION`. Both changed → no finding in v1.
5. Every changed file goes into `changes[]` regardless.

Sort `issues`, `changes` and `skipped` by path and id before saving, so repeated runs are byte-identical apart from `analysis_id` and `created_at` (AC-10).

## 4. GitHub side

- *Superseded (2026-10-17) by [guide step 3](github-connector-steps.md) and roadmap v3 item 2: on a PR, head is `pull_request.head.sha`, not `github.sha` (which is GitHub's synthetic merge commit), and base is the merge base.* **Trigger:** a workflow in the analysed repo on `push` and `pull_request`. Base = `github.event.pull_request.base.sha` or `github.event.before`; head = `github.sha`. It `curl`s `POST /analyze` and posts findings as a PR comment or check run using the built-in `GITHUB_TOKEN` (`actions/github-script` or `gh`).
- **Rate limits:** the git path uses no REST quota. If the REST path is used, unauthenticated is 60 req/h per IP, which runs out fast; a no-scope token gives 5,000/h. Details in the [API notes](/mnt/project-files/github-api/base-head-endpoints.md).
- **Review (M5, REQ-03):** reviewers confirm/dismiss by replying on the PR comment; the run file stays `PENDING_REVIEW` and decisions are recorded alongside (spec review note 10 asks how AC-05 reads them back; a small `POST /analysis/{id}/review` endpoint is the simplest testable answer).
- **Phase 5 webhook path:** a GitHub App, HMAC check on `X-Hub-Signature-256`, dedupe on `X-GitHub-Delivery`, a queue (RQ + Redis, or just a DB table), and `smee.io` for local webhook testing.

## 5. Safety (REQ-06)

- Never `pip install`, import, run tests or build in the cloned repo. `ast.parse` and Markdown parsing only read text.
- Clone into a fresh temp dir per run, `--no-checkout` (read blobs with `git show`), delete it afterwards. Cloned repos carry no hooks.
- Set `GIT_TERMINAL_PROMPT=0` and a timeout on every git call; cap repo size / file count and return `TIMEOUT` or `CHECKS_SKIPPED` rather than hanging.
- AC-09 test: hash the fixture repo before and after a run and assert nothing changed.

## 6. Dev tooling

| Need | Tool |
|---|---|
| Language / env | Python 3.12, `uv` (or pip + venv), `pyproject.toml` |
| Tests | `pytest`; FastAPI `TestClient`; fixture repos built in tests with `git init` in `tmp_path` so cases are exact |
| Lint / types | `ruff` (lint + format), `mypy` (optional) |
| CI | GitHub Actions running pytest on every PR |
| Contract testing with the other team | The OpenAPI schema FastAPI emits; optionally `schemathesis` against the deployed URL |
| Deploy (Phase 5) | Dockerfile with `git` installed; Render / Fly.io / Railway free tier, or a small VM. Needs a persistent volume for `runs/` unless runs go to the evidence repo. |
| Dev assistants | Claude / Codex offline only (spec §8.2) |

## 7. Suggested build order

Aligned with the spec's milestones. Each step ends in something testable.

**Phase 3: changes and the interface (AC-01, 07, 08, 10)**
1. `pyproject.toml`, `ruff`, `pytest`, CI workflow.
2. Pydantic models for `AnalysisRequest`, `AnalysisResult`, `Finding`, `Change`, `Skipped`, `ErrorInfo` (straight from M4).
3. `GitHub_Connector`: `fetch(repo)`, `resolve(sha)`, `diff(base, head)` → `Change[]` + hunks. This replaces the `get_diff` stub; `monitor` waits for Phase 5.
4. `POST /analyze` returning `changes[]` only; `GET /analysis/{id}` reading run files.
5. Error mapping: clone fails → `REPO_NOT_ACCESSIBLE` (404), unknown SHA → `COMMIT_NOT_FOUND` (404), bad body → 400.
6. A public **test repo** with labelled cases (spec §4.2). Also needed for the Priority 1 risk.

**Phase 4: mapping and detection (AC-02, 03, 10)**
7. Markdown sectioner and Python symbol extractor → `Snapshot`.
8. Mapping file loader and selector resolver.
9. M3 rule → `issues[]` and `skipped[]`. Template explanations.
10. Reliability run on the test repo (target ≥90% caught, <10% false alerts). If missed, fall back to file-level mapping (spec §9.1).

**Phase 5: hosting and review (AC-04, 05, 06, 09)**
11. Deploy, evidence repo, Action that comments on PRs, review recording.
12. Optional: GitHub App + webhooks + queue (the `WebHookConnectors.png` design), sign-in, notifications.

## 8. Decisions needed before coding (from the spec's own review notes)

These change what gets built, so the pod should settle them first:

1. **Fact comparison vs co-change.** REQ-02 says "compare facts"; M3 says "both changed → no warning". Schema v14 already chose co-change at symbol level; narrow REQ-02 to match.
2. **HTTP status for failed runs.** M2 saves ERROR runs with HTTP 200; §5.1 says 404/500. Suggest: 400/404 when nothing is saved, 200 + `status: ERROR` once a run file exists.
3. **Confidence.** AC-10 wants confidence within 0.05, but the schema has no field. Either add `confidence` to `Finding` or drop it from AC-10. A rule-based detector can just say 1.0.
4. **Mapping file format and path** (`.doctracker.yml`?) and whether it's required in test repos.
5. **Spec examples** use `sample-credit-project` and 6-char SHAs; fix to `owner/name` and 7–40 hex.
6. **Stateless vs stateful** (section 2 above).

## 9. Deliberately left out (per `Skills/CLAUDE.md`: minimal first)

Not in the minimal v1 above, flagged so it's a conscious choice: languages other than Python, rename following, per-user accounts and storage, the webhook/queue path, notifications, a viewer UI beyond the PR comment, and any runtime LLM.
