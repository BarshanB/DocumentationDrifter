# DocumentationDrifter: the end product and where each part lands

The Phase 2 spec (`phase2.pdf`, the pod's specification) and schema v14 (`Models/documentation-tracker-schema-v14.pdf`) describe the **end product**, not v1 or v2. This file keeps that picture in one place and says which version builds each part, and where a later decision changed it. The [roadmap](roadmap.md) is the plan to follow; the [decision log](decisions-2026-10-17.md) has the reasons. Terms are as in [CONTEXT.md](../CONTEXT.md).

Revised 2026-10-17 to match the decisions and the v1.1 build. The first version of this file was a snapshot of `main` at `5b74560`.

## 1. The end product, in one paragraph

A read-only service, called by a GitHub Action on every push and pull request, that works out what changed between two commits of a public repo and flags documentation that is now missing or outdated. It does this through a living map between doc sections and the code they describe (the "sectioning" of phase2.pdf §7.2 and schema v14). Every finding is `PENDING_REVIEW` until an authorised human confirms or dismisses it. The decision, reviewer and timestamp are recorded, and the tool never edits code or docs. Each run is saved as one JSON file that can be fetched back unchanged. The final version is deterministic: the same inputs give the same findings.

## 2. What changed since Phase 2

| Phase 2 said | Now | Why |
|---|---|---|
| No GenAI in the running system; a hand-written rule-based detector (§8.1, §8.2) | An LLM decides drift from **v1.2**, probabilistic on purpose for now; the **final version** is deterministic | Decision 4 (Q1, Q9); also Kaan's note in `Source/LLM_Shell/LLM.md` |
| A confidence rating in Phase 4; AC-10 within 0.05 | No confidence field; AC-10 is checked without that clause, and the LLM's reasoning goes in `explanation` | Decision 5 (Q13); the shared contract has no such field |
| A mapping file is required (M2, M3) | None in v1.1 or v1.2; the mapping file arrives in **v1.3** if time allows, otherwise **v2** | Q10 |
| Section-level mapping (sectioning, schema v14) | **After v2.** The roadmap lists it under v4, because `Finding` is file-level in the shared contract and the pod would have to extend it | Roadmap "What this changes" 3 |
| Changed lines from `git diff -U0` (hunks) | Dropped from v1.1; they come back with section-level mapping | Q2 |
| Failed analyses saved as HTTP 200 with status ERROR (M2) | 400, 404 or 500 with an `ErrorBody`, nothing saved | Decision 13; matches the reference service |
| Error codes `REPO_NOT_FOUND`, `REPO_NOT_ACCESSIBLE`, `INVALID_CONFIG`, `CHECKS_SKIPPED`, `DETECTOR_ERROR` | The contract's codes: `INVALID_REQUEST`, `REPOSITORY_NOT_FOUND`, `COMMIT_NOT_FOUND`, `TIMEOUT`, `WRITE_FAILED`; `LLM_UNAVAILABLE` from v1.2; `INVALID_CONFIG` returns with the mapping file | Reference service; Q16 |
| `POST /analyze`, `GET /analysis/{id}` | The same under `/system`, plus `GET /system/health` | Reference service |
| Per-user sign-in and storage, job queues, repos that sleep and wake (§7.3, `WebHookConnectors.png`) | **v4**, only by conscious choice | Roadmap v4; the tester calls a stateless API |
| A documentation viewer in Phase 3 (§6.1) | A minimal read-only viewer in **v3**, only if the course still requires it | Roadmap v3 item 5 |
| User notifications in Phase 5 | **v4**; phase2.pdf §6.4 names them as the first thing to cut | Roadmap v4 |
| The Action uses `github.sha` as head and the PR base as base | Head is `pull_request.head.sha` and base is the merge base, read from GitHub's compare endpoint, in **v3** | Decision 15, guide step 3 |
| Mapping file `.doctracker.yml` | `doctracker.yml`, because the hidden-path rule would drop a dot-file | Guide step 4 |

## 3. Phase 2's review notes and how they were settled

phase2.pdf pp. 19–20 lists twelve inconsistencies to fix before the next phase.

| # | Note | Settled as |
|---|---|---|
| 1 | Fact comparison (REQ-02, §8.1) or co-change (M3)? | From v1.2 the LLM reads the changed code and the docs and judges drift, which is closer to fact comparison. The deterministic rule for the final version is still open. |
| 2 | Human review mandatory (REQ-03) or selectable (§7.2)? | Mandatory: every finding is `PENDING_REVIEW` (roadmap goal 3). Recording decisions comes in v3. |
| 3 | Read-only scope, yet the architecture edits docs | Read-only. The tool never edits the repo or its docs (goal 3, REQ-06). |
| 4 | HTTP 200 with ERROR, or 404 and 500? | 400, 404 or 500 with nothing saved (decision 13). |
| 5 | Examples use `sample-credit-project` and 6-character SHAs | `owner/name`, 7–40 hex in, 40 hex out, and `config_version` always present ([spec](spec-v1.1.md)). |
| 6 | Confidence and repeatability | No confidence field (decision 5). v1.1 is exact; from v1.2 `changes[]` stays exact and `issues[]` is checked by shape. |
| 7 | Is a mapping required, and in what format? | Not before v1.3 or v2. Its name and format are open (roadmap decision 6). |
| 8 | Reliability measured before the mapping exists | The reliability run moves to v2, on the public test repo (ticket 11). |
| 9 | Stateless test interface versus per-user storage | The API is stateless; per-user storage is v4. |
| 10 | How AC-05 reads review decisions back | v3. A small review endpoint agreed with the pod is recommended (roadmap decision 7, open). |
| 11 | Viewers, notifications and the hosted app versus the narrow scope | Each is labelled with its version in the roadmap. |
| 12 | "Human review ensures compliance" | The tool supports documentation maintenance; it certifies nothing. |

## 4. The pipeline, version by version

| Stage | v1.1 (built) | v1.2 | v1.3 or v2 | Later |
|---|---|---|---|---|
| Validate the request | `owner/name` and 7–40 hex, before any git work | — | — | — |
| Get the repo | Anonymous blobless clone with no checkout, deleted after the run | — | — | REST fallback for hosts without git (v4) |
| Resolve commits | Full SHAs; base is `base_commit`, else the first parent, else none (first audit) | — | — | — |
| Changed files | `git diff --raw -M`: renames only, hidden paths, symlinks and submodules ignored | — | — | — |
| Skipped files | Binary, over 1 MB, not UTF-8 | Docs over the 200 KB doc budget | — | — |
| Categories | Ordered path rules in `path_rules.json` | — | — | DESIGN, ARCHITECTURE, SPECIFICATION and REQUIREMENT rules, once the pod agrees conventions |
| Drift | `issues[]` empty | The LLM reads the changed code and every doc at head and fills `issues[]` | The mapping narrows what the LLM reads; the reliability run | Deterministic detection in the final version; section and symbol level (§5) |
| `config_version` | Hash of the rules file | Plus the LLM provider, model and doc budget | Plus the mapping file at head | — |
| Save the run | `runs/{analysis_id}.json` on local disk | — | — | Durable store in v3 (an evidence repo through the Contents API) |
| Callers | The `/system` API and the tests | — | — | The GitHub Action (v3); the webhook (v4) |
| Review | — | — | — | Review records beside the run file (v3) |

## 5. Sectioning, kept for after v2

This is schema v14's model, the "living map" of phase2.pdf §7.2. It stays out until Kaan schedules it.

- **Snapshot** of the repo at one commit: a folder tree, doc sections, code symbols and code-to-code dependencies.
- **DocSection:** one Markdown heading and everything under it, keyed by `doc_path` and `heading_path`, with line spans. Each file also has a whole-file section.
- **Function and Class:** named code symbols with line spans, from `ast` for Python first and tree-sitter adapters for other languages.
- **DocLink:** an authored entry in the mapping file tying a section to code selectors such as `src/model/`, `src/model/scoring.py`, `src/model/scoring.py::score` or `src/model/scoring.py::Scorer.score`.
- **The rule:**
  - Code has changed when a target's span overlaps a hunk on either side, when it exists at base only, or when something it depends on changed (one hop).
  - Code changed and doc not → `OUTDATED_DOCUMENTATION`.
  - Link kept but section gone → `MISSING_DOCUMENTATION`.
  - Unresolvable selector → skipped as `INVALID_MAPPING`.
  - Unparsable code → skipped as `PARSE_FAILED`.

Turning it on needs:
- hunks back (`git diff -U0`)
- a Markdown sectioner (`markdown-it-py`, or a small heading parser that skips code fences)
- a symbol extractor
- a mapping format agreed with the pod
- a `Finding` extended with section and line detail, which changes the shared contract

The connector's `tree()` and `read()` already give it what it reads from git.

## 6. Safety (REQ-06), as built in v1.1

- Nothing from the repo is installed, imported or run. A test plants files that would leave a marker if they ran.
- The clone is anonymous: `GIT_TERMINAL_PROMPT=0` and an empty credential helper, so a private repo fails at once.
- Blobless with no checkout: repo files exist only as git objects in a temporary clone, deleted after every run, error or not.
- Each git call has a 60 s cap and the analysis a 120 s deadline; a git process that overruns is killed with its whole process group.
- At most two analyses run at once, so two clones fit in Render's free-tier 512 MB.

## 7. Tooling, as used

- **Tests:** `pytest` with FastAPI's `TestClient` against the real app. Fixture repos are built with git under `tmp_path`, plus the labelled test repo from `tools/testrepo.py`.
- **CI:** `.github/workflows/ci.yml` on every PR. `acceptance.yml` checks the deployed service on demand.
- **Hosting:** a Dockerfile with git, deployed to Render's free tier (`render.yaml`) once Kaan approves.
- **Not added, by choice** (`Skills/CLAUDE.md`, minimal first): `pyproject.toml`, `ruff` and `mypy`.

## 8. Left out until someone decides otherwise

Languages other than Python, following renames, private repos with a token, per-user accounts, the webhook and queue path, notifications, and a viewer beyond the v3 minimum.
