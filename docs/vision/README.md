# Product vision

> **Inspiration, not a blueprint.** This folder describes where Documentation Tracker could end up after every phase. It is not the plan for the next version and not a checklist. **Most of the requirements, acceptance criteria and specs in here will not be available in most versions.** Some arrive much later, and some may never be built the way they are written. Use the folder to understand **why the system exists** and **the constraints it works under**, then take whatever ideas help the version you are building.
>
> What a version actually builds is decided by [the roadmap](../plan/roadmap.md), that version's spec (for v1.1, [spec-v1.1.md](../Models/v1/v1.1/spec-v1.1.md)) and [the decision log](../plan/decisions.md). Where they disagree with this folder, they win. Even firm-sounding lines here have already changed: section 8.2 keeps GenAI out of the running system, yet the roadmap brings an LLM in from v1.2.

## What's here

| File | What it is |
|---|---|
| [phase2-specification.txt](phase2-specification.txt) | The Phase 2 specification (Teams 15 and 16) as plain text, section by section, with a `[DIAGRAM]` line wherever the original shows a figure. Its last section lists where the specification contradicts itself. |
| [01-system-boundary.png](01-system-boundary.png) | Who is inside the tracker, who is outside, and what crosses the line (section 2.1) |
| [02-M1-data-flow-and-context.png](02-M1-data-flow-and-context.png) | M1: the data path from a push or an API call to the evidence store |
| [03-M2-analysis-run-lifecycle.png](03-M2-analysis-run-lifecycle.png) | M2: every way one analysis request can end |
| [04-M3-file-level-finding-rule.png](04-M3-file-level-finding-rule.png) | M3: when one changed file produces a finding, and of which type |
| [05-M4-run-file-schema.png](05-M4-run-file-schema.png) | M4: the request, the run file and the error body every team must share |
| [06-M5-finding-review-workflow.png](06-M5-finding-review-workflow.png) | M5: where a finding goes and how a person's decision is recorded |
| [documentation-tracker-schema-v14.pdf](documentation-tracker-schema-v14.pdf) | Schema v14: the team's fuller data model for the product vision (snapshots, the doc-to-code map, sections and symbols). Not built in v1; the roadmap moves its mapping to later versions (v2 and beyond). |

Read the diagrams in that order: the boundary first, then a request's path through the models. This folder replaces the original phase2.pdf, which was removed from the repo on 2026-10-17.

## The purpose, in one paragraph

Engineering and compliance teams at general-purpose AI model providers must keep technical documentation current as the model's design, architecture, specifications and requirements change (EU AI Act, Article 53(1)(a) and Annex XI). The tracker watches a repository's commits and pull requests, flags documentation that may now be missing or outdated, and keeps a traceable record of each check, so that people can fix the docs and answer an authority's request. It supports that work; it never does the compliance judgement itself.

## Constraints we have treated as firm so far

These have held in every version planned so far. They are still decisions, not laws, and the decision log is where one would change.

- **Read-only.** The tracker never changes the code or the documentation it analyses (REQ-06).
- **Never runs repository code.** Repository contents are data, never something to execute (REQ-06).
- **People decide.** A finding is only a suggestion; the tracker never approves or edits documentation on its own (REQ-03).
- **Git, public GitHub, docs in the same repo.** Other version control, private repos and documentation stored elsewhere are out of scope (section 2.2).
- **One shared contract.** Both teams answer the same requests with the same JSON (section 5), so a grader can compare them. In practice we match the other team's live service where it and this document differ.

## How each diagram compares with v1.1 (October 2026)

v1.1 is the first slice: change detection over the API, deployed on Railway. Most of what the diagrams show is later work.

- **01, system boundary.** v1.1 builds part of the central box: it detects and classifies changes when called through the API. There is no GitHub Action, no evidence storage outside the service, and no review loop yet.
- **02, M1.** v1.1 has the API, RESOLVE, the classification half of DETECT, and SAVE, which writes run files to the service's own disk (wiped on every redeploy) instead of an evidence repository. The Action step and durable evidence storage are planned for v3. The routes sit under `/system`, and an unknown run id returns 404 `ANALYSIS_NOT_FOUND`, both copied from the other team's service.
- **03, M2.** Where M2 and the other team's service differ, v1.1 follows the service. A missing repository or commit is a 404 (`REPOSITORY_NOT_FOUND`, `COMMIT_NOT_FOUND`), not a 200 with status ERROR, and a timeout is a 500 (`TIMEOUT`). Nothing is saved for a failed request. There is no mapping config to load yet, and skipped files don't turn a run into ERROR.
- **04, M3.** Only the CLASSIFY step exists: the first matching path rule wins, everything else is OTHER, and `config_version` is a hash of the rules file. `issues[]` is always empty. Findings arrive in v1.2, decided by an LLM (roadmap decision 4); a code-to-doc mapping file comes in v1.3 or v2.
- **05, M4.** v1.1 copies the other team's OpenAPI document, which differs from M4. A change is `path`, `old_path`, `change_type` and `category`; a rename is one RENAMED change, not a delete plus an add; TYPE_CHANGED exists; we add DOCUMENTATION to the categories; and the error codes are INVALID_REQUEST, REPOSITORY_NOT_FOUND, COMMIT_NOT_FOUND, TIMEOUT and WRITE_FAILED.
- **06, M5.** Not in v1.1. The GitHub Action, its pull request and commit comments, and the review loop are all planned for v3 ("hosted review loop" in the roadmap). Whether decisions live in PR replies, as M5 shows, or in a small review endpoint is still open (roadmap decision 7).
